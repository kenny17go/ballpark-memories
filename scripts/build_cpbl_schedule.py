#!/usr/bin/env python3
import html,json,re,sys,urllib.parse,urllib.request
from pathlib import Path
YEAR=int(sys.argv[1]) if len(sys.argv)>1 else 2025
if YEAR!=2025: raise RuntimeError("historical builder currently supports 2025")
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/f"data/schedule-{YEAR}.json"
BASE="https://zxc22.idv.tw/cpbl36/allgame.asp"
teams=["統一7-ELEVEn獅","中信兄弟","味全龍","富邦悍將","樂天桃猿","台鋼雄鷹"]
aliases={"統一獅":"統一7-ELEVEn獅","統一7-ELEVEN獅":"統一7-ELEVEn獅"}
def clean(s): return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",s))).strip()
def team(s): return aliases.get(s.strip(),s.strip())
def fetch(page):
 data=urllib.parse.urlencode({"pagesize":400,"page":page}).encode()
 req=urllib.request.Request(BASE,data=data,headers={"User-Agent":"Mozilla/5.0 Ballpark-Memories/1.0","Content-Type":"application/x-www-form-urlencoded"})
 with urllib.request.urlopen(req,timeout=30) as r:
  b=r.read()
  for enc in ("utf-8","big5","cp950"):
   try:return b.decode(enc)
   except UnicodeDecodeError: pass
  return b.decode("big5","ignore")
by={}
for page in range(1,3):
 raw=fetch(page)
 rows=re.findall(r"<tr\b[^>]*>(.*?)</tr>",raw,re.I|re.S)
 for row in rows:
  cells=[clean(x) for x in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>",row,re.I|re.S)]
  if not cells: continue
  joined=" | ".join(cells)
  sno_m=re.search(r"(?<!\d)(\d{1,3})(?!\d)",cells[0] if cells else "")
  date_m=re.search(r"2025[/-](\d{1,2})[/-](\d{1,2})",joined)
  found=[t for t in teams if t in joined]
  if len(found)<2:
   found=[team(x) for x in cells if team(x) in teams]
  score_m=re.search(r"(?<!\d)(\d{1,2})\s*[:：-]\s*(\d{1,2})(?!\d)",joined)
  if not (sno_m and date_m and len(found)>=2 and score_m): continue
  sno=int(sno_m.group(1))
  if not 1<=sno<=360: continue
  date=f"2025-{int(date_m.group(1)):02d}-{int(date_m.group(2)):02d}"
  # zxc22 table order is away then home.
  away,home=found[0],found[1]
  venue=""
  for x in cells:
   if any(k in x for k in ("洲際","桃園","天母","新莊","台南","澄清湖","大巨蛋","嘉義","花蓮","斗六")):
    venue=x; break
  dur=re.search(r"(\d+)\s*小時\s*(\d+)\s*分",joined)
  att=re.search(r"(?:觀眾|人數)?\s*([\d,]{3,})\s*(?:人)?",joined)
  g={"id":f"2025-A-{sno}","date":date,"start":date+"T00:00:00","venue":venue,"away":away,"home":home,"status":"FINISHED","awayScore":int(score_m.group(1)),"homeScore":int(score_m.group(2)),"source":"zxc22 historical CPBL archive","sourceUrl":BASE}
  if dur:g["gameDurationMinutes"]=int(dur.group(1))*60+int(dur.group(2))
  if att:
   n=int(att.group(1).replace(",",""))
   if n>=100:g["attendance"]=n
  by[sno]=g
 if len(by)>=360: break
missing=[n for n in range(1,361) if n not in by]
if len(by)!=360 or missing: raise RuntimeError(f"safety stop: expected games 1..360, got {len(by)}, missing={missing[:30]}")
games=[by[n] for n in range(1,361)]
OUT.write_text(json.dumps(games,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("wrote",len(games),"2025 games from zxc22 archive")
