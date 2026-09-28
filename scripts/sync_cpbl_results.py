#!/usr/bin/env python3
import json,re,urllib.request,urllib.parse,http.cookiejar
from datetime import date,timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCHEDULE=ROOT/"data/schedule-2026.json"
RESULTS=ROOT/"data/results-2026.json"
BASE="https://cpbl.com.tw"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Ballpark-Memories/1.0"
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

def request(url,data=None,headers=None,timeout=20):
    h={"User-Agent":UA,**(headers or {})}
    body=urllib.parse.urlencode(data).encode() if data is not None else None
    req=urllib.request.Request(url,data=body,headers=h)
    with opener.open(req,timeout=timeout) as r:
        return r.read().decode("utf-8","ignore")

def csrf():
    html=request(BASE+"/schedule?KindCode=A")
    patterns=[
        r"RequestVerificationToken['\"]?\s*[:=]\s*['\"]([^'\"]{20,})",
        r'name="__RequestVerificationToken"[^>]*value="([^"]+)"'
    ]
    for p in patterns:
        m=re.search(p,html)
        if m:return m.group(1)
    raise RuntimeError("CPBL CSRF token not found")

def api_post(endpoint,data,token):
    raw=request(BASE+endpoint,data,{
        "Content-Type":"application/x-www-form-urlencoded",
        "X-Requested-With":"XMLHttpRequest",
        "RequestVerificationToken":token,
        "Referer":BASE+"/schedule?KindCode=A"
    },30)
    return json.loads(raw)

def norm_team(v):
    v=(v or "").replace("7-ELEVEn","").replace("7-ELEVEN","")
    return re.sub(r"[^\w\u4e00-\u9fff]","",v)

def same_team(a,b):
    a,b=norm_team(a),norm_team(b)
    return a==b or (a and b and (a in b or b in a))

def duration_minutes(v):
    s=re.sub(r"\D","",str(v or ""))
    if not s:return None
    # CPBL commonly returns HHMMSS (e.g. 032300).
    s=s.zfill(6)[-6:]
    h,m,sec=int(s[:2]),int(s[2:4]),int(s[4:])
    return h*60+m+(1 if sec>=30 else 0)

def zxc22_attendance(game,sno):
    want=(game.get("date") or "").replace("-","/")
    away,home=norm_team(game.get("away")),norm_team(game.get("home"))
    for team in range(1,7):
        try:
            html=request(f"https://zxc22.idv.tw/last10.asp?team={team}",timeout=10)
            txt=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",html))
            m=re.search(rf"\b0*{int(sno)}\b\s+{re.escape(want)}\s+.*?(\d{{3,6}})\s+(?:勝|敗|和)",txt)
            if not m:continue
            vicinity=norm_team(txt[m.start():m.start()+500])
            if away not in vicinity or home not in vicinity:continue
            return int(m.group(1)),f"https://zxc22.idv.tw/last10.asp?team={team}"
        except Exception:
            pass
    return None,None

schedule=json.loads(SCHEDULE.read_text(encoding="utf-8"))
results=json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {}
today=date.today()
window_start=(today-timedelta(days=4)).isoformat()
today_iso=today.isoformat()
candidates=[g for g in schedule if str(g.get("id","")).startswith("2026-A-")
            and window_start<=g.get("date","")<=today_iso]
if len(candidates)>24:
    raise RuntimeError(f"safety stop: unexpected candidate window of {len(candidates)} games")
print(f"checking {len(candidates)} recent games ({window_start}..{today_iso})")

token=csrf()
payload=api_post("/schedule/getgamedatas",{
    "calendar":f"{today.year}/01/01","location":"","kindCode":"A"
},token)
if not payload.get("Success"):
    raise RuntimeError("CPBL schedule API returned Success=false")
official=json.loads(payload.get("GameDatas") or "[]")
by_sno={}
for x in official:
    try:sno=int(x.get("GameSno"))
    except (TypeError,ValueError):continue
    # Same GameSno may have postponed/reserved historical rows; latest execution date wins.
    stamp=str(x.get("PreExeDate") or x.get("GameDate") or x.get("GameDateTimeS") or "")
    if sno not in by_sno or stamp>by_sno[sno][0]:
        by_sno[sno]=(stamp,x)

changed=0
for g in candidates:
    gid=str(g["id"]);sno=int(gid.rsplit("-",1)[-1])
    pair=by_sno.get(sno)
    if not pair:
        print(gid,"skip: not in official API");continue
    x=pair[1]
    api_date=str(x.get("GameDate") or x.get("GameDateTimeS") or "")[:10].replace("/","-")
    if api_date!=g.get("date") or not same_team(x.get("VisitingTeamName"),g.get("away")) or not same_team(x.get("HomeTeamName"),g.get("home")):
        print(gid,"skip: identity validation failed",api_date,x.get("VisitingTeamName"),x.get("HomeTeamName"));continue
    away_score,home_score=x.get("VisitingScore"),x.get("HomeScore")
    ended=bool(x.get("GameDateTimeE"))
    if away_score is None or home_score is None or not ended:
        print(gid,"skip: not finished");continue
    row=dict(results.get(gid,{}))
    row.update({
        "date":g.get("date"),"venue":g.get("venue"),"away":g.get("away"),"home":g.get("home"),
        "status":"FINISHED","awayScore":int(away_score),"homeScore":int(home_score),
        "resultSource":"CPBL official","resultSourceUrl":f"{BASE}/box/index?year={today.year}&kindCode=A&gameSno={sno}"
    })
    mapping={"MvpName":"mvp","WinningPitcherName":"winningPitcher","LoserPitcherName":"losingPitcher"}
    for src,dst in mapping.items():
        if x.get(src):row[dst]=x[src]
        else:row.pop(dst,None)
    mins=duration_minutes(x.get("GameDuringTime"))
    if mins:row["gameDurationMinutes"]=mins

    # Official box endpoint is the preferred attendance source.
    try:
        box=api_post("/box/getlive",{"GameSno":str(sno),"KindCode":"A","Year":str(today.year),
             "PrevOrNext":"","PresentStatus":""},token)
        curt=json.loads(box.get("CurtGameDetailJson") or "{}") if box.get("Success") else {}
        # Schedule CloserName can mean the last pitcher, not a credited save.
        # Box detail exposes the official credited closer; use only this for savePitcher.
        closer=curt.get("CloserPitcherName")
        if closer: row["savePitcher"]=closer
        else: row.pop("savePitcher",None)
        audience=curt.get("AudienceCntBackend") or curt.get("AudienceCnt")
        if audience not in (None,""):
            row["attendance"]=int(str(audience).replace(",",""))
            row["attendanceSource"]="CPBL official"
            row["attendanceSourceUrl"]=f"{BASE}/box/index?year={today.year}&kindCode=A&gameSno={sno}"
    except Exception as e:
        print(gid,"official attendance skip:",e)

    if not row.get("attendance"):
        att,src=zxc22_attendance(g,sno)
        if att:
            row["attendance"]=att;row["attendanceSource"]="zxc22";row["attendanceSourceUrl"]=src

    if row!=results.get(gid):
        results[gid]=row;changed+=1

if changed>len(candidates):
    raise RuntimeError(f"safety stop: changed {changed} exceeds {len(candidates)} candidates")
RESULTS.write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("updated",changed,"games")
