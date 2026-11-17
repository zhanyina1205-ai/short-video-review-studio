"""Local snapshot archive and offline report renderer."""
import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path

ROOT = Path.home() / "Documents" / "短视频复盘"
KEYS = {"plays", "views", "likes", "comments", "saves", "shares", "gained", "lost"}


def render(doc, weekly):
    e = lambda value: escape(str(value))
    cards = "".join(f'<div><small>{e(k)}</small><b>{e(v)}</b></div>' for k, v in doc["highlights"])
    heads = ["平台", "作品 / 指标", "结果", "比较口径", "解读"] if weekly else ["维度", "指标", "读数", "比较口径", "解读"]
    rows = []
    for row in doc["metrics"]:
        if len(row) != 5:
            raise ValueError("每行指标需要五列")
        rows.append("<tr>" + "".join(f"<td>{e(cell)}</td>" for cell in row) + "</tr>")
    table = ("<div class=scroll><table><thead><tr>" + "".join(f"<th>{h}</th>" for h in heads)
             + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>") if rows else ""
    sections = "".join(f"<article><h2>{e(k)}</h2><p>{e(v)}</p></article>" for k, v in doc["sections"])
    kind = "运营周报" if weekly else doc["platform"] + " · 单条复盘"
    page = (Path(__file__).with_name("report.html")).read_text()
    from string import Template
    return Template(page).substitute(title=e(doc["title"]), kind=e(kind), summary=e(doc["summary"]),
                                     note=e(doc["note"]), cards=cards, table=table, sections=sections)


def write_html(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as out:
        out.write(content)
    os.replace(out.name, path)


def monday(value):
    day = date.fromisoformat(value)
    if day.weekday() != 0:
        raise ValueError("请输入该周周一的日期")
    return day


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="op", required=True)
    sub.add_parser("list")
    get = sub.add_parser("get")
    get.add_argument("id")
    sub.add_parser("save").add_argument("file", type=Path)
    week = sub.add_parser("week")
    week.add_argument("day")
    week.add_argument("cutoff", nargs="?")
    report = sub.add_parser("report")
    report.add_argument("day")
    report.add_argument("file", type=Path)
    a = parser.parse_args()
    a.root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(a.root / "作品档案.sqlite")
    db.execute("CREATE TABLE IF NOT EXISTS snapshots (id TEXT, observed TEXT, data TEXT, PRIMARY KEY(id,observed))")
    if a.op in {"save", "report"}:
        d = json.loads(a.file.read_text())
        if a.op == "save":
            stamp = datetime.fromisoformat(d["observed"]).isoformat(timespec="minutes")
            if d["published"]:
                datetime.fromisoformat(d["published"])
            if any(k not in KEYS or type(v) != int or v < 0 for k,v in d["counts"].items()):
                raise ValueError("counts 仅接受支持的非负整数计数")
            key = hashlib.sha256(d["id"].encode()).hexdigest()[:12]
            path = a.root / "单条" / key / (stamp.replace(":", "-") + ".html")
            d["observed"] = stamp
            content = render(d, False)
            with db:
                db.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?)", (d["id"], stamp, json.dumps(d, ensure_ascii=False)))
                write_html(path, content)
        else:
            path = a.root / "周报" / (monday(a.day).isoformat() + ".html")
            write_html(path, render(d, True))
        print(path)
        return
    if a.op == "get":
        rows = db.execute("SELECT data FROM snapshots WHERE id=? ORDER BY observed", (a.id,))
        print(json.dumps([json.loads(row[0]) for row in rows], ensure_ascii=False, indent=2))
        return
    latest = {}
    cutoff = getattr(a, "cutoff", None)
    for key, stamp, data in db.execute("SELECT id,observed,data FROM snapshots ORDER BY observed"):
        if not cutoff or stamp <= cutoff:
            latest[key] = json.loads(data)
    if a.op == "list":
        result = [{k:d.get(k) for k in ("id","platform","account","title","published","observed")} for d in latest.values()]
    else:
        start = monday(a.day)
        stop = (start + timedelta(days=7)).isoformat()
        works = [d for d in latest.values() if start.isoformat() <= d["published"][:10] < stop]
        totals = defaultdict(dict)
        for d in works:
            for k,v in d["counts"].items():
                stat = totals[d["platform"]].setdefault(k, {"sum":0, "works":0})
                stat["sum"] += v
                stat["works"] += 1
        result = {"start":a.day, "works":works, "totals":totals, "undated":[d["id"] for d in latest.values() if not d["published"]]}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
