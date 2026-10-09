"""Refresh official ARD metadata; preserve the player and fail visibly on errors."""
import datetime as dt
import json
import pathlib
import re
import sys
import urllib.request
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ard.json"
# Linked by the official tagesschau audio-podcast page; redirects to its URN.
SHOW = "https://www.ardsounds.de/sendung/tagesschau-audio-podcast/343278/"
SHOW_URN = "urn:ard:show:3b5a0f8757de647e"
EPISODE = re.compile(r"urn:ard:episode:[0-9a-f]{16}")
TITLE = re.compile(r"tagesschau 20:00 Uhr, (\d{2}\.\d{2}\.\d{4})")


class JsonScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("type") in (
            "application/json", "application/ld+json"
        ):
            self.current = [attrs.get("id"), ""]

    def handle_data(self, data):
        if self.current is not None:
            self.current[1] += data

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.scripts.append(self.current)
            self.current = None


def scripts(raw):
    parser = JsonScripts()
    parser.feed(raw)
    return parser.scripts


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Morgenbriefing/1.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        if urlparse(response.url).hostname != "www.ardsounds.de":
            raise ValueError("Unexpected ARD redirect")
        return response.read().decode("utf-8")


def select_episode(raw, today):
    payload = next(json.loads(value) for key, value in scripts(raw) if key == "__NEXT_DATA__")
    show = payload["props"]["pageProps"]["initialData"]["data"]["result"]
    if show["coreId"] != SHOW_URN:
        raise ValueError("Unexpected podcast series")
    candidates = set()
    for item in show["items"]["nodes"]:
        title = TITLE.fullmatch(item.get("title", ""))
        urn = item.get("assetId", "")
        if not title or not EPISODE.fullmatch(urn) or not item.get("isPublished"):
            continue
        day = dt.datetime.strptime(title[1], "%d.%m.%Y").date()
        published = dt.datetime.fromisoformat(item["publishDate"])
        if (published.date() != day or item["programSet"]["coreId"] != SHOW_URN
                or unquote(item["path"]) != f"/episode/{urn}/"):
            raise ValueError("Conflicting episode metadata")
        if dt.timedelta(0) <= today - day <= dt.timedelta(days=1):
            candidates.add((day, urn))
    if not candidates:
        raise ValueError("No current, clearly dated 20:00 episode")
    latest = max(day for day, _ in candidates)
    ids = {urn for day, urn in candidates if day == latest}
    if len(ids) != 1:
        raise ValueError("Ambiguous latest episode")
    return latest, ids.pop()


def verify_episode(raw, day, urn):
    episodes = [json.loads(value) for _, value in scripts(raw)]
    episodes = [item for item in episodes if isinstance(item, dict)
                and item.get("@type") == "PodcastEpisode"]
    expected_url = f"https://www.ardsounds.de/episode/{urn}/"
    expected_title = "tagesschau 20:00 Uhr, " + day.strftime("%d.%m.%Y")
    if len(episodes) != 1:
        raise ValueError("Missing or ambiguous episode details")
    episode = episodes[0]
    if (unquote(episode["url"]) != expected_url or episode["name"] != expected_title
            or dt.datetime.fromisoformat(episode["datePublished"]).date() != day
            or unquote(episode["partOfSeries"]["url"]).rstrip("/").split("/")[-1] != SHOW_URN):
        raise ValueError("Episode detail page does not confirm date, title and URN")


def main():
    today = dt.datetime.now(dt.timezone.utc).date()
    day, urn = select_episode(fetch(SHOW), today)
    verify_episode(fetch(f"https://www.ardsounds.de/episode/{urn}/"), day, urn)
    prior = json.loads(OUT.read_text(encoding="utf-8"))
    if prior.get("date", "") > day.isoformat():
        raise ValueError("Refusing to replace a newer verified episode")
    if prior.get("date") == day.isoformat() and prior.get("episode_urn") == urn:
        print("Already up to date:", day, urn)
        return
    data = {
        "date": day.isoformat(),
        "title": "tagesschau 20:00 Uhr, " + day.strftime("%d.%m.%Y"),
        "episode_urn": urn,
        "embed_url": f"https://www.ardsounds.de/embed/episode/{urn}/",
        "episode_url": f"https://www.ardsounds.de/episode/{urn}/",
        "source": "ARD Sounds official episode metadata",
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated", day, urn)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("::error::ARD refresh failed; retaining last verified player:", error)
        sys.exit(1)
