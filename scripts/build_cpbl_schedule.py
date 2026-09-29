#!/usr/bin/env python3
import html,json,re,sys,urllib.request
from pathlib import Path
YEAR=int(sys.argv[1]) if len(sys.argv)>1 else 2025
if YEAR!=2025: raise RuntimeError("historical builder currently supports 2025")
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/f"data/schedule-{YEAR}.json"
URL="https://zxc22.idv.tw/cpbl36/allgame.asp?pagesize=500"
req=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0 Ballpark-Memories/1.0"})
with urllib.request.urlopen(req,timeout=30) as r: raw=r.read().decode("big5","ignore")
text=html.unescape(re.sub(r"<[^>]+>"," ",raw)); text=re.sub(r"\s+"," ",text)
teams=["統一7-ELEVEn獅","中信兄弟","味全龍","富邦悍將","樂天桃猿","台鋼雄鷹"]
tp="("+"|".join(map(re.escape,teams))+")"
pat=re.compile(r"\b(\d{1,3})\s+(2025)/(\d{1,2})/(\d{1,2})\s*\([^)]*\)\s+(\S+)\s+"+tp+r"\s+"+tp+r"\s+(\d+)\s*:\s*(\d+)\s+(\d+)小時(\d+)分\s+(\d+)")
by={}
for m in pat.finditer(text):
 sno=int(m.group(1)); date=f"2025-{int(m.group(3)):02d}-{int(m.group(4)):02d}"
 by[sno]={"id":f"2025-A-{sno}","date":date,"start":date+"T00:00:00","venue":m.group(5),"away":m.group(6),"home":m.group(7),"status":"FINISHED","awayScore":int(m.group(8)),"homeScore":int(m.group(9)),"gameDurationMinutes":int(m.group(10))*60+int(m.group(11)),"attendance":int(m.group(12)),"source":"zxc22 historical CPBL archive","sourceUrl":URL}
missing=[n for n in range(1,361) if n not in by]
if len(by)!=360 or missing: raise RuntimeError(f"safety stop: expected games 1..360, got {len(by)}, missing={missing[:30]}")
games=[by[n] for n in range(1,361)]
OUT.write_text(json.dumps(games,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("wrote",len(games),"2025 games from zxc22 archive")
