#!/usr/bin/env python3
import json,re,urllib.request
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCHEDULE=ROOT/"data/schedule-2026.json"
RESULTS=ROOT/"data/results-2026.json"
UA={"User-Agent":"Mozilla/5.0 Ballpark-Memories/1.0"}

def get(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=20) as r:
        return r.read().decode("utf-8","ignore")

def text(html):
    return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",html)).strip()

def pick(pattern,s):
    m=re.search(pattern,s,re.I)
    return m.group(1).strip() if m else None

schedule=json.loads(SCHEDULE.read_text(encoding="utf-8"))
results=json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {}
today=date.today().isoformat()
changed=0
for g in schedule:
    gid=str(g.get("id",""))
    if not gid.startswith("2026-A-") or g.get("date","9999")>today: continue
    sno=gid.rsplit("-",1)[-1]
    try:
        html=get("https://stats.cpbl.com.tw/schedule/"+gid)
        s=text(html)
        if "已結束" not in s: continue
        row=dict(results.get(gid,{}))
        row.update({"date":g.get("date"),"venue":g.get("venue"),"away":g.get("away"),"home":g.get("home"),"status":"FINISHED",
                    "resultSource":"CPBL official","resultSourceUrl":"https://stats.cpbl.com.tw/schedule/"+gid})
        score=re.search(r"\b(\d+)\s*:\s*(\d+)\b",s)
        if score: row["awayScore"],row["homeScore"]=score.group(1),score.group(2)
        for key,label in [("mvp","MVP"),("winningPitcher","勝投"),("losingPitcher","敗投"),("savePitcher","救援成功")]:
            v=pick(label+r"\s*(?:[^#\d]{0,30}#\d+\s*)?([^\s]+)",s)
            if v: row[key]=v
        try:
            news=text(get(f"https://cpbl.com.tw/box/news?gameSno={int(sno)}&kindCode=A&year=2026"))
            m=re.search(r"(?:吸引|湧入|進場|入場)[^。]{0,35}?([\d,]{3,6})\s*人",news)
            if not m: m=re.search(r"([\d,]{3,6})\s*人(?:進場|入場)",news)
            if m: row["attendance"]=int(m.group(1).replace(",",""))
        except Exception: pass
        if row!=results.get(gid):
            results[gid]=row;changed+=1
    except Exception as e:
        print(gid,"skip:",e)
RESULTS.write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("updated",changed,"games")
