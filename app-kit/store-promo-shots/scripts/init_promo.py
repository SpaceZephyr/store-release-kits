#!/usr/bin/env python3
"""扫一个截图目录，生成 promo.json 的骨架。

    python3 init_promo.py ./shots --name 清单 --out promo.json

它会按文件名排序把截图填进去，自动排好版式节奏（避免五张一个样），
并从第一张截图里取一个主色当品牌色。文案留空，需要你或 Agent 补。
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import zlib
from pathlib import Path

EXTS = {".png", ".jpg", ".jpeg", ".webp"}

# 五张一套的默认节奏：开场 → 主功能 → 换构图 → 抓眼 → 广度
RHYTHM = ["statement", "headline-top-bleed", "headline-top-float", "tilted", "stack"]


def png_size(p: Path) -> tuple[int, int] | None:
    try:
        with p.open("rb") as f:
            head = f.read(33)
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return struct.unpack(">II", head[16:24])
    except Exception:
        return None


def dominant_color(p: Path) -> str | None:
    """从 PNG 里粗略取一个主色。取不到就返回 None，让用户自己给。"""
    try:
        raw = p.read_bytes()
        if raw[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        w, h = struct.unpack(">II", raw[16:24])
        bit_depth, color_type = raw[24], raw[25]
        if bit_depth != 8 or color_type not in (2, 6):
            return None
        channels = 3 if color_type == 2 else 4
        idat = b"".join(
            raw[i + 8: i + 8 + struct.unpack(">I", raw[i - 4: i])[0]]
            for i in (m.start() for m in re.finditer(b"IDAT", raw))
        )
        data = zlib.decompress(idat)
        stride = w * channels + 1
        buckets: dict[tuple[int, int, int], int] = {}
        prev = bytearray(w * channels)
        pos = 0
        for y in range(min(h, 400)):
            if pos + stride > len(data):
                break
            ft = data[pos]
            line = bytearray(data[pos + 1: pos + stride])
            # 只处理最常见的两种过滤器，够用了
            if ft == 2:
                for i in range(len(line)):
                    line[i] = (line[i] + prev[i]) & 0xFF
            elif ft not in (0, 2):
                pos += stride
                prev = line
                continue
            if y % 7 == 0:
                for x in range(0, w * channels, channels * 9):
                    r, g, b = line[x], line[x + 1], line[x + 2]
                    key = (r // 32, g // 32, b // 32)
                    buckets[key] = buckets.get(key, 0) + 1
            prev = line
            pos += stride
        if not buckets:
            return None
        r, g, b = max(buckets, key=buckets.get)
        return "#{:02X}{:02X}{:02X}".format(r * 32 + 16, g * 32 + 16, b * 32 + 16)
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description="从截图目录生成 promo.json 骨架")
    ap.add_argument("shots_dir")
    ap.add_argument("--name", default="产品名")
    ap.add_argument("--out", default="promo.json")
    ap.add_argument("--sizes", default="iphone-6.9")
    args = ap.parse_args()

    d = Path(args.shots_dir)
    if not d.is_dir():
        raise SystemExit(f"目录不存在：{d}")
    shots = sorted(p for p in d.iterdir() if p.suffix.lower() in EXTS)
    if not shots:
        raise SystemExit(f"{d} 里没找到截图（支持 {'/'.join(sorted(EXTS))}）")

    portrait = []
    for p in shots:
        wh = png_size(p)
        portrait.append(wh is None or wh[1] >= wh[0])

    brand = dominant_color(shots[0])
    out_path = Path(args.out)
    shots_rel = d.resolve()
    try:
        shots_rel = shots_rel.relative_to(out_path.resolve().parent)
    except ValueError:
        pass

    slides = []
    for i, p in enumerate(shots):
        layout = RHYTHM[min(i + 1, len(RHYTHM) - 1)] if i else RHYTHM[1]
        slide = {
            "layout": layout,
            "headline": "",                       # 待填：一行不超过 8 个汉字
            "sub": "",                            # 可留空
            "shot": p.name,
        }
        if layout == "stack":
            slide["shots"] = [q.name for q in shots[:3] if q.name != p.name][:2]
        if not portrait[i]:
            slide["frame"] = "browser"
        slides.append(slide)

    # 第一张换成开场白
    slides.insert(0, {"layout": "statement",
                      "headline": f"你好，\n我们是**{args.name}**。",
                      "wordmark": ""})

    mf = {
        "product": {"name": args.name, "tagline": ""},
        "shots_dir": str(shots_rel),
        "output": "promo-out",
        "theme": {"preset": "brand" if brand else "light",
                  "bg": brand or "#F5F5F7",
                  "fg": "#111318", "device": "white", "font": "sans"},
        "sizes": [s.strip() for s in args.sizes.split(",") if s.strip()],
        "slides": slides,
    }
    out_path.write_text(json.dumps(mf, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"写好了 {out_path}，{len(slides)} 张")
    if brand:
        print(f"品牌色从第一张截图里取的：{brand}，不对就直接改 theme.bg")
    print("headline 全是空的，填完再跑 render_promo.py")


if __name__ == "__main__":
    main()
