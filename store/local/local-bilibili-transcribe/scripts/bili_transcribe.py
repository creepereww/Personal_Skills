#!/usr/bin/env python
"""B站视频无登录转文字工具。

子命令:
  info      取标题/UP/时长/官方章节/字幕可用性/章节封面图
  audio     下载 360P 视频流并抽取 16k 单声道音轨
  model     从 hf-mirror 下载 faster-whisper 模型文件
  transcribe 用 faster-whisper 转写音轨（优先 GPU）
  all       audio + model + transcribe 一条龙

依赖: pip install faster-whisper imageio-ffmpeg nvidia-cublas-cu12 nvidia-cudnn-cu12
用法: python bili_transcribe.py all --url "https://www.bilibili.com/video/BV1xx411c7XX/"
"""

import argparse
import glob
import json
import os
import re
import site
import subprocess
import sys
import time
import urllib.request

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}

MODEL_FILES = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")
DEFAULT_PROMPT = ""  # 中文技术视频可传入术语表，显著提升专有名词准确率


def bvid_of(text):
    m = re.search(r"(BV[0-9A-Za-z]{10})", text or "")
    if not m:
        raise SystemExit(f"无法从 {text!r} 解析出 BV 号")
    return m.group(1)


def api(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if data.get("code") != 0:
        raise SystemExit(f"接口返回 code={data.get('code')}: {data.get('message')}")
    return data["data"]


def hhmmss(sec):
    return f"{int(sec) // 60:02d}:{int(sec) % 60:02d}"


def pick_cid(data, page):
    pages = data.get("pages") or []
    if not pages:
        raise SystemExit("视频无分P信息")
    if page < 1 or page > len(pages):
        raise SystemExit(f"分P {page} 不存在（共 {len(pages)} P）")
    return pages[page - 1]["cid"], pages[page - 1]["duration"]


def cmd_info(args):
    bvid = bvid_of(args.url)
    view = api(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
    cid, duration = pick_cid(view, args.page)
    player = api(f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}")

    print(f"标题: {view['title']}")
    print(f"UP:   {view['owner']['name']}")
    print(f"时长: {hhmmss(duration)} ({duration}s)")
    print(f"BV:   {bvid}  cid: {cid}")
    if view.get("desc"):
        print(f"简介: {view['desc'][:200]}")

    subs = (player.get("subtitle") or {}).get("subtitles") or []
    if subs:
        print("字幕: 有公开字幕")
        for s in subs:
            print(f"  - {s.get('lan_doc')}: {s.get('subtitle_url')}")
    else:
        print(
            "字幕: 无（need_login_subtitle=%s）→ 走本地转写"
            % player.get("need_login_subtitle")
        )

    points = player.get("view_points") or []
    if points:
        print(f"官方章节 {len(points)} 段（章节封面图含关键画面，可先读图拿目录）:")
        for p in points:
            print(f"  {hhmmss(p['from'])}  {p['content'].strip()}")
            if p.get("imgUrl"):
                print(f"          图: {p['imgUrl']}")
    return bvid, cid, duration


def fetch_playurl(bvid, cid, qn=32):
    url = (
        "https://api.bilibili.com/x/player/playurl"
        f"?bvid={bvid}&cid={cid}&qn={qn}&type=mp4&platform=html5"
    )
    data = api(url)
    durl = data.get("durl") or []
    if not durl:
        raise SystemExit("无 durl（可能需要登录或该视频不可匿名播放）")
    return durl[0]["url"], data.get("quality")


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    return os.path.getsize(dest)


def cmd_audio(args):
    bvid = bvid_of(args.url)
    view = api(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
    cid, _ = pick_cid(view, args.page)
    url, quality = fetch_playurl(bvid, cid, args.qn)
    os.makedirs(args.workdir, exist_ok=True)

    mp4 = os.path.join(args.workdir, f"{bvid}.mp4")
    wav = os.path.join(args.workdir, f"{bvid}.wav")
    size = download(url, mp4)
    print(f"视频已下载 qn={quality}: {mp4} ({size / 1e6:.1f} MB)")

    import imageio_ffmpeg

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ff, "-y", "-i", mp4, "-vn", "-ac", "1", "-ar", "16000", wav, "-loglevel", "error"],
        check=True,
    )
    print(f"音轨已抽取: {wav} ({os.path.getsize(wav) / 1e6:.1f} MB)")
    return wav


def cmd_model(args):
    repo = f"Systran/faster-whisper-{args.model_size}"
    dest = args.model_dir or os.path.join(
        os.environ.get("TEMP", "."), f"whisper_{args.model_size}"
    )
    os.makedirs(dest, exist_ok=True)
    for name in MODEL_FILES:
        path = os.path.join(dest, name)
        if os.path.exists(path) and os.path.getsize(path) > 1024:
            print(f"已存在, 跳过: {path}")
            continue
        url = f"https://hf-mirror.com/{repo}/resolve/main/{name}"
        print(f"下载 {name} ...", flush=True)
        try:
            # hf-mirror 对 Xet 仓库会 302 到签名直链，urllib 自动跟随
            download(url, path)
        except Exception as e:
            raise SystemExit(
                f"{name} 下载失败: {e}\n"
                "可改用 curl -L 重试；hub 客户端会报 401, 必须走 resolve 直链"
            )
        print(f"  -> {path} ({os.path.getsize(path) / 1e6:.1f} MB)")
    return dest


def preload_cuda_dlls():
    """ctranslate2 只会按裸文件名加载 cublas/cudnn，必须预先映射进进程。"""
    bins = []
    for sp in site.getsitepackages():
        bins += glob.glob(os.path.join(sp, "nvidia", "*", "bin"))
    if not bins:
        return
    os.environ["PATH"] = ";".join(bins) + ";" + os.environ["PATH"]
    for b in bins:
        try:
            os.add_dll_directory(b)
        except OSError:
            pass
    import ctypes

    for f in [x for b in bins for x in glob.glob(os.path.join(b, "*.dll"))]:
        try:
            ctypes.WinDLL(f)
        except OSError:
            pass


def cmd_transcribe(args):
    preload_cuda_dlls()
    from faster_whisper import WhisperModel

    model_dir = args.model_dir or os.path.join(
        os.environ.get("TEMP", "."), f"whisper_{args.model_size}"
    )
    model = None
    for device, compute in (("cuda", "float16"), ("cpu", "int8")):
        try:
            t0 = time.time()
            model = WhisperModel(
                model_dir, device=device, compute_type=compute,
                cpu_threads=8, local_files_only=True,
            )
            print(f"模型加载成功: {device}/{compute} ({time.time() - t0:.0f}s)", flush=True)
            break
        except Exception as e:
            print(f"{device} 不可用: {e}", flush=True)
    if model is None:
        raise SystemExit("GPU 与 CPU 均加载失败，检查模型目录是否缺文件")

    t0 = time.time()
    segments, info = model.transcribe(
        args.wav,
        language=args.language or None,
        initial_prompt=args.prompt or None,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        condition_on_previous_text=False,
        beam_size=5,
    )
    out = getattr(args, "out", None) or os.path.splitext(args.wav)[0] + ".txt"
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(f"[{hhmmss(seg.start)}] {seg.text.strip()}\n")
            n += 1
            if n % 100 == 0:
                print(f"  {n} 段 / {seg.end:.0f}s 音频 / {time.time() - t0:.0f}s", flush=True)
    print(f"完成: {n} 段 -> {out} (耗时 {time.time() - t0:.0f}s, 语言={info.language})")
    return out


def cmd_all(args):
    wav = cmd_audio(args)
    if not args.skip_model:
        cmd_model(args)
    args.wav = wav
    return cmd_transcribe(args)


def main():
    p = argparse.ArgumentParser(description="B站视频无登录转文字")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, need_url=False):
        sp.add_argument("--url", required=need_url, help="视频 URL 或 BV 号")
        sp.add_argument("--page", type=int, default=1, help="分P 序号, 默认 1")
        sp.add_argument("--workdir", default=".", help="输出目录")
        sp.add_argument("--model-dir", default=None, help="本地模型目录")
        sp.add_argument("--model-size", default="medium", help="small/medium/large-v3")
        sp.add_argument("--language", default="zh", help="语言, 默认 zh")
        sp.add_argument("--prompt", default=DEFAULT_PROMPT, help="术语表 initial_prompt")
        sp.add_argument("--qn", type=int, default=32, help="清晰度, 默认 32(360P)")
        sp.add_argument("--skip-model", action="store_true", help="跳过模型下载")

    for name, fn in (
        ("info", cmd_info), ("audio", cmd_audio),
        ("model", cmd_model), ("transcribe", cmd_transcribe), ("all", cmd_all),
    ):
        sp = sub.add_parser(name)
        common(sp, need_url=name in ("info", "audio", "all"))
        if name == "transcribe":
            sp.add_argument("--wav", required=True)
            sp.add_argument("--out", default=None)
        sp.set_defaults(func=fn)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
