"""Refresh official ARD Sounds embed without copying copyrighted audio.

Best-effort: require a trustworthy date/episode pairing; on provider markup changes
preserve the last known-good player and exit successfully.
"""
import datetime as dt
import html
import json
import pathlib
import re
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"ard.json"
SHOW="https://www.ardsounds.de/sendung/tagesschau-die-20-uhr-nachrichten-audio/urn%3Aard%3Ashow%3A771504b9e731d619/"
EPISODE=re.compile(r"urn:ard:episode:[0-9a-f]{16}",re.I)
ISO=re.compile(r"20\\d{2}-[01]\\d-[0-3]\\d")
GERMAN=re.compile(r"([0-3]?\\d)\\.([01]?\\d)\\.(20\\d{2})")
def main():
    req=urllib.request.Request(SHOW,headers={"User-Agent":"Mozilla/5.0 (Morgenbriefing personal podcast page)"})
    try:
        with urllib.request.urlopen(req,timeout=25) as response:
            raw=response.read().decode("utf-8")
    except Exception as e:
        print("ARD source unavailable; keeping last verified episode:",str(e))
        return
    page=html.unescape(raw).replace("\\\\u003A",":").replace("\\\\u002F","/").replace("\\/","/")
    candidates=[]
    today=dt.datetime.now(dt.timezone.utc).date()
    for match in EPISODE.finditer(page):
        nearby=page[max(0,match.start()-1000):match.end()+1000]
        dates=[]
        for iso in ISO.findall(nearby):
            try: dates.append(dt.date.fromisoformat(iso))
            except ValueError: pass
        for dd,mm,yyyy in GERMAN.findall(nearby):
            try: dates.append(dt.date(int(yyyy),int(mm),int(dd)))
            except ValueError: pass
        for day in dates:
            if dt.timedelta(0)<=today-day<=dt.timedelta(days=4):
                candidates.append((day,match.group(0).lower()))
    if not candidates:
        print("No clearly dated ARD Sounds episode; preserving last verified player")
        return
    date=max(day for day,urn in candidates)
    ids={urn for day,urn in candidates if day==date}
    if len(ids)!=1:
        print("Ambiguous latest ARD episode identifiers; retaining verified player",date,len(ids))
        return
    urn=ids.pop()
    prior=json.loads(OUT.read_text(encoding="utf-8"))
    if prior.get("date","")>date.isoformat():
        print("Old ARD episode candidate; retaining previous")
        return
    data={"date":date.isoformat(),"title":"tagesschau 20:00 Uhr, "+date.strftime("%d.%m.%Y"),"episode_urn":urn,"embed_url":"https://www.ardsounds.de/embed/episode/"+urn+"/","episode_url":"https://www.ardsounds.de/episode/"+urn+"/","source":"ARD Sounds official show"}
    if data["date"]==prior.get("date") and urn==prior.get("episode_urn"):
        print("Already up to date:",date)
        return
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Updated",date,urn)
if __name__=="__main__":main()
