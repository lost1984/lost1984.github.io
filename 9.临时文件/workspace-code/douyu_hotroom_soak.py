#!/usr/bin/env python3
import datetime as dt
import json
import os
import signal
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from urllib.request import Request, urlopen

WORKDIR = Path('/root/.openclaw/workspace-code')
OUTDIR = WORKDIR / 'test_recordings' / 'hotroom_soak'
LOG = OUTDIR / 'soak.log'
SUMMARY = OUTDIR / 'summary.jsonl'
ROOMS_JSON = OUTDIR / 'rooms.json'
DOUYU = WORKDIR / 'douyu_recorder.py'
PLUGIN = WORKDIR / '.douyu-plugin'
DEADLINE_HOUR = 21
DEADLINE_MIN = 30
QUERIES = ['王者荣耀', 'LOL', 'DOTA2', 'CF', 'DNF', '颜值']
ROOM_SECONDS = 180


def now():
    return dt.datetime.now()


def log(msg):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    line = f"[{now().strftime('%F %T')}] {msg}"
    print(line, flush=True)
    with LOG.open('a', encoding='utf-8') as f:
        f.write(line + '\n')


def fetch_hot_rooms():
    seen = {}
    for q in QUERIES:
        url = 'https://www.douyu.com/japi/search/api/searchShow?kw=' + urllib.parse.quote(q) + '&page=1&pageSize=5'
        txt = urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.douyu.com/'}), timeout=20).read().decode('utf-8', 'ignore')
        data = json.loads(txt).get('data', {}).get('relateShow', [])
        for item in data:
            if item.get('isLive') != 1:
                continue
            rid = str(item.get('rid'))
            hot = item.get('hot') or ''
            if rid not in seen:
                seen[rid] = {
                    'rid': rid,
                    'roomName': item.get('roomName') or '',
                    'nickName': item.get('nickName') or '',
                    'cateName': item.get('cateName') or '',
                    'hot': hot,
                    'url': f'https://www.douyu.com/{rid}',
                }
    rooms = list(seen.values())
    def hot_num(x):
        s = x['hot'].replace('万', '')
        try:
            n = float(s)
            if '万' in x['hot']:
                n *= 10000
            return n
        except Exception:
            return 0
    rooms.sort(key=hot_num, reverse=True)
    ROOMS_JSON.write_text(json.dumps(rooms, ensure_ascii=False, indent=2), encoding='utf-8')
    return rooms


def run_room(room):
    stamp = now().strftime('%Y%m%d_%H%M%S')
    room_dir = OUTDIR / f"{stamp}_{room['rid']}"
    room_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(DOUYU),
        '--room-url', room['url'],
        '--plugin-dir', str(PLUGIN),
        '--outdir', str(room_dir),
        '--keep-source',
        '--room-alias', f"{room['cateName']}_{room['nickName']}_{room['rid']}",
        '--max-minutes', '3',
    ]
    log(f"START rid={room['rid']} hot={room['hot']} room={room['roomName']} cmd={' '.join(cmd)}")
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = round(time.time() - t0, 1)
    rec = {
        'time': now().isoformat(sep=' ', timespec='seconds'),
        'rid': room['rid'],
        'url': room['url'],
        'hot': room['hot'],
        'cateName': room['cateName'],
        'nickName': room['nickName'],
        'roomName': room['roomName'],
        'elapsed': elapsed,
        'returncode': p.returncode,
        'stdout_tail': '\n'.join((p.stdout or '').splitlines()[-20:]),
        'stderr_tail': '\n'.join((p.stderr or '').splitlines()[-20:]),
        'room_dir': str(room_dir),
    }
    with SUMMARY.open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    if p.returncode == 0:
        log(f"OK rid={room['rid']} elapsed={elapsed}s dir={room_dir}")
    else:
        log(f"FAIL rid={room['rid']} elapsed={elapsed}s rc={p.returncode}")
        if rec['stdout_tail']:
            log('STDOUT tail:\n' + rec['stdout_tail'])
        if rec['stderr_tail']:
            log('STDERR tail:\n' + rec['stderr_tail'])
    return rec


def deadline_reached():
    n = now()
    d = n.replace(hour=DEADLINE_HOUR, minute=DEADLINE_MIN, second=0, microsecond=0)
    return n >= d


def main():
    log('SOAK START')
    rooms = fetch_hot_rooms()
    log(f'Fetched {len(rooms)} candidate rooms')
    # 先测前 6 个高热房；若时间允许继续下一轮
    while not deadline_reached():
        any_run = False
        for room in rooms[:6]:
            if deadline_reached():
                break
            run_room(room)
            any_run = True
        if not any_run:
            break
        if deadline_reached():
            break
    log('SOAK END')


if __name__ == '__main__':
    main()
