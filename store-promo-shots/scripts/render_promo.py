#!/usr/bin/env python3
"""把截图批量合成成商店宣传图。

输入一份 promo.json，输出每个版式 × 每个尺寸的 PNG。
文案、背景、设备框全部用 HTML/CSS 画，再用无头 Chrome 按精确像素截图，
所以文字永远是清晰的矢量渲染，不会像图像模型那样把字画糊。

    python3 render_promo.py promo.json
    python3 render_promo.py promo.json --only iphone-6.9 --slide 1
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- 尺寸表

SIZES = {
    # Apple：6.9 寸是现行主力，一套传上去其余尺寸苹果会自动适配
    "iphone-6.9":  (1290, 2796),
    "iphone-6.5":  (1242, 2688),
    "iphone-5.5":  (1242, 2208),
    "ipad-13":     (2064, 2752),
    "ipad-12.9":   (2048, 2732),
    "mac":         (2880, 1800),
    # 微信小程序
    "wx-share":    (1080, 864),    # 5:4 分享卡
    "wx-poster":   (1080, 1920),   # 带码海报
    # Chrome Web Store
    "chrome-shot": (1280, 800),
    "chrome-tile": (440, 280),
    "chrome-marquee": (1400, 560),
    # 网页 / 社交
    "og":          (1200, 630),
    "web-hero":    (1920, 1080),
}

# 竖版尺寸用竖构图，横版用横构图
def is_portrait(w: int, h: int) -> bool:
    return h >= w


CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    shutil.which("chromium") or "",
    shutil.which("google-chrome") or "",
]


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if c and Path(c).exists():
            return c
    sys.exit("找不到 Chrome / Chromium。装一个，或用 --chrome 指定路径。")


# ---------------------------------------------------------------- 主题

PRESETS = {
    "light":     {"bg": "#F5F5F7", "fg": "#111318", "sub": "#5E6470", "device": "black"},
    "dark":      {"bg": "#0C0D10", "fg": "#FFFFFF", "sub": "#9AA3B2", "device": "black"},
    "brand":     {"bg": "#FFD400", "fg": "#0B1E3D", "sub": "#3A4A69", "device": "white"},
    "editorial": {"bg": "#C9A227", "fg": "#FFFFFF", "sub": "#F3E7C8", "device": "black",
                  "font": "serif"},
    "gradient":  {"bg": "linear-gradient(150deg,#FF7A52 0%,#F0442F 55%,#C9261C 100%)",
                  "fg": "#FFFFFF", "sub": "rgba(255,255,255,.88)", "device": "white"},
    "ink":       {"bg": "linear-gradient(140deg,#1B2740 0%,#122033 100%)",
                  "fg": "#FFFFFF", "sub": "#9FB0C9", "device": "black"},
}

FONTS = {
    "sans": '"PingFang SC","Hiragino Sans GB","Microsoft YaHei",-apple-system,'
            '"Helvetica Neue",Arial,sans-serif',
    "serif": '"Songti SC","Noto Serif CJK SC",Georgia,"Times New Roman",serif',
}


def resolve_theme(cfg: dict, override: dict | None) -> dict:
    base = dict(PRESETS.get(cfg.get("preset", "light"), PRESETS["light"]))
    base.update({k: v for k, v in cfg.items() if k != "preset"})
    if override:
        base.update({k: v for k, v in override.items() if k != "preset"})
        if "preset" in override:
            merged = dict(PRESETS.get(override["preset"], base))
            merged.update({k: v for k, v in override.items() if k != "preset"})
            base = merged
    base.setdefault("font", "sans")
    base.setdefault("device", "black")
    return base


# ---------------------------------------------------------------- 文案

def rich(text: str) -> str:
    """**加粗** 换成 <b>，换行换成 <br>。参考图里那种一句话里混字重的写法。"""
    out = html.escape(text or "")
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    return out.replace("\n", "<br>")


def text_units(line: str) -> float:
    """粗略估一行占多少个「字宽」：中文 1，拉丁数字约 0.55。"""
    cjk = len(re.findall(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]", line))
    return cjk * 1.0 + (len(line) - cjk) * 0.55


def fit_headline(text: str, avail_px: float, cap_px: float, max_lines_px: float) -> float:
    """按可用宽度倒推字号，长标题自己缩小，不会撑破画面。"""
    plain = re.sub(r"\*\*", "", text or "")
    lines = plain.split("\n") or [""]
    longest = max((text_units(l) for l in lines), default=1) or 1
    by_width = avail_px / longest
    by_height = max_lines_px / (len(lines) * 1.18)
    return max(12.0, min(by_width, by_height, cap_px))


# ---------------------------------------------------------------- 版式

LAYOUTS = {
    # 文案在上，截图从下方出血出去 —— 最常用，信息密度和展示面积平衡得最好
    "headline-top-bleed",
    # 文案在上，完整设备居中，四周留白 —— 适合界面本身好看的产品
    "headline-top-float",
    # 设备在上，文案在下 —— 序列里换一下节奏，避免五张一个样
    "headline-bottom",
    # 纯文案，没有截图 —— 放第一张当品牌开场，或最后一张当行动号召
    "statement",
    # 设备倾斜带透视 —— 单张里最抓眼的一种，别连用两张
    "tilted",
    # 截图铺满整屏，文案压在顶部 —— 适合内容型产品（照片、视频）
    "full-bleed",
    # 上下两张对比，带 BEFORE / AFTER 角标
    "before-after",
    # 多台设备叠放 —— 展示多个界面或多端
    "stack",
}


def device_frame(shot: str | None, style: str, w_ratio: float, extra_class: str = "",
                 kind: str = "phone") -> str:
    """设备框全部用 CSS 画，不依赖任何图片素材。
    kind: phone 手机 / browser 浏览器窗口 / none 只要圆角截图"""
    img = f'<img src="{shot}">' if shot else '<div class="blank"></div>'
    if kind == "none" or style == "none":
        return (f'<div class="dev bare {kind} {extra_class}" style="--w:{w_ratio}">'
                f'{img}</div>')
    if kind == "browser":
        return (f'<div class="dev browser {style} {extra_class}" style="--w:{w_ratio}">'
                f'<div class="chrome"><i></i><i></i><i></i><span class="url"></span></div>'
                f'<div class="scr">{img}</div></div>')
    return (f'<div class="dev phone {style} {extra_class}" style="--w:{w_ratio}">'
            f'<div class="scr">{img}<div class="notch"></div></div></div>')


BADGES = {
    "editors-choice": ("Editors'", "Choice"),
    "editor-choice": ("Editor's", "Choice"),
    "new-apps-we-love": ("New Apps", "We Love"),
    "design-award": ("Apple Design", "Award"),
}


def badge_html(kind: str | None) -> str:
    if not kind:
        return ""
    top, bottom = BADGES.get(kind, (kind, ""))
    return (f'<div class="badge"><span class="lf">&#127807;</span>'
            f'<div class="bt"><em>{html.escape(top)}</em><i>{html.escape(bottom)}</i></div>'
            f'<span class="lf flip">&#127807;</span></div>')


def build_body(slide: dict, th: dict, w: float, h: float, shots_root: Path) -> str:
    layout = slide.get("layout", "headline-top-bleed")
    if layout not in LAYOUTS:
        raise SystemExit(f"不认识的版式：{layout}\n可用：{sorted(LAYOUTS)}")

    def shot_url(key: str = "shot") -> str | None:
        v = slide.get(key)
        if not v:
            return None
        p = Path(v)
        if not p.is_absolute():
            p = shots_root / p
        if not p.exists():
            raise SystemExit(f"截图不存在：{p}")
        return p.resolve().as_uri()

    # 竖版默认手机框，横版默认浏览器窗口；单张可以在 manifest 里覆盖
    kind = slide.get("frame") or ("phone" if is_portrait(w, h) else "browser")

    head = slide.get("headline", "")
    sub = slide.get("sub") or ""
    badge = badge_html(slide.get("badge"))
    wordmark = slide.get("wordmark") or ""
    dev = th.get("device", "black")

    portrait = is_portrait(w, h)
    pad = 0.062 * min(w, h)
    # 横版文案只占左半边
    avail = (w - 2 * pad) * (1.0 if portrait else 0.50)
    cap = 0.125 * (w if portrait else h)
    room = (h - 2 * pad) * (0.34 if portrait else 0.62)
    hsize = fit_headline(head, avail, cap, room)
    ssize = hsize * 0.42

    txt = (f'<div class="copy"><h1 style="font-size:{hsize:.1f}px">{rich(head)}</h1>'
           + (f'<p style="font-size:{ssize:.1f}px">{rich(sub)}</p>' if sub else "")
           + "</div>")
    mark = f'<div class="wordmark">{rich(wordmark)}</div>' if wordmark else ""

    if layout == "statement":
        return f'<div class="wrap center">{txt}{badge}{mark}</div>'

    if layout == "headline-top-bleed":
        return (f'<div class="wrap top">{txt}{badge}'
                f'<div class="stagebleed">{device_frame(shot_url(), dev, .78, kind=kind)}</div>{mark}</div>')

    if layout == "headline-top-float":
        return (f'<div class="wrap top">{txt}{badge}'
                f'<div class="stage">{device_frame(shot_url(), dev, .66, kind=kind)}</div>{mark}</div>')

    if layout == "headline-bottom":
        return (f'<div class="wrap bottom">'
                f'<div class="stage">{device_frame(shot_url(), dev, .70, kind=kind)}</div>{txt}{badge}{mark}</div>')

    if layout == "tilted":
        return (f'<div class="wrap top">{txt}{badge}'
                f'<div class="stagebleed tilt">{device_frame(shot_url(), dev, .84, kind=kind)}</div>{mark}</div>')

    if layout == "full-bleed":
        u = shot_url()
        return (f'<div class="wrap full">'
                f'<div class="bleedimg"><img src="{u}"></div>'
                f'<div class="overlay">{txt}</div>{badge}{mark}</div>')

    if layout == "before-after":
        a, b = shot_url("shot"), shot_url("shot_after")
        if not b:
            raise SystemExit("before-after 版式需要 shot 和 shot_after 两张图")
        return (f'<div class="wrap top">{txt}'
                f'<div class="ba">'
                f'<div class="half"><img src="{a}"><span class="tagba">BEFORE</span></div>'
                f'<div class="half"><img src="{b}"><span class="tagba">AFTER</span></div>'
                f'</div>{mark}</div>')

    # stack
    extra = slide.get("shots") or []
    urls = [shot_url()] + [
        (shots_root / s).resolve().as_uri() if not Path(s).is_absolute() else Path(s).as_uri()
        for s in extra
    ]
    cards = "".join(
        device_frame(u, dev, .60, f"s{i}", kind=kind) for i, u in enumerate(urls[:3])
    )
    return (f'<div class="wrap top">{txt}{badge}'
            f'<div class="stagebleed stack">{cards}</div>{mark}</div>')


# ---------------------------------------------------------------- 页面

def page(slide: dict, th: dict, w: int, h: int, shots_root: Path, css: str,
         scale: int = 1) -> str:
    lw, lh = w / scale, h / scale          # CSS 里一律用逻辑像素
    body = build_body(slide, th, lw, lh, shots_root)
    font = FONTS.get(th.get("font", "sans"), FONTS["sans"])
    pad = 0.062 * min(lw, lh)
    orient = "port" if is_portrait(w, h) else "land"
    return f"""<!doctype html><meta charset="utf-8"><style>
