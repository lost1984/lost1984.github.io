#!/usr/bin/env python3
import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
DEFAULT_ROOM_URL = "https://www.douyu.com/22619"
DEFAULT_ROOM_ID = "5551871"
DEFAULT_OUTDIR = Path.home() / "videos" / "douyu"
DEFAULT_FONT = "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"
DEFAULT_STREAMLINK = "/root/.local/bin/streamlink"


def log(msg: str) -> None:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")


def fetch_text(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def sanitize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[\\/:*?\"<>|\r\n\t]+", "_", name)
    name = re.sub(r"\s+", " ", name)
    return name[:80] if name else "douyu_room"


def resolve_room_info(room_url: str) -> tuple[str, str, str]:
    html = fetch_text(room_url)

    room_id = ""
    for pat in [
        r'roomInfo.{0,80}room_id\\":(\d+)',
        r'room_id\\":(\d+)',
        r'"room_id":(\d+)',
    ]:
        m = re.search(pat, html)
        if m:
            room_id = m.group(1)
            break
    if not room_id:
        raise RuntimeError("无法从页面解析 room_id")

    anchor_name = ""
    for pat in [
        r'"owner_name":"([^\"]+)"',
        r'owner_name\\":\\"([^\"]+)\\"',
        r'"nickname":"([^\"]+)"',
        r'nickname\\":\\"([^\"]+)\\"',
    ]:
        m = re.search(pat, html)
        if m:
            anchor_name = m.group(1)
            break

    room_name = ""
    for pat in [
        r'"room_name":"([^\"]+)"',
        r'room_name\\":\\"([^\"]+)\\"',
    ]:
        m = re.search(pat, html)
        if m:
            room_name = m.group(1)
            break

    return room_id, sanitize_name(anchor_name or room_id), sanitize_name(room_name or room_id)


def ensure_cmd(name: str) -> str:
    path = shutil.which(name)
    if not path and name == "streamlink" and Path(DEFAULT_STREAMLINK).exists():
        path = DEFAULT_STREAMLINK
    if not path:
        raise RuntimeError(f"缺少依赖命令: {name}")
    return path


def streamlink_probe(room_url: str, plugin_dir: str | None = None) -> str:
    streamlink = ensure_cmd("streamlink")
    cmd = [streamlink, "--stream-url", room_url, "best"]
    if plugin_dir:
        cmd[1:1] = ["--plugin-dirs", plugin_dir]
    log("探测直播流: " + " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"streamlink 探测失败: {msg}")
    stream_url = proc.stdout.strip().splitlines()[-1].strip()
    if not stream_url:
        raise RuntimeError("streamlink 未返回有效流地址")
    return stream_url


def record_source_mkv(stream_url: str, outfile: Path, max_minutes: int) -> Path:
    ffmpeg = ensure_cmd("ffmpeg")
    outfile.parent.mkdir(parents=True, exist_ok=True)
    duration = max_minutes * 60
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        stream_url,
        "-t",
        str(duration),
        "-c",
        "copy",
        str(outfile),
    ]
    log("开始原始录制: " + " ".join(cmd))
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 原始录制失败，退出码 {proc.returncode}")
    return outfile


def choose_font(font_path: str | None = None) -> str:
    if font_path and Path(font_path).exists():
        return font_path
    if Path(DEFAULT_FONT).exists():
        return DEFAULT_FONT
    fc_match = shutil.which("fc-match")
    if fc_match:
        proc = subprocess.run([fc_match, "-f", "%{file}\n", "Liberation Mono"], capture_output=True, text=True)
        path = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
        if path and Path(path).exists():
            return path
    raise RuntimeError("找不到可用字体文件，无法绘制时间戳")


def probe_duration_seconds(src: Path) -> float:
    ffprobe = ensure_cmd("ffprobe")
    proc = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(src),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return 0.0
    try:
        return float(proc.stdout.strip())
    except Exception:
        return 0.0


def transcode_h264_with_timestamp(src: Path, out_mp4: Path, start_dt: dt.datetime, font_path: str | None = None) -> Path:
    ffmpeg = ensure_cmd("ffmpeg")
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    font = choose_font(font_path)

    # 用文本文件 + reload 方案稳定生成“年-月-日 HH:MM:SS”完整时间戳，
    # 避开 drawtext/localtime 在复杂转义下的兼容性问题。
    ts_file = out_mp4.with_suffix(".timestamp.txt")
    current = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    ts_file.write_text(current, encoding="utf-8")

    vf = (
        f"drawtext=fontfile={font}:"
        f"textfile={ts_file}:reload=1:"
        f"x=w-tw-20:y=h-th-20:"
        f"fontsize=28:fontcolor=white:borderw=2:bordercolor=black:"
        f"box=1:boxcolor=black@0.35"
    )

    updater = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import time,sys,datetime as dt,pathlib;"
                "p=pathlib.Path(sys.argv[1]);"
                "t=dt.datetime.fromisoformat(sys.argv[2]);"
                "end=time.time()+float(sys.argv[3])+30;"
                "\nwhile time.time()<end:\n"
                " p.write_text(t.strftime('%Y-%m-%d %H:%M:%S'), encoding='utf-8');"
                " time.sleep(1);"
                " t += dt.timedelta(seconds=1)"
            ),
            str(ts_file),
            start_dt.isoformat(sep=" "),
            str(max(60, int(probe_duration_seconds(src)))),
        ]
    )

    try:
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(src),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(out_mp4),
        ]
        log("开始转码(H.264+完整日期时间戳): " + " ".join(cmd))
        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg 转码失败，退出码 {proc.returncode}")
        return out_mp4
    finally:
        updater.terminate()
        try:
            updater.wait(timeout=3)
        except Exception:
            pass
        if ts_file.exists():
            ts_file.unlink()


