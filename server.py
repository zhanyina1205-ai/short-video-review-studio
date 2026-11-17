import hashlib
import json
import mimetypes
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo

from analysis import FIELDS, extract, make_report

HERE=Path(__file__).resolve().parent
SKILL=HERE/"skill/scripts"
sys.path.insert(0,str(SKILL))
import review
ROOT=Path(os.environ.get("VIDEO_REVIEW_DATA",review.ROOT))
PORT=int(os.environ.get("VIDEO_REVIEW_PORT",18476))
HOST=f"127.0.0.1:{PORT}"
CACHE=Path.home()/"Library/Caches/video-review-studio"
lock=threading.Lock()

def recognize(data):
    if not data.startswith((b"\x89PNG\r\n\x1a\n",b"\xff\xd8\xff")):
        raise ValueError("请选择 PNG 或 JPEG 截图")
    exe=CACHE/"ocr"
    with lock:
        if not exe.exists() or exe.stat().st_mtime<(HERE/"ocr.swift").stat().st_mtime:
            CACHE.mkdir(parents=True,exist_ok=True)
            compiler=["xcrun","swiftc"]
            sdk=Path("/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk")
            if sdk.exists(): compiler+=["-sdk",str(sdk)]
            subprocess.run(compiler+[str(HERE/"ocr.swift"),"-o",str(exe)],check=True,timeout=120,capture_output=True)
    with tempfile.NamedTemporaryFile() as f:
        f.write(data);f.flush()
        blocks=json.loads(subprocess.check_output([str(exe),f.name],timeout=90))
    blocks.sort(key=lambda p:(round(p["y"],2),p["x"]))
    lines=[b["t"] for b in blocks]
    result={"fields":extract(blocks),"lines":lines}
    for i,t in enumerate(lines):
        m=re.search(r"(20\d\d-\d\d-\d\d) (\d\d:\d\d).*发布",t)
        if m:
            result["published"]=m[1]+"T"+m[2]
            if i: result["title"]=lines[i-1]
            break
    return result

def report_route(d):
    code=hashlib.sha256(d["id"].encode()).hexdigest()[:12]
    return f'/reports/单条/{code}/{d["observed"].replace(":","-")}.html'

def connect():
    db=sqlite3.connect(ROOT/"作品档案.sqlite",timeout=15)
    db.execute("CREATE TABLE IF NOT EXISTS snapshots(id TEXT, observed TEXT, data TEXT, PRIMARY KEY(id,observed))")
    return db

def state():
    works={}
    with connect() as db:
        for raw, in db.execute("SELECT data FROM snapshots ORDER BY observed DESC"):
            d=json.loads(raw)
            if d["id"] not in works: works[d["id"]]=dict(d,history=[])
            works[d["id"]]["history"].append({"time":d["observed"],"url":report_route(d)})
    weeks=sorted((ROOT/"周报").glob("????-??-??.html"),reverse=True)
    return {"works":list(works.values()),"weeks":[p.stem for p in weeks],"fields":list(FIELDS),"today":datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="minutes")[:16]}

def save(payload):
    platform=payload["platform"]
    if platform not in ["抖音","小红书"]: raise ValueError("请选择平台")
    title=payload["title"].strip()
    if not title: raise ValueError("请输入标题")
    published=payload["published"]; observed=payload["observed"]
    for stamp in [observed]+([published] if published else []):
        if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d",stamp): raise ValueError("请输入完整日期与时间")
        datetime.fromisoformat(stamp)
    if published and published>observed: raise ValueError("观察时间应在发布之后")
    key=payload.get("id") or hashlib.sha256((platform+"|"+title+"|"+published).encode()).hexdigest()[:24]
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        for raw, in db.execute("SELECT data FROM snapshots"):
            old=json.loads(raw)
            if old["platform"]==platform and old["title"]==title and old["published"]==published:
                key=old["id"];break
        prev=db.execute("SELECT data FROM snapshots WHERE id=? ORDER BY observed DESC LIMIT 1",(key,)).fetchone()
        if prev and json.loads(prev[0])["platform"]!=platform: raise ValueError("补录时请保持平台一致")
        if db.execute("SELECT 1 FROM snapshots WHERE id=? AND observed=?",(key,observed)).fetchone(): raise ValueError("这条作品的同一观察时间已归档，请查看已有报告或填写新截图的观察时间")
        d=make_report(dict(id=key,platform=platform,published=published,observed=observed,title=title,account="",theme="",goal=payload["goal"],fields=payload["fields"]))
        note=str(payload.get("context","")).strip()
        if note: d["sections"].insert(0,["补充观察",note])
        url=report_route(d)
        review.write_html(ROOT/url.removeprefix("/reports/"),review.render(d,False))
        db.execute("INSERT INTO snapshots VALUES (?,?,?)",(key,observed,json.dumps(d,ensure_ascii=False)))
    return {"url":url}

class Handler(BaseHTTPRequestHandler):
    def reply(self,data,kind="application/json; charset=utf-8",status=200):
        if not isinstance(data,bytes): data=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type",kind)
        self.send_header("Content-Length",str(len(data)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if self.headers.get("Host")!=HOST: return self.send_error(403)
        path=unquote(urlsplit(self.path).path)
        if path=="/api/state": return self.reply(state())
        if path=="/api/health": return self.reply({"app":"video-review-studio"})
        if path in ["/","/style.css","/app.js"]: f=HERE/("index.html" if path=="/" else path[1:])
        elif path.startswith("/reports/"):
            f=(ROOT/path[9:]).resolve()
            if ROOT.resolve() not in f.parents or f.suffix!=".html": return self.send_error(404)
        else: return self.send_error(404)
        if not f.is_file(): return self.send_error(404)
        self.reply(f.read_bytes(),(mimetypes.guess_type(f.name)[0] or "text/plain")+"; charset=utf-8")
    def do_POST(self):
        if self.headers.get("Host")!=HOST or self.headers.get("Origin")!="http://"+HOST: return self.send_error(403)
        try:
            size=int(self.headers.get("Content-Length","0"))
            if not 0<size<=18*1024*1024: raise ValueError("单张截图请控制在 18 MB 以内")
            data=self.rfile.read(size)
            if self.path=="/api/ocr": result=recognize(data)
            elif self.path=="/api/save": result=save(json.loads(data))
            else: return self.send_error(404)
            self.reply(result)
        except (ValueError,KeyError,TypeError,sqlite3.Error) as e: self.reply({"error":str(e)},status=400)
        except (subprocess.SubprocessError,OSError): self.reply({"error":"本机处理失败，可重试或手动录入指标。"},status=500)

if __name__=="__main__":
    ROOT.mkdir(parents=True,exist_ok=True)
    httpd=ThreadingHTTPServer(("127.0.0.1",PORT),Handler)
    print(f"http://{HOST}",flush=True)
    if "--open" in sys.argv: webbrowser.open(f"http://{HOST}")
    httpd.serve_forever()

