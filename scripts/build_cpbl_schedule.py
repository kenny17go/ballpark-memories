#!/usr/bin/env python3
"""Build data/schedule-2025.json (CPBL 2025 regular season, GAME 1..360) from zxc22.

Data path
  1. by_total2.asp                      -> discover every venue link (by_place.asp?place=<id>&flag=-1)
  2. by_place.asp?place=<id>&flag=-1    -> ALL games of that venue on ONE page (no paging)
The union of all venue pages is the full season (each game is played at exactly one venue).

Every venue page prints its own totals ("合計:66場，總人數:1328772人"). A page whose parsed
rows do not match those totals is rejected, so a truncated page can never slip through.
The final GAME 1..360 check is unchanged and still blocks output.
"""
import argparse, datetime, html, json, re, sys, time, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SITE="https://zxc22.idv.tw/cpbl36/"; TOTAL_URL=SITE+"by_total2.asp"; PLACE_URL=SITE+"by_place.asp?place={}&flag=-1"; ALLGAME_URL=SITE+"allgame.asp?flag=-1"; SOURCE_URL=SITE+"allgame.asp"
KNOWN_PLACES=[1,3,4,6,7,9,10,11,13,15,16]
TEAMS=["統一7-ELEVEn獅","中信兄弟","味全龍","富邦悍將","樂天桃猿","台鋼雄鷹"]; ALIASES={"統一獅":"統一7-ELEVEn獅"}
CANON={t.lower():t for t in TEAMS}; CANON.update({k.lower():v for k,v in ALIASES.items()})
TEAM_RE="("+"|".join(re.escape(k) for k in sorted(CANON,key=len,reverse=True))+")"; L,R=r"[\(（]",r"[\)）]"; HR_E=r"\s*"+L+r"\d+"+R+r"\s*"+L+r"\d+"+R
REC=re.compile(r"(?<!\d)(\d{1,3})\s+(\d{4})/(\d{1,2})/(\d{1,2})\s*"+L+r"[^\s\)）]{1,2}"+R+r"\s*(\S+)\s+"+TEAM_RE+HR_E+r"\s*"+TEAM_RE+HR_E+r"\s*(\d+)\s*[:：]\s*(\d+)\s+([\d,]{3,7})(?!\d)",re.I)
PAGE_TOTAL=re.compile(r"合計\s*[:：]\s*(\d+)\s*場[^\d]{0,12}?總人數\s*[:：]\s*(\d+)")
DUR=r"(?:(\d+)\s*小時\s*(\d+)\s*分|(\d{1,2})\s*[:：]\s*(\d{2}))"
ALLREC=re.compile(r"(?<!\d)(\d{1,3})\s+(\d{4})/(\d{1,2})/(\d{1,2})\s+(\S+)\s+"+TEAM_RE+r"\s*"+TEAM_RE+r"\s*(\d+)\s*[:：]\s*(\d+)\s+"+DUR,re.I)
def decode(b,content_type=""):
 m=re.search(r"charset=([\w-]+)",content_type or "",re.I); encs=[]
 if m:
  cs=m.group(1).lower(); encs.append("cp950" if cs in ("big5","big5-hkscs") else cs)
 encs+=["utf-8","cp950"]
 for enc in encs:
  try:return b.decode(enc)
  except (UnicodeDecodeError,LookupError):pass
 return b.decode("cp950","replace")
def page_text(raw):
 raw=re.sub(r"(?is)<(script|style)\b.*?</\1>"," ",raw); return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]*>"," ",raw))).strip()
def make_fetcher(save_dir=None,from_dir=None):
 def slug(url):return re.sub(r"\W+","_",url.split("/cpbl36/")[-1]).strip("_")+".html"
 def fetch(url):
  name=slug(url)
  if from_dir:return decode((Path(from_dir)/name).read_bytes())
  last=None
  for attempt in range(3):
   try:
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 Ballpark-Memories/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r:raw=decode(r.read(),r.headers.get("Content-Type",""))
    if save_dir:
     Path(save_dir).mkdir(parents=True,exist_ok=True); (Path(save_dir)/name).write_text(raw,encoding="utf-8")
    time.sleep(.4); return raw
   except Exception as e:last=e; time.sleep(2*(attempt+1))
  raise RuntimeError(f"fetch failed: {url}: {last}")
 return fetch
