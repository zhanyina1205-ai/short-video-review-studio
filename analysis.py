import re
import unicodedata
from decimal import Decimal

# 平台原始字段、分组、计数映射、解读
FIELDS = {}
def group(section, entries):
    for label, key, meaning in entries:
        FIELDS[label] = (section, key, meaning)

group("触达", [
 ("播放量","plays","用于衡量播放规模；可能包含同一观众的多次播放。"),
 ("观看量","views","作为本平台观看规模的基线，可用于计算同口径互动率。"),
 ("观看人数","","记录独立观众规模，与播放次数分开比较。"),
 ("曝光量","","作品获得展示的规模，结合进入后的观看量观察封面表现。"),
 ("封面点击率","","反映看到封面后进入的比例，下一条可单独测试首图或标题。"),
 ("流量激励","","平台单列的支持量，需保留这一背景比较分发效果。")])
group("留存", [
 ("2s跳出率","","前两秒离开的比例，观察首帧能否兑现标题。"),
 ("5s完播率","","看到第五秒的比例，适合检验第一个内容变化出现的时机。"),
 ("完播率","","看至结尾的比例，比较时优先选择相近片长。"),
 ("平均播放时长","","平均每次观看的秒数，可以定位前段是否承载了核心内容。"),
 ("平均播放占比","","平均观看长度占全片的比例，可与播放秒数一起判断。")])
group("互动",[(k,v,s) for k,v,s in [
 ("点赞量","likes","表明观众给出了即时正向反馈。"),("评论量","comments","可结合评论原话梳理疑问，作为选题线索。"),
 ("收藏量","saves","观众保存了内容，可对照评论检验其使用场景。"),("分享量","shares","观众主动传播内容，可作为系列传播的比较基线。"),
 ("弹幕量","","观看过程中发出的弹幕数量。"),("点赞率","","比较同平台每次观看获得点赞的频率。"),("评论率","","比较同平台触发讨论的频率。"),("分享率","","比较同平台触发传播的频率。"),("收藏率","","比较同平台触发保存的频率。")]])
group("涨粉与受众",[("吸粉量","gained","本条带来的新增关注，可作为 IP 转化结果。"),("吸粉率","","观察作品将流量转为关注的效率。"),("脱粉量","lost","与吸粉量一起计算净增关注。"),("脱粉率","","记录取消关注的比例，单条数值无法定位原因。"),("不感兴趣量","","明确表达不感兴趣的反馈数量。"),("不感兴趣率","","观察负反馈随选题和受众的变化。"),("主页访问量","","衡量观看后继续了解账号的人次。")])
group("业务",[("私信量","","观察由内容引发的一对一互动。"),("有效咨询量","","按自己的有效咨询定义衡量业务结果。")])
ALIASES={"曝光数":"曝光量","笔记观看数":"观看量","笔记观看量":"观看量","曝光点击率":"封面点击率","2秒跳出率":"2s跳出率","5秒完播率":"5s完播率","浏览量":"观看量","观看数":"观看量","点赞数":"点赞量","评论数":"评论量","分享数":"分享量","收藏数":"收藏量","涨粉量":"吸粉量","新增关注":"吸粉量","笔记曝光量":"曝光量"}
NUM=r"(?:\d[\d,]*(?:\.\d+)?|\.\d+)(?:万|亿|千|%|秒|s)?"
def clean(s):
    return unicodedata.normalize("NFKC",s).replace(" ","").replace("−","-").replace("↗","").replace("↘","").lower()

def number(s):
    m=re.fullmatch(r"(\d+(?:\.\d+)?|\.\d+)(万|亿|千|%|秒|s)?",clean(s).replace(",",""))
    if m:
        return Decimal(m[1])*{"万":10000,"亿":100000000,"千":1000}.get(m[2],1)

def extract(blocks):
    found={}
    for b in blocks:
        t=clean(b["t"]).strip("↑↓↗↘")
        inc=re.search(r"获得([\d,]+)流量激励",t)
        if inc: found["流量激励"]=[inc[1],""]
        for name in sorted([*FIELDS,*ALIASES],key=len,reverse=True):
            if not t.startswith(name): continue
            label=ALIASES.get(name,name)
            inline=t[len(name):].lstrip(":")
            if inline and not re.fullmatch(NUM,inline): continue
            near=sorted((p for p in blocks if abs(p["x"]-b["x"])<.065 and 0<p["y"]-b["y"]<.059),key=lambda p:p["y"])
            val=inline or next((clean(p["t"]) for p in near if re.fullmatch(NUM,clean(p["t"]))),"")
            if val and ("率" not in label and "占比" not in label or "%" in val):
                comp=next((p["t"] for p in near if "往期" in p["t"]),"")
                found[label]=[val,comp]
            break
    fulltext=" ".join(clean(b["t"]) for b in blocks)
    change=re.search(r"播放量较往期(上涨|下降)?([+-]?[\d.]+%)",fulltext)
    if change and "播放量" in found:
        pct=change[2]
        if change[1]=="下降" and not pct.startswith("-"): pct="-"+pct.lstrip("+")
        found["播放量"][1]="较往期 "+pct
    prefs=re.search(r"([\u4e00-\u9fff]{2,8})最多[,，]相比大盘",fulltext)
    if prefs: found["观众兴趣"]=[prefs[1],"相较大盘更显著"]
    return found

