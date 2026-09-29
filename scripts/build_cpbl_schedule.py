#!/usr/bin/env python3
import json,re,sys,urllib.request,urllib.parse,http.cookiejar
from pathlib import Path
YEAR=int(sys.argv[1]) if len(sys.argv)>1 else 2025
if YEAR not in (2025,2026): raise RuntimeError("unsupported year")
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/f"data/schedule-{YEAR}.json"; BASE="https://cpbl.com.tw"
jar=http.cookiejar.CookieJar(); opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def req(url,data=None,headers=None):
 h={"User-Agent":"Mozilla/5.0 Ballpark-Memories/1.0",**(headers or {})}; body=urllib.parse.urlencode(data).encode() if data else None
 with opener.open(urllib.request.Request(url,data=body,headers=h),timeout=30) as r:return r.read().decode("utf-8","ignore")
html=req(BASE+"/schedule?KindCode=A"); m=re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"',html)
if not m: raise RuntimeError("CPBL CSRF token not found")
token=m.group(1); raw=req(BASE+"/schedule/getgamedatas",{"calendar":f"{YEAR}/01/01","location":"","kindCode":"A"},{"X-Requested-With":"XMLHttpRequest","RequestVerificationToken":token,"Referer":BASE+"/schedule?KindCode=A"})
payload=json.loads(raw)
if not payload.get("Success"): raise RuntimeError("CPBL API Success=false")
rows=json.loads(payload.get("GameDatas") or "[]"); by={}
for x in rows:
 try:sno=int(x.get("GameSno"))
 except:continue
 if not 1<=sno<=400:continue
 stamp=str(x.get("PreExeDate") or x.get("GameDate") or x.get("GameDateTimeS") or "")
 if sno not in by or stamp>by[sno][0]:by[sno]=(stamp,x)
games=[]
for sno,(_,x) in sorted(by.items()):
 d=str(x.get("GameDate") or x.get("GameDateTimeS") or "")[:10].replace("/","-")
 if not d.startswith(str(YEAR)):continue
 start=str(x.get("GameDateTimeS") or "")
 if "/" in start:start=start.replace("/","-")
 games.append({"id":f"{YEAR}-A-{sno}","date":d,"start":start,"away":x.get("VisitingTeamName") or "","home":x.get("HomeTeamName") or "","venue":x.get("FieldAbbe") or x.get("FieldName") or "","status":"SCHEDULED","source":"CPBL"})
if YEAR==2025 and len(games)!=360:raise RuntimeError(f"safety stop: expected 360 2025 games, got {len(games)}")
OUT.write_text(json.dumps(games,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print("wrote",len(games),"games to",OUT)