def parse_games(text,year):
 out={}
 for m in REC.finditer(text):
  sno,y,mo,d=int(m[1]),int(m[2]),int(m[3]),int(m[4])
  if y!=year or not 1<=sno<=360:continue
  date=datetime.date(y,mo,d).isoformat()
  g={"id":f"{year}-A-{sno}","date":date,"start":date+"T00:00:00","venue":m[5],"away":CANON[m[6].lower()],"home":CANON[m[7].lower()],"status":"FINISHED","awayScore":int(m[8]),"homeScore":int(m[9]),"source":"zxc22 historical CPBL archive","sourceUrl":SOURCE_URL}
  att=int(m[10].replace(",",""))
  if att>=100:g["attendance"]=att
  if sno in out and out[sno]!=g:raise RuntimeError(f"conflicting records for GAME {sno} inside one page")
  out[sno]=g
 return out
def check_page(name,games,text):
 m=PAGE_TOTAL.search(text)
 if not m:raise RuntimeError(f"{name}: page total line not found; layout changed?")
 n,people=int(m[1]),int(m[2]); got=sum(g.get("attendance",0) for g in games.values())
 if len(games)!=n or got!=people:raise RuntimeError(f"{name}: page says {n} games / {people} people, parsed {len(games)} / {got}")
def discover_places(fetch):
 ids=[]
 try:
  for x in re.findall(r"by_place\.asp\?(?:[^\"'\s>]*?&(?:amp;)?)?place=(\d+)",fetch(TOTAL_URL)):
   if x not in ids:ids.append(x)
 except Exception as e:print("warn: could not read by_total2.asp:",e,file=sys.stderr)
 if not ids:print("warn: using built-in venue list",file=sys.stderr); ids=[str(x) for x in KNOWN_PLACES]
 return ids
def add_durations(by,fetch,year):
 try:
  text=page_text(fetch(ALLGAME_URL)); found={}
  for m in ALLREC.finditer(text):
   sno=int(m[1]); g=by.get(sno)
   if not g or int(m[2])!=year or g["date"]!=f"{year}-{int(m[3]):02d}-{int(m[4]):02d}":continue
   if (g["awayScore"],g["homeScore"])!=(int(m[9]),int(m[10])):continue
   found[sno]=int(m[11])*60+int(m[12]) if m[11] else int(m[13])*60+int(m[14])
  if len(found)==360:
   for sno,mins in found.items():by[sno]["gameDurationMinutes"]=mins
   print("game durations: 360/360")
  else:print(f"game durations skipped (allgame.asp gave {len(found)}/360)",file=sys.stderr)
 except Exception as e:print("game durations skipped:",e,file=sys.stderr)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("year",nargs="?",type=int,default=2025); ap.add_argument("--save-html"); ap.add_argument("--from-dir"); a=ap.parse_args()
 if a.year!=2025:raise RuntimeError("historical builder currently supports 2025")
 out=ROOT/f"data/schedule-{a.year}.json"; fetch=make_fetcher(a.save_html,a.from_dir); by={}
 for pid in discover_places(fetch):
  text=page_text(fetch(PLACE_URL.format(pid))); games=parse_games(text,a.year); check_page(f"place={pid}",games,text)
  for sno,g in games.items():
   if sno in by and by[sno]!=g:raise RuntimeError(f"GAME {sno} appears with different data on two venue pages")
   by[sno]=g
  print(f"place={pid}: {len(games)} games")
 missing=[n for n in range(1,361) if n not in by]
 if len(by)!=360 or missing:raise RuntimeError(f"safety stop: expected games 1..360, got {len(by)}, missing={missing[:30]}")
 per_team={t:sum(1 for g in by.values() if t in (g["away"],g["home"])) for t in TEAMS}
 if any(v!=120 for v in per_team.values()):raise RuntimeError(f"safety stop: every team must have 120 games, got {per_team}")
 if any(g["away"]==g["home"] for g in by.values()):raise RuntimeError("safety stop: same away/home")
 add_durations(by,fetch,a.year); out.write_text(json.dumps([by[n] for n in range(1,361)],ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print("wrote 360 2025 games from zxc22 archive")
if __name__=="__main__":main()