def make_report(d):
    fields=d.pop("fields")
    rows=[]; counts={}; values={}
    for name,val,comparison in fields:
        if not name.strip() or not val.strip(): continue
        section,key,meaning=FIELDS.get(name,("补充数据","","结合本条目标留作后续同口径比较。"))
        n=number(val)
        if name in FIELDS and (n is None or (("率" in name or "占比" in name) and ("%" not in val or n>100))):
            raise ValueError("请检查「"+name+"」的数值或单位")
        if name in values: raise ValueError("同一指标出现两次："+name)
        if key and n is not None:
            if int(n)!=n or "%" in val: raise ValueError(name+"需填次数或人数")
            counts[key]=int(n)
        if name=="观众兴趣": section,meaning="受众","可用作这条作品的受众线索，单次画像不足以推断账号长期受众。"
        delta=re.search(r"往期[^+\d-]*([+-]?[\d.]+)%",clean(comparison))
        if delta:
            change=Decimal(delta[1])
            direction="增加" if change>0 else "减少" if change<0 else "持平"
            meaning+=f" 本条较往期{direction}"+(f" {abs(change)}%。" if change else "。")
        if name in ("2s跳出率","5s完播率","完播率") and n is not None:
            action={"2s跳出率":"在开头两秒离开","5s完播率":"看到第 5 秒","完播率":"看完了作品"}[name]
            meaning=f"每百次播放约有 {n:.0f} 次{action}。"+meaning
        values[name]=val
        rows.append([section,name,val,comparison or "本次快照",meaning])
    if not rows: raise ValueError("请至少核对一项指标")
    reach=counts.get("plays",counts.get("views"))
    for row in rows:
        key=FIELDS.get(row[1],("","",""))[1]
        if reach and key in ("likes","saves","comments","shares","gained","lost"):
            row[4]+=f" 按本条约每万次播放或观看折算为 {counts[key]*10000/reach:.1f}。"
    goal=d["goal"]
    if goal=="涨粉" and ("吸粉率" in values or "gained" in counts):
        k="吸粉率" if "吸粉率" in values else "吸粉量"
        action="结尾只改一处：说明关注后下一期可以看到什么。比较同平台、相近播放规模作品的吸粉率。"
    elif goal=="咨询" and "有效咨询量" in values:
        k="有效咨询量";action="只改结尾的咨询入口，给出一个和内容相关的具体提问，对比同观察窗口的有效咨询量。"
    elif goal=="互动" and any(k in values for k in ["收藏量","评论量","点赞量","分享量"]):
        k=next(k for k in ["收藏量","评论量","点赞量","分享量"] if k in values)
        action={"收藏量":"只调整总结页，给出一份可保存的要点清单；比较每千次观看的收藏数。","评论量":"只改结尾提问，提供两个可选答案，对比评论率。","点赞量":"把一个可立即理解的成果移到前段，对比点赞率。","分享量":"增加一个具体适用场景，对比分享率。"}[k]
    elif "5s完播率" in values:
        k="5s完播率";action="对照原片查看第 2～5 秒。若关键结果仍未出现，下一条仅将首次结果展示提前，比较 5 秒完播率。"
    elif "2s跳出率" in values:
        k="2s跳出率";action="保留主体剪辑，只将首帧换成结果画面，比较 2 秒跳出率是否下降。"
    else:
        k=next(iter(values));action="保留同题材和相近片长，只调整第一句或首帧；补录 2 秒跳出率或开头留存后比较。"
    summary=f"按「{goal}」视角，本条{k}为 {values[k]}。"
    if reach is not None: summary+=f"已记录约 {reach:,} 次播放或观看。"
    if "2s跳出率" in values and "5s完播率" in values:
        early=100-number(values["2s跳出率"])
        five=number(values["5s完播率"])
        if early>five: summary+=f" 越过两秒的比例约 {early}%，看到五秒的比例为 {five}%，可先核对这段剪辑。"
    if goal=="涨粉" and "gained" not in counts and "吸粉率" not in values: summary+=" 尚缺吸粉数据，暂时只能判断观看或互动。"
    if goal=="咨询" and "有效咨询量" not in values: summary+=" 补充有效咨询量后才能评估业务结果。"
    if "gained" in counts and "lost" in counts: summary+=f" 净增关注 {counts['gained']-counts['lost']}。"
    d.update(metrics=rows,counts=counts,highlights=[[n,values[n]] for n in dict.fromkeys([k,*values])][:4],summary=summary,
        note=f"{d['platform']} · 发布 {d['published'] or '待补'} · 观察 {d['observed']} · 平台缩写数按展示精度折算",
        sections=[["下一条优先实验",action],["复测口径","按本次发布到观察的相同时长复测，记录平台、片长与流量激励。样本积累前，把结果作为实验基线。"]])
    return d