:root{{
  --bg:{th['bg']}; --fg:{th['fg']}; --sub:{th.get('sub', th['fg'])};
  --pad:{pad:.2f}px; --W:{lw:.2f}px; --H:{lh:.2f}px; --font:{font};
}}
{css}
</style><div class="root {orient}">{body}</div>"""


# ---------------------------------------------------------------- 渲染

def render(chrome: str, html_text: str, out: Path, w: int, h: int, scale: int) -> None:
    tmp = out.with_suffix(".html")
    tmp.write_text(html_text, encoding="utf-8")
    cmd = [
        chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--allow-file-access-from-files",
        f"--force-device-scale-factor={scale}",
        f"--window-size={w // scale},{h // scale}",
        f"--screenshot={out}", tmp.resolve().as_uri(),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not out.exists():
        sys.exit(f"渲染失败：{out.name}\n{r.stderr[-800:]}")
    tmp.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="批量合成商店宣传图")
    ap.add_argument("manifest")
    ap.add_argument("--only", action="append", help="只渲染某个尺寸，可重复")
    ap.add_argument("--slide", type=int, help="只渲染第 N 张（从 1 开始）")
    ap.add_argument("--chrome", help="Chrome 可执行文件路径")
    ap.add_argument("--scale", type=int, default=2, help="渲染倍率，默认 2")
    args = ap.parse_args()

    mf_path = Path(args.manifest).resolve()
    mf = json.loads(mf_path.read_text(encoding="utf-8"))
    root = mf_path.parent
    shots_root = root / mf.get("shots_dir", ".")
    out_dir = root / mf.get("output", "promo-out")
    out_dir.mkdir(parents=True, exist_ok=True)

    css = (Path(__file__).parent.parent / "templates" / "base.css").read_text(encoding="utf-8")
    chrome = args.chrome or find_chrome()
    theme_cfg = mf.get("theme", {})
    sizes = args.only or mf.get("sizes", ["iphone-6.9"])
    slides = mf.get("slides", [])
    if args.slide:
        slides = slides[args.slide - 1: args.slide]

    made = 0
    for key in sizes:
        if key not in SIZES:
            sys.exit(f"不认识的尺寸：{key}\n可用：{', '.join(SIZES)}")
        w, h = SIZES[key]
        sub_dir = out_dir / key
        sub_dir.mkdir(exist_ok=True)
        scale = args.scale
        while scale > 1 and (w % scale or h % scale):
            scale -= 1
        for i, slide in enumerate(slides, 1):
            idx = slide.get("index", i)
            th = resolve_theme(theme_cfg, slide.get("theme"))
            name = f"{idx:02d}-{slide.get('layout', 'shot')}.png"
            render(chrome, page(slide, th, w, h, shots_root, css, scale),
                   sub_dir / name, w, h, scale)
            made += 1
            print(f"  {key}/{name}")

    print(f"\n出了 {made} 张，在 {out_dir}")
    print("提醒：截图必须来自真实运行的界面，画出来的假界面会被苹果按「与实际功能不符」驳回。")


if __name__ == "__main__":
    main()
