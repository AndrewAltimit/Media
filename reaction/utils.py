"""Helpers for maintaining the reaction image set.

Usage (run from anywhere):
    python utils.py convert <input> [<input> ...] [--out DIR] [--name ID] [--size 128]
    python utils.py check

convert
    Normalizes an image or clip into the formats this folder uses:
      * single-frame input (png/jpg/gif/webp/bmp) -> <id>.png
      * multi-frame input (animated gif/webp/png)  -> <id>.webp (animated, lossless-ish)
      * video input (mp4/webm/mov)                 -> <id>.webp via ffmpeg (needs ffmpeg on PATH)
    Frames are scaled so the longest side is at most --size (default 128, the
    size of most existing reactions); smaller images are left as-is.
    --name sets the output id (only valid with one input); otherwise the input
    filename is snake_cased.

check
    Verifies that every image in this folder has exactly one config.yaml entry,
    that every entry points at an existing file with the right extension, and
    that ids are unique and match filenames.

Requires Pillow (pip install pillow).
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageSequence

HERE = Path(__file__).resolve().parent
RAW_PREFIX = "https://raw.githubusercontent.com/AndrewAltimit/Media/refs/heads/main/reaction/"
IMAGE_EXTS = {".png", ".webp", ".gif"}
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".mkv"}


def snake_id(name: str) -> str:
    stem = re.sub(r"^\d+[_-]", "", Path(name).stem)  # drop emoji-site numeric prefixes
    stem = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", stem)
    return re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")


def _fit(im: Image.Image, size: int) -> Image.Image:
    if max(im.size) <= size:
        return im
    scale = size / max(im.size)
    return im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)


def _video_to_gif(src: Path, size: int, fps: int = 15) -> Path:
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is required to convert video files")
    tmp = Path(tempfile.mkdtemp()) / (src.stem + ".gif")
    vf = f"fps={fps},scale='if(gt(iw,ih),min({size},iw),-2)':'if(gt(iw,ih),-2,min({size},ih))':flags=lanczos"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-vf", vf, str(tmp)], check=True)
    return tmp


def convert(src: Path, out_dir: Path, name: str | None, size: int) -> Path:
    if src.suffix.lower() in VIDEO_EXTS:
        src = _video_to_gif(src, size)
    out_id = name or snake_id(src.name)
    with Image.open(src) as im:
        n_frames = getattr(im, "n_frames", 1)
        if n_frames <= 1:
            dest = out_dir / f"{out_id}.png"
            _fit(im.convert("RGBA"), size).save(dest, optimize=True)
        else:
            frames, durations = [], []
            for frame in ImageSequence.Iterator(im):
                frames.append(_fit(frame.convert("RGBA"), size))
                durations.append(frame.info.get("duration", im.info.get("duration", 80)) or 80)
            dest = out_dir / f"{out_id}.webp"
            frames[0].save(
                dest,
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=im.info.get("loop", 0),
                quality=90,
                method=6,
            )
    return dest


def check() -> int:
    text = (HERE / "config.yaml").read_text(encoding="utf-8")
    ids = re.findall(r'^\s*- id:\s*"([^"]+)"', text, re.M)
    urls = re.findall(r'^\s*source_url:\s*"([^"]+)"', text, re.M)
    problems = []
    if len(ids) != len(urls):
        problems.append(f"{len(ids)} ids but {len(urls)} source_urls")
    seen = {}
    for i, url in zip(ids, urls):
        if not url.startswith(RAW_PREFIX):
            problems.append(f"{i}: source_url does not use the raw GitHub prefix")
            continue
        fname = url[len(RAW_PREFIX):]
        if Path(fname).stem != i:
            problems.append(f"{i}: id does not match filename {fname}")
        if not (HERE / fname).is_file():
            problems.append(f"{i}: missing file {fname}")
        seen.setdefault(i, []).append(fname)
    for i, files in seen.items():
        if len(files) > 1:
            problems.append(f"duplicate id {i!r}: {', '.join(files)}")
    referenced = {u[len(RAW_PREFIX):] for u in urls if u.startswith(RAW_PREFIX)}
    for f in sorted(HERE.iterdir()):
        if f.suffix.lower() in IMAGE_EXTS and f.name not in referenced:
            problems.append(f"unregistered image {f.name}")
    for p in problems:
        print(p)
    print(f"{len(ids)} entries, {len(problems)} problem(s)")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert", help="convert images/clips to reaction png/webp")
    c.add_argument("inputs", nargs="+", type=Path)
    c.add_argument("--out", type=Path, default=HERE)
    c.add_argument("--name", help="output id (single input only)")
    c.add_argument("--size", type=int, default=128, help="max side in pixels (default 128)")
    sub.add_parser("check", help="verify images and config.yaml are in sync")
    args = ap.parse_args()

    if args.cmd == "check":
        return check()
    if args.name and len(args.inputs) > 1:
        ap.error("--name can only be used with a single input")
    args.out.mkdir(parents=True, exist_ok=True)
    for src in args.inputs:
        print(convert(src, args.out, args.name, args.size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
