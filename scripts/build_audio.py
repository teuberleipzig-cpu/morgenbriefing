"""Offline TTS: produce MP3 only for a verified, nonempty script."""
import json, pathlib, subprocess, sys, re
ROOT=pathlib.Path(__file__).resolve().parents[1]
EDITION=ROOT/"data"/"edition.json"
def main():
    data=json.loads(EDITION.read_text(encoding="utf-8"))
    script=data.get("podcast_script","").strip()
    data["audio"]=None
    if script:
        if len(script)<100 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",data.get("date","")): sys.exit("Invalid podcast data")
        out=ROOT/"audio"/(data["date"]+".mp3")
        out.parent.mkdir(exist_ok=True)
        wav=out.with_suffix(".wav")
        subprocess.run(["piper","--model","de_DE-thorsten-medium","--output_file",str(wav)],input=script,text=True,check=True)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(wav),"-codec:a","libmp3lame","-qscale:a","5",str(out)],check=True)
        wav.unlink(missing_ok=True)
        if out.stat().st_size<10000: sys.exit("Audio suspiciously small")
        data["audio"]="./audio/"+out.name
    EDITION.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__": main()
