"""Keep official ARD Sounds embedded player in sync with the newest 20:00 podcast.

Never scrape/re-host audio. Match official ARD podcast's date against an ARD Sounds
episode URL; preserve the previous confirmed player if either source changes format.
"""
import datetime as dt
import html
import json
import pathlib
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ard.json"
RSS = "https://www.tagesschau.de/tagesschau_20_uhr/podcast-ts2000-audio-100~podcast.xml"
SHOW = "https://www.ardsounds.de/sendung/tagesschau-die-20-uhr-nachrichten-audio/urn%3Aard%3Ashow%3A771504b9e731d619/"
URN_RE = re.compile(r"urn:ard:episode:[0-9a-f]{16}", re.I)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "MorgenbriefingBot/1.0 (personal podcast viewer)", "Accept": "text/html,application/xml,text/xml"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read().decode("utf-8")

def main():
    rss = ET.fromstring(fetch(RSS))
    entries = []
    for item in rss.findall("./channel/item"):
        title = item.findtext("title", "").strip()
        published = item.findtext("pubDate", "").strip()
        if not published: continue
        timestamp = parsedate_to_datetime(published)
        # Official feed includes the 20:00 main bulletin, not the 100-second recap.
        entries.append((timestamp, title, item.findtext("link", "")))
    if not entries: raise ValueError("No published episodes in official RSS feed")
    published, title, link = max(entries, key=lambda e:e[0])
    date = published.date()
    today = dt.datetime.now(dt.timezone.utc).date()
    if date > today or (today-date).days > 4: raise ValueError("RSS latest date unexpectedly stale or in future")
    page = html.unescape(fetch(SHOW)).replace("\\u003A", ":").replace("\\u002F", "/")
    # Most recently published episode from the official show page. The page lists
    # newest-first, but we also validate that the RSS day is visible near that ID.
    matches = list(URN_RE.finditer(page))
    if not matches: raise ValueError("No official ARD Sounds episode IDs found")
    selected = None
    iso = date.strftime("%Y-%m-%d")
    german = date.strftime("%d.%m.%Y")
    for match in matches:
        context = page[max(0, match.start()-1500):match.end()+1500]
        if iso in context or german in context:
            selected = match.group()
            break
    if not selected:
        raise ValueError("Could not match RSS date to official ARD Sounds episode")
    previous = {}
    if OUT.exists(): previous = json.loads(OUT.read_text(encoding="utf-8"))
    if previous.get("date", "") > iso:
        raise ValueError("Refusing to roll back to older episode")
    edition = {"date":iso,"title":title,"episode_urn":selected,"embed_url":"https://www.ardsounds.de/embed/episode/"+selected+"/","episode_url":"https://www.ardsounds.de/episode/"+selected+"/","source":"ARD tagesschau RSS + ARD Sounds"}
    OUT.write_text(json.dumps(edition,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Confirmed",iso,selected)
if __name__=="__main__": main()