def build_paths(outdir: Path, anchor_name: str, start_dt: dt.datetime) -> tuple[Path, Path]:
    date_s = start_dt.strftime("%F")
    time_s = start_dt.strftime("%H%M%S")
    base = f"{anchor_name}_{date_s}_{time_s}"
    mkv = outdir / f"{base}_source.mkv"
    mp4 = outdir / f"{base}_h264_ts.mp4"
    return mkv, mp4


def main() -> int:
    ap = argparse.ArgumentParser(description="Douyu 录播：先录 MKV，再转 H.264 并叠加右下角真实时间戳")
    ap.add_argument("--room-url", default=DEFAULT_ROOM_URL, help="斗鱼房间链接")
    ap.add_argument("--room-id", default=DEFAULT_ROOM_ID, help="预留参数，兼容旧调用")
    ap.add_argument("--room-alias", default="", help="手动指定文件名前缀；为空则自动用房间名")
    ap.add_argument("--outdir", default=str(DEFAULT_OUTDIR), help="录播输出目录")
    ap.add_argument("--max-minutes", type=int, default=120, help="单次最多录多少分钟")
    ap.add_argument("--resolve-room-id", action="store_true", help="仅做页面校验")
    ap.add_argument("--plugin-dir", default="", help="streamlink douyu 插件目录")
    ap.add_argument("--font", default="", help="drawtext 字体文件路径")
    ap.add_argument("--keep-source", action="store_true", help="转码后保留原始 MKV")
    args = ap.parse_args()

    outdir = Path(args.outdir).expanduser().resolve()
    start_dt = dt.datetime.now()

    try:
        room_id, anchor_name, room_name = resolve_room_info(args.room_url)
        if args.resolve_room_id:
            log(f"解析到 room_id={room_id}, anchor_name={anchor_name}, room_name={room_name}")

        if args.room_alias.strip():
            anchor_name = sanitize_name(args.room_alias)

        stream_url = streamlink_probe(args.room_url, args.plugin_dir or None)
        src_mkv, out_mp4 = build_paths(outdir, anchor_name, start_dt)

        record_source_mkv(stream_url, src_mkv, args.max_minutes)
        log(f"原始录制完成: {src_mkv}")

        transcode_h264_with_timestamp(src_mkv, out_mp4, start_dt, args.font or None)
        log(f"转码完成: {out_mp4}")

        if not args.keep_source and src_mkv.exists():
            src_mkv.unlink()
            log(f"已删除原始 MKV: {src_mkv}")

        return 0

    except Exception as e:
        log(f"执行失败: {e}")
        return 12


if __name__ == "__main__":
    sys.exit(main())
