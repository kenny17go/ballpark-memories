#!/usr/bin/env python3
import io,json,re,sys,urllib.request
from pathlib import Path
YEAR=int(sys.argv[1]) if len(sys.argv)>1 else 2025
if YEAR!=2025: raise RuntimeError("historical PDF builder currently supports 2025")
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/f"data/schedule-{YEAR}.json"
try:
 import pdfplumber
except ImportError:
 raise RuntimeError("pdfplumber is required")
URL="https://www.cpbl.com.tw/files/GameDets/{y}/A/CPBL%E4%B8%80%E8%BB%8D%E4%BE%8B%E8%A1%8C%E8%B3%BD_{y}{m:02d}.pdf"
team_pat=r"(統一[-]?7-ELEVEn獅|統一7-ELEVEn獅|中信兄弟|味全龍|富邦悍將|樂天桃猿|台鋼雄鷹)"
def norm_team(s): return s.replace("統一-7-ELEVEn獅","統一7-ELEVEn獅")
by={}
for month in range(3,11):
 url=URL.format(y=YEAR,m=month)
 with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 Ballpark-Memories/1.0"}),timeout=30) as r:data=r.read()
 with pdfplumber.open(io.BytesIO(data)) as pdf:
  text="\n".join((p.extract_text(x_tolerance=2,y_tolerance=3) or "") for p in pdf.pages)
 current_date=None
 for raw in text.splitlines():
  line=" ".join(raw.split())
  dm=re.search(r"(\d{1,2})/(\d{1,2})\s*\(",line)
  if dm: current_date=f"{YEAR}-{int(dm.group(1)):02d}-{int(dm.group(2)):02d}"
  gm=re.search(r"\b(\d{1,3})\b\s+"+team_pat+r"\s+(\d+|VS\.?)[：:]?\s*(\d+)?\s*"+team_pat,line,re.I)
  if not gm or not current_date: continue
  sno=int(gm.group(1)); away=norm_team(gm.group(2)); home=norm_team(gm.group(5))
  score1=gm.group(3); score2=gm.group(4)
  rest=line[gm.end():]
  venue=(rest.split()[0] if rest else "").strip()
  if venue in ("VS.","VS",""): 
   parts=rest.split(); venue=parts[1] if len(parts)>1 else ""
  finished=score1.upper() not in ("VS","VS.")
  row={"id":f"{YEAR}-A-{sno}","date":current_date,"start":current_date+"T00:00:00","away":away,"home":home,"venue":venue,"status":"FINISHED" if finished else "POSTPONED","source":"CPBL official monthly PDF"}
  if finished and score2 is not None: row.update({"awayScore":int(score1),"homeScore":int(score2)})
  # Later monthly PDFs contain replayed postponed games; latest actual appearance wins.
  if finished or sno not in by: by[sno]=row
games=[by[k] for k in sorted(by)]
missing=[n for n in range(1,361) if n not in by]
if len(games)!=360 or missing: raise RuntimeError(f"safety stop: expected games 1..360, got {len(games)}, missing={missing[:30]}")
OUT.write_text(json.dumps(games,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("wrote",len(games),"official 2025 games from monthly CPBL PDFs")
