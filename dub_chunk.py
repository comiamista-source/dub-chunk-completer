#!/usr/bin/env python3
"""
Chunk Completer - dubs ONE chunk file and writes the dubbed result.
Each failed chunk from the main pipeline (uploaded to Dubz/Chunks) is dubbed by
its own matrix job using this script.

Usage:
    python dub_chunk.py INPUT.mp4 --src Hindi --target English --tries 3 --out OUT.mp4
"""
import argparse, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "engine"))
try:
    from dub_engine import DubEngine
except Exception as e:
    print(f"ERROR: could not import dub_engine: {e}")
    sys.exit(2)

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def main():
    ap = argparse.ArgumentParser(description="Dub a single chunk file.")
    ap.add_argument("input")
    ap.add_argument("--src", default="Hindi")
    ap.add_argument("--target", default="English")
    ap.add_argument("--genre", default="monologue")
    ap.add_argument("--speakers", type=int, default=1)
    ap.add_argument("--tries", type=int, default=3)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    inp = Path(args.input.strip().strip('"'))
    if not inp.exists():
        print(f"ERROR: input not found: {inp}"); sys.exit(1)
    out = Path(args.out) if args.out else inp.with_name(f"{inp.stem} - {args.target} DUB{inp.suffix}")

    dub = DubEngine(poll_interval=3)
    last = None
    for attempt in range(1, args.tries + 1):
        try:
            log(f"Attempt {attempt}/{args.tries}: dubbing {inp.name}")
            job = dub.create_job(src_lang=args.src, target_langs=[args.target],
                                 job_name=inp.stem, num_speakers=args.speakers, genre=args.genre)
            jid = job["job_id"]
            dub.upload(job["upload_url"], str(inp))
            dub.start(jid)
            def cb(st):
                prog = getattr(st, "progress", 0) or 0
                step = getattr(st, "current_step_label", "") or ""
                log(f"  {step} {prog}%")
            st = dub.wait(jid, on_progress=cb, timeout=1800)
            url = getattr(st, "dubbed_video_url", None)
            if not url:
                raise RuntimeError("no dubbed_video_url returned")
            dub.download(url, str(out))
            log(f"DONE -> {out.name}")
            print(f"OUTPUT={out}")
            return 0
        except Exception as e:
            last = e
            log(f"  attempt {attempt} failed: {e}")
            time.sleep(5)
    log(f"FAILED after {args.tries} tries: {last}")
    sys.exit(1)

if __name__ == "__main__":
    sys.exit(main() or 0)