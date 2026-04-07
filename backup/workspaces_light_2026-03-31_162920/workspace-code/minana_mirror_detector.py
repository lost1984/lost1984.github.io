#!/usr/bin/env python3
import argparse
import itertools
import math
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen
import re
from PIL import Image, ImageStat

UA = 'Mozilla/5.0'
DEFAULT_URL = 'https://www.douyu.com/22619'
DEFAULT_PLUGIN = '/root/.openclaw/workspace-code/.douyu-plugin'
DEFAULT_STREAMLINK = '/root/.local/bin/streamlink'


def fetch_stream_url(room_url: str, plugin_dir: str) -> str:
    cmd = [DEFAULT_STREAMLINK, '--plugin-dirs', plugin_dir, '--stream-url', room_url, 'best']
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip())
    return p.stdout.strip().splitlines()[-1].strip()


def capture_frame(stream_url: str, out: Path) -> None:
    cmd = ['ffmpeg', '-y', '-i', stream_url, '-frames:v', '1', '-q:v', '2', str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout)[-1000:])


def region_feature(img: Image.Image):
    small = img.resize((48, 48)).convert('L')
    stat = ImageStat.Stat(small)
    mean = stat.mean[0]
    var = stat.var[0]
    # downsample into vector
    px = list(small.getdata())
    return mean, var, px


def sim(a, b):
    ma, va, pa = a
    mb, vb, pb = b
    if abs(ma - mb) > 20:
        return 0.0
    if abs(va - vb) > 2000:
        return 0.0
    diff = sum(abs(x - y) for x, y in zip(pa, pb)) / len(pa)
    return max(0.0, 1.0 - diff / 80.0)


def detect_repeated_regions(img: Image.Image):
    w, h = img.size
    # focus center stage area, ignore top/bottom bars
    crop = img.crop((0, int(h * 0.08), w, int(h * 0.92)))
    cw, ch = crop.size
    candidates = []

    # person-like windows around portrait/body proportions
    for cols in (2, 3, 4):
        box_w = cw // cols
        box_h = int(box_w * 0.72)
        if box_h > ch:
            continue
        top = max(0, int(ch * 0.18))
        if top + box_h > ch:
            top = ch - box_h
        for i in range(cols):
            x1 = i * box_w
            x2 = x1 + box_w
            if x2 > cw:
                continue
            region = crop.crop((x1, top, x2, top + box_h))
            candidates.append(((x1, top, x2, top + box_h), region_feature(region)))

    # also check three overlapping central windows
    thirds = [
        (int(cw*0.05), int(ch*0.18), int(cw*0.35), int(ch*0.75)),
        (int(cw*0.33), int(ch*0.18), int(cw*0.67), int(ch*0.75)),
        (int(cw*0.65), int(ch*0.18), int(cw*0.95), int(ch*0.75)),
    ]
    for box in thirds:
        candidates.append((box, region_feature(crop.crop(box))))

    best_pair = None
    best_pair_score = 0.0
    for (box1, f1), (box2, f2) in itertools.combinations(candidates, 2):
        score = sim(f1, f2)
        if score > best_pair_score:
            best_pair_score = score
            best_pair = (box1, box2)

    best_triplet = None
    best_triplet_score = 0.0
    for a, b, c in itertools.combinations(candidates, 3):
        score = (sim(a[1], b[1]) + sim(a[1], c[1]) + sim(b[1], c[1])) / 3
        if score > best_triplet_score:
            best_triplet_score = score
            best_triplet = (a[0], b[0], c[0])

    return {
        'pair_score': round(best_pair_score, 4),
        'pair_boxes': best_pair,
        'triplet_score': round(best_triplet_score, 4),
        'triplet_boxes': best_triplet,
        'matched': best_triplet_score >= 0.72 or best_pair_score >= 0.78,
    }


def main():
    ap = argparse.ArgumentParser(description='Detect 2/3 similar subject regions in Minana live frame')
    ap.add_argument('--room-url', default=DEFAULT_URL)
    ap.add_argument('--plugin-dir', default=DEFAULT_PLUGIN)
    ap.add_argument('--save-frame', default='')
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as td:
        frame = Path(td) / 'frame.jpg'
        stream_url = fetch_stream_url(args.room_url, args.plugin_dir)
        capture_frame(stream_url, frame)
        if args.save_frame:
            Path(args.save_frame).write_bytes(frame.read_bytes())
        img = Image.open(frame)
        res = detect_repeated_regions(img)
        print(res)
        if res['matched']:
            sys.exit(0)
        sys.exit(3)


if __name__ == '__main__':
    main()
