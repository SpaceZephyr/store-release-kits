#!/usr/bin/env python3
"""配音校验：把每场配音用 Whisper 识别回文字，和旁白原文比字，找念错、漏念、吞字。

用法:
  <venv>/bin/python check_voice.py out/<style>-16x9            # 读 timeline.json 和 brief 里的旁白
需要: mlx-audio（Apple Silicon）和 whisper-large-v3-turbo 模型目录（环境变量 PROMO_ASR_MODEL，
默认 ~/.cache/promo-tts/whisper-turbo）。安装见 references/voice.md。

输出每场的字错率（CER）。英文产品名、数字的写法不同（Agent/agent、3.71/三点七一）会被算作差异，
所以只看 CER 高的那几场，再去听原音频。CER > 0.2 基本就是念错了或吞字了，换种子（voice.seed）重配。
"""
import json, os, re, sys
READ = re.compile(r"\{([^{}|]+)\|([^{}]+)\}")
from pathlib import Path

def norm(s):
    s = s.lower()
    return re.sub(r"[\s，。！？；：、,.!?;:“”\"'（）()·\-—]", "", s)

def cer(ref, hyp):
    a, b = norm(ref), norm(hyp)
    if not a: return 0.0
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, cb in enumerate(b, 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (ca != cb))
            prev, d[j] = d[j], cur
    return d[len(b)] / len(a)

def main():
    out = Path(sys.argv[1]).resolve()
    tl = json.loads((out / "timeline.json").read_text())
    brief = json.loads((out.parent.parent / "brief.json").read_text())
    from mlx_audio.stt.utils import load_model
    m = load_model(os.path.expanduser(os.environ.get("PROMO_ASR_MODEL", "~/.cache/promo-tts/whisper-turbo")))
    worst = 0
    for i, (s, b) in enumerate(zip(tl["scenes"], brief["scenes"])):
        if not s.get("voice") or not b.get("say"): continue
        hyp = m.generate(str(out / s["voice"]["file"]), language="zh").text.strip()
        say = READ.sub(r"\2", b["say"]); c = min(cer(say, hyp), cer(READ.sub(r"\1", b["say"]), hyp)); worst = max(worst, c)
        flag = "  <-- 去听一下" if c > .2 else ""
        print(f"s{i + 1:02d} CER {c:.2f}{flag}\n    原文: {say}\n    识别: {hyp}")
    print(f"最高 CER {worst:.2f}")

if __name__ == "__main__":
    main()
