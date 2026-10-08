"""Generate a verified MP3 from the newsletter podcast script with Piper."""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
EDITION = ROOT / "data" / "edition.json"
VOICE = "de_DE-thorsten-medium"

def main():
    data = json.loads(EDITION.read_text(encoding="utf-8"))
    spoken = data.get("podcast_script", "").strip()
    data["audio"] = None
    if not spoken:
        EDITION.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    date = data.get("date", "")
    if len(spoken) < 100 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        sys.exit("Invalid podcast text or edition date")
    audio_dir = ROOT / "audio"
    audio_dir.mkdir(exist_ok=True)
    wav = audio_dir / f"{date}.wav"
    mp3 = audio_dir / f"{date}.mp3"
    text_file = audio_dir / "narration.txt"
    text_file.write_text(spoken, encoding="utf-8")
    subprocess.run([sys.executable, "-m", "piper.download_voices", VOICE], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "piper", "-m", VOICE, "-f", str(wav), "--input-file", str(text_file)], cwd=ROOT, check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-codec:a", "libmp3lame", "-qscale:a", "5", str(mp3)], check=True)
    wav.unlink(missing_ok=True)
    text_file.unlink(missing_ok=True)
    if not mp3.exists() or mp3.stat().st_size < 10000:
        sys.exit("No valid MP3 generated")
    data["audio"] = "./audio/" + mp3.name
    EDITION.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
