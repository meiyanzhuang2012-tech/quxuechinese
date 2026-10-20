#!/usr/bin/env python3
"""一键出片：episodes/*.md -> renders/成片/*.mp4 + subtitles/*.srt

用法:
    python3 scripts/render.py scripts/episodes/A-001-火.md
    python3 scripts/render.py scripts/episodes/A-001-火.md --tts none     # 出无声样片（自测用，不烧 TTS）
    python3 scripts/render.py scripts/episodes/A-001-火.md --tts qwen     # 本机 Qwen3-TTS 英语配音
    python3 scripts/render.py scripts/episodes/A-001-火.md --tts edge     # edge-tts 备用

依赖（本机已装，无需额外安装）:
    ffmpeg 6.x (libx264/aac/libass), pillow, 本机 Qwen3-TTS 服务 :8891, edge-tts

设计原则:
    1. 脚本即源文件：所有时间轴/旁白/字幕都写在 md 里，代码只做渲染，不改内容。
    2. 幂等：同一 ep 重复跑覆盖同名产物，不产生中间垃圾（中间文件落在 .cache/，可随时删）。
    3. 没有 TTS 也能出片：--tts none 用字数估算时长，用于验版式和钩子。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_LATIN = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
W, H, FPS = 1080, 1920, 30
PAPER = (243, 236, 223)
INK = (38, 34, 32)
VERMILION = (178, 34, 34)


# ---------------------------------------------------------------- 解析
def parse_episode(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        sys.exit(f"[render] {md_path} 缺少 YAML front matter（--- 包起来的头部）")
    head, body = m.group(1), m.group(2)
    meta = {}
    for line in head.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip('"').strip("'")
    rows = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        if re.fullmatch(r"[-: ]+", cells[0]):
            continue
        if cells[0].lower() in ("time", "时间"):
            continue
        rows.append({"time": cells[0], "vo": cells[1],
                     "onscreen": cells[2].replace("<br>", "\n").replace("<br/>", "\n"),
                     "visual": cells[3]})
    if not rows:
        sys.exit(f"[render] {md_path} 没解析到分镜表（需要 | time | vo_en | onscreen_zh | visual |）")
    return {"meta": meta, "rows": rows, "path": md_path}


def to_seconds(ts: str) -> float:
    ts = ts.strip()
    if ":" in ts:
        parts = [float(p) for p in ts.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0.0)
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return float(ts)


def fmt_ts(sec: float) -> str:
    sec = max(0.0, sec)
    h, rem = divmod(int(sec), 3600)
    mnt, s = divmod(rem, 60)
    ms = int(round((sec - int(sec)) * 1000))
    return f"{h:02d}:{mnt:02d}:{s:02d},{ms:03d}"


# ---------------------------------------------------------------- 配音
def synth(text: str, out_mp3: Path, mode: str) -> float | None:
    """返回音频时长（秒）；mode=none 返回 None 由调用方估算。"""
    if mode == "none" or not text.strip():
        return None
    if mode == "qwen":
        bridge = Path("/root/qwen3-tts/say.sh")
        if not bridge.exists():
            sys.exit("[render] 找不到 /root/qwen3-tts/say.sh")
        txt = out_mp3.with_suffix(".txt")
        txt.write_text(text, encoding="utf-8")
        env = dict(os.environ, QWEN3_TTS_SPEAKER=os.environ.get("QWEN3_TTS_SPEAKER", "Serena"))
        r = subprocess.run(["bash", str(bridge), str(txt), str(out_mp3)], env=env,
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"[render] Qwen3-TTS 失败: {r.stderr[:300]}")
    elif mode == "edge":
        r = subprocess.run(["edge-tts", "--voice", "en-US-AriaNeural", "--text", text,
                            "--write-media", str(out_mp3)], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"[render] edge-tts 失败: {r.stderr[:300]}")
    else:
        sys.exit(f"[render] 未知 --tts {mode}")
    return probe_duration(out_mp3)


def probe_duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        sys.exit(f"[render] ffprobe 读不出时长: {path}")


def estimate_duration(text: str) -> float:
    words = len(re.findall(r"[A-Za-z']+", text)) or 1
    return max(2.5, words / 2.6 + 0.25)


# ---------------------------------------------------------------- 画面
def paper_bg(w: int = W, h: int = H):
    from PIL import Image, ImageDraw, ImageFilter
    import random

    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    rnd = random.Random(20261020)
    for _ in range(2600):
        x, y = rnd.randrange(w), rnd.randrange(h)
        c = rnd.choice([(232, 222, 205), (249, 244, 233), (226, 214, 196)])
        d.point((x, y), fill=c)
    for _ in range(28):  # 纤维
        x, y = rnd.randrange(w), rnd.randrange(h)
        d.line([(x, y), (x + rnd.randrange(-26, 26), y + rnd.randrange(-8, 8))],
               fill=(228, 217, 199), width=1)
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    vig = Image.new("L", (w, h), 0)  # 四角压暗
    vd = ImageDraw.Draw(vig)
    vd.rectangle([0, 0, w, h], fill=255)
    vd.ellipse([-w * 0.25, -h * 0.15, w * 1.25, h * 1.15], fill=0)
    vig = vig.filter(ImageFilter.GaussianBlur(160))
    dark = Image.new("RGB", (w, h), (206, 193, 172))
    return Image.composite(img, dark, vig.point(lambda v: 255 - v))


def wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def make_slide(row: dict, meta: dict, idx: int, total: int, out_png: Path):
    from PIL import Image, ImageDraw, ImageFont

    img = paper_bg()
    d = ImageDraw.Draw(img)

    onscreen = row["onscreen"].strip()
    # 大字只取行首连续汉字（"火 huǒ · fire" -> "火"），英文/拼音留给下方说明行
    m = re.match(r"^([\u4e00-\u9fff]{1,6})", onscreen)
    head = m.group(1) if m else ""
    size = 430 if len(head) <= 1 else (330 if len(head) == 2 else 200)
    big_font = ImageFont.truetype(FONT_BOLD, size, index=0)
    cap_font = ImageFont.truetype(FONT_REG, 52, index=0)
    tag_font = ImageFont.truetype(FONT_REG, 34, index=0)

    if head:
        bbox = d.textbbox((0, 0), head, font=big_font)
        gh = bbox[3] - bbox[1]
        cy = 520
        d.text(((W - (bbox[2] - bbox[0])) / 2 - bbox[0], cy - gh / 2 - bbox[1]),
               head, font=big_font, fill=INK)
        # 朱红竖线（视觉签名）
        d.rectangle([W / 2 - 3, cy + gh / 2 + 55, W / 2 + 3, cy + gh / 2 + 185], fill=VERMILION)

    # 屏幕文字（含拼音/释义）
    y = 1130
    for line in onscreen.split("\n")[:3]:
        for seg in wrap(d, line, cap_font, W - 200):
            tw = d.textlength(seg, font=cap_font)
            d.text(((W - tw) / 2, y), seg, font=cap_font, fill=INK)
            y += 74

    # 角标：ep 编号 + 分镜序号
    tag = f"{meta.get('ep', '')}  {idx + 1}/{total}"
    d.text((60, H - 130), tag, font=tag_font, fill=(150, 138, 120))
    d.text((W - 60 - d.textlength("@HanziBites", font=tag_font), H - 130),
           "@HanziBites", font=tag_font, fill=(150, 138, 120))
    img.save(out_png, "PNG")


# ---------------------------------------------------------------- 合成
def build_segment(png: Path, audio: Path | None, dur: float, out_mp4: Path):
    cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(png)]
    if audio and audio.exists():
        cmd += ["-i", str(audio)]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    cmd += ["-t", f"{dur:.3f}", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            "-af", "apad", "-shortest", str(out_mp4)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"[render] ffmpeg 分段失败: {r.stderr[-500:]}")


def render(md_path: Path, tts: str, burn: bool = False) -> dict:
    ep = parse_episode(md_path)
    meta, rows = ep["meta"], ep["rows"]
    slug = meta.get("slug") or re.sub(r"[^\w-]", "-", meta.get("title_en", "ep"))[:40]
    tag = f"{meta.get('ep', 'EP')}-{slug}"
    CACHE.mkdir(exist_ok=True)
    seg_dir = CACHE / tag
    if seg_dir.exists():
        shutil.rmtree(seg_dir)
    seg_dir.mkdir(parents=True)

    # 1) 行级音频 + 时长
    words_dir = seg_dir / "vo"
    words_dir.mkdir()
    timed, t = [], 0.0
    slot_ends = [to_seconds(r["time"]) for r in rows] + [to_seconds(rows[-1]["time"]) + 5.0]
    for i, row in enumerate(rows):
        mp3 = words_dir / f"{i:02d}.mp3"
        dur = synth(row["vo"], mp3, tts) if row["vo"].strip() else None
        slot = max(1.2, slot_ends[i + 1] - slot_ends[i])
        seg_dur = max(slot, (dur + 0.35) if dur else slot)
        timed.append({"row": row, "audio": mp3 if mp3.exists() else None,
                      "dur": round(seg_dur, 3), "start": round(t, 3), "vo_dur": dur or estimate_duration(row["vo"])})
        t += seg_dur

    # 2) 幻灯片 + 分段
    parts = []
    for i, item in enumerate(timed):
        png = seg_dir / f"{i:02d}.png"
        make_slide(item["row"], meta, i, len(timed), png)
        seg = seg_dir / f"{i:02d}.mp4"
        build_segment(png, item["audio"], item["dur"], seg)
        parts.append(seg)

    # 3) 拼接
    concat_list = seg_dir / "parts.txt"
    concat_list.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
    video = CACHE / f"{tag}.raw.mp4"
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                        "-i", str(concat_list), "-c", "copy", str(video)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"[render] 拼接失败: {r.stderr[-500:]}")

    # 4) 字幕（srt）+ 烧字幕
    srt_lines, n = [], 1
    for i, item in enumerate(timed):
        vo = item["row"]["vo"].strip()
        if not vo:
            continue
        end = item["start"] + min(item["vo_dur"], item["dur"] - 0.05)
        srt_lines.append(f"{n}\n{fmt_ts(item['start'])} --> {fmt_ts(end)}\n{vo}\n")
        n += 1
    srt_dir = ROOT / "subtitles"
    srt_dir.mkdir(exist_ok=True)
    srt = srt_dir / f"{tag}.srt"
    srt.write_text("\n".join(srt_lines), encoding="utf-8")

    out_dir = ROOT / "renders" / "成片"
    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / f"{tag}.mp4"
    if burn:
        # 烧字幕会压住主视觉大字，默认不烧（平台侧传 srt / 用平台自动字幕）。
        style = ("FontName=Noto Sans CJK SC,FontSize=16,PrimaryColour=&H00262220,"
                 "BackColour=&HFF000000,BorderStyle=1,Outline=1,Shadow=0,"
                 "OutlineColour=&H00F3ECDF,Alignment=2,MarginV=140")
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video),
                            "-vf", f"subtitles={srt}:force_style='{style}'",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                            "-pix_fmt", "yuv420p", "-c:a", "copy", str(final)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[render] 烧字幕失败，退回无字幕版: {r.stderr[-300:]}", file=sys.stderr)
            shutil.copy(video, final)
    else:
        shutil.copy(video, final)

    dur = probe_duration(final)
    info = {"ep": meta.get("ep"), "slug": slug, "video": str(final), "srt": str(srt),
            "duration_s": round(dur, 2), "segments": len(timed), "tts": tts}
    (out_dir / f"{tag}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--tts", default="qwen", choices=["qwen", "edge", "none"])
    ap.add_argument("--burn", action="store_true", help="把字幕烧进画面（默认不烧，只出 srt）")
    a = ap.parse_args()
    p = Path(a.episode)
    if not p.is_absolute():
        p = (ROOT / p).resolve()
    info = render(p, a.tts, burn=a.burn)
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
