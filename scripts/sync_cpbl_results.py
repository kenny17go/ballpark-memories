#!/usr/bin/env python3
import json,re,urllib.request
from datetime import date,timedelta
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

def norm_team(v):
    v=(v or "").replace("7-ELEVEn","").replace("7-ELEVEN","")
    return re.sub(r"[^\w\u4e00-\u9fff]","",v).replace("悍將","").replace("雄鷹","").replace("桃猿","").replace("兄弟","").replace("龍","").replace("獅","")

def zxc22_attendance(game, sno):
    # zxc22 exposes recent per-team game rows with game number/date/teams/score/attendance.
    # Search all six team pages, then require game no + date + both teams before accepting.
    want_date=(game.get("date") or "").replace("-","/")
    away=norm_team(game.get("away")); home=norm_team(game.get("home"))
    for team in range(1,7):
        page=text(get(f"https://zxc22.idv.tw/last10.asp?team={team}"))
        m=re.search(rf"\b0*{int(sno)}\b\s+{re.escape(want_date)}\s+.*?(\d{{3,6}})\s+(?:勝|敗|和)",page)
        if not m: continue
        # Validate the matched row vicinity, not game number alone.
        pos=m.start(); vicinity=page[pos:pos+500]
        if away and away not in norm_team(vicinity): continue
        if home and home not in norm_team(vicinity): continue
        return int(m.group(1)), f"https://zxc22.idv.tw/last10.asp?team={team}"
    return None,None

schedule=json.loads(SCHEDULE.read_text(encoding="utf-8"))
results=json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {}
today=date.today()
# Incremental sync only: recent games are enough for a daily result updater.
# Existing historical rows stay untouched; this avoids hundreds of CPBL requests.
window_start=(today-timedelta(days=4)).isoformat()
today_iso=today.isoformat()
candidates=[g for g in schedule if str(g.get("id","")).startswith("2026-A-")
            and window_start <= g.get("date","") <= today_iso]
print(f"checking {len(candidates)} recent games ({window_start}..{today_iso})")
changed=0
for g in candidates:
    gid=str(g.get("id",""))
    sno=gid.rsplit("-",1)[-1]
    try:
        html=get("https://stats.cpbl.com.tw/schedule/"+gid)
        s=text(html)
        # Do not trust page-wide "已結束": the schedule page can contain other games.
        # A finished target game must expose a target-game score and must not say target game is pending.
        detail=s.split("賽事詳情",1)[-1]
        if "未開始" in detail[:500] or "比賽準備中" in detail[:500]:
            continue
        score=re.search(r"\b(\d{1,2})\s*:\s*(\d{1,2})\b",detail[:1800])
        if not score:
            continue
        row=dict(results.get(gid,{}))
        row.update({"date":g.get("date"),"venue":g.get("venue"),"away":g.get("away"),"home":g.get("home"),"status":"FINISHED",
                    "resultSource":"CPBL official","resultSourceUrl":"https://stats.cpbl.com.tw/schedule/"+gid})
        row["awayScore"],row["homeScore"]=int(score.group(1)),int(score.group(2))
        for key,label in [("mvp","MVP"),("winningPitcher","勝投"),("losingPitcher","敗投"),("savePitcher","救援成功")]:
            v=pick(label+r"\s*(?:[^#\d]{0,30}#\d+\s*)?([^\s]+)",s)
            if v: row[key]=v
        try:
            news=text(get(f"https://cpbl.com.tw/box/news?gameSno={int(sno)}&kindCode=A&year=2026"))
            m=re.search(r"(?:吸引|湧入|進場|入場)[^。]{0,35}?([\d,]{3,6})\s*人",news)
            if not m: m=re.search(r"([\d,]{3,6})\s*人(?:進場|入場)",news)
            if m:
                row["attendance"]=int(m.group(1).replace(",",""))
                row["attendanceSource"]="CPBL official"
                row["attendanceSourceUrl"]=f"https://cpbl.com.tw/box/news?gameSno={int(sno)}&kindCode=A&year=2026"
        except Exception: pass
        if not row.get("attendance") or row.get("attendanceSource")!="CPBL official":
            try:
                attendance,source=zxc22_attendance(g,sno)
                if attendance:
                    row["attendance"]=attendance
                    row["attendanceSource"]="zxc22"
                    row["attendanceSourceUrl"]=source
            except Exception as e:
                print(gid,"zxc22 attendance skip:",e)
        if row!=results.get(gid):
            results[gid]=row;changed+=1
    except Exception as e:
        print(gid,"skip:",e)
# Safety guard: a normal daily run should never rewrite a large part of the season.
# Fail closed so a CPBL HTML change cannot corrupt the published data file.
if changed > len(candidates):
    raise RuntimeError(f"safety stop: changed {changed} exceeds {len(candidates)} candidates")
if len(candidates) > 24:
    raise RuntimeError(f"safety stop: unexpected candidate window of {len(candidates)} games")
RESULTS.write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("updated",changed,"games")
