# 配音：本地开源 TTS 和校验

默认用 [yovoice](https://github.com/leemysw/yovoice)（Apache-2.0）的独立 CLI 跑 Qwen3-TTS，全程在本机推理，不需要账号和网络。
没装时 `make.py` 自动退回 edge-tts，再退回 macOS `say`。

## 安装（一次）

```bash
# 1. CLI：从 Releases 下载对应平台的 cli 压缩包，解压后保留同级 tools/ 目录
gh release download -R leemysw/yovoice -p "yovoice-*-cli-macos-arm64.zip" -p SHA256SUMS.txt
shasum -a 256 -c SHA256SUMS.txt --ignore-missing
unzip yovoice-*-cli-macos-arm64.zip -d ~/.local/opt/yovoice
# 2. 推理引擎（Mac 用 Metal）和模型（2.8 GB，ModelScope 国内快）
~/.local/opt/yovoice/yovoice setup --backend metal
~/.local/opt/yovoice/yovoice models download qwen3-tts-customvoice-q8 --source modelscope
```

`make.py` 按 `$YOVOICE_BIN` → PATH 里的 `yovoice` → `~/.local/opt/yovoice/yovoice` 的顺序找 CLI。
同一个数据目录（`~/.yovoice`）同时只能跑一个命令，下载模型时不能配音。

## 选音色

Qwen3-TTS CustomVoice 内置 9 个音色，中文用这四个：

| 音色 | 声音 | 默认给哪些风格 |
| --- | --- | --- |
| `Serena` | 温和的年轻女声，咬字最稳 | saas-glow、editorial、bento |
| `Vivian` | 明亮、带点个性的年轻女声 | flat-mg、neo-brutal |
| `Dylan` | 清亮的年轻男声（略带京腔） | kinetic、cyber-glitch |
| `Uncle_Fu` | 低沉醇厚的成熟男声，语速慢 | apple-keynote |

`Eric` 是成都口音，宣传片里不要用。`description` 是演绎描述（「沉稳自信，清晰有力」），会影响语气，不会换音色。

```json
"voice": { "engine": "auto", "speaker": "Dylan", "description": "科技产品宣传片旁白，沉稳自信，清晰有力", "seed": 7 }
```

同一段文字、同一个种子，每次生成结果一样（缓存在 `.tts-cache/raw-*.wav`）。某一场念得不好，在那一场里写 `"seed": 11` 单独换一版。

## 读音标注

中文模型读英文专名不稳定：「Grok Bot」读成 Rockball，「Cue」被吞掉。旁白里写 `{字幕写法|配音读法}`：

```json
"say": "{Grok Bot|格罗克波特}，能交付真活儿的 AI 队友。"
"say": "{Cue|Q}，现已开放抢先体验。"
```

字幕和旁白对位用前者，配音念后者。常见英文词（Agent、macOS、Windows、WhatsApp、AI）一般能读对，先不标，校验出问题再标。

## 后处理

`make.py` 对 yovoice 的输出做三件事：去掉首尾静音；超过 0.18 秒的句中停顿压到 0.16 秒左右（模型在顿号处会停 0.6–0.9 秒，宣传片里显得拖）；
按风格的 `rate` 用 atempo 微调语速（取 edge 语速的一半，kinetic 约快 7%）。

## 校验

配音生成后用 Whisper 识别回来和原文比字：

```bash
# 一次性准备（Apple Silicon）
uv venv -p 3.12 ~/.cache/promo-tts/.venv && uv pip install -p ~/.cache/promo-tts/.venv/bin/python mlx-audio
# 模型从 ModelScope 下（Hugging Face 在国内很慢）：mlx-community/whisper-large-v3-turbo 的 config.json、weights.safetensors，
# 加上 AI-ModelScope/whisper-large-v3-turbo 的 tokenizer 文件（tokenizer.json、vocab.json、merges.txt、preprocessor_config.json 等），
# 放进同一个目录 ~/.cache/promo-tts/whisper-turbo

HF_HUB_OFFLINE=1 ~/.cache/promo-tts/.venv/bin/python scripts/check_voice.py out/<style>-16x9
```

看 CER（字错率）：识别结果里「它/他」「Agent/agent」这类差异会算进去，0.1 以下基本没问题；
超过 0.2 的场去听原音频，多半是英文名读错或吞字，用读音标注或换种子。

## 实测记录（2026-10，Cue / Grok Bot / Muse）

- 同一句「把几个 Agent 拉进同一个群聊……」：Serena、Dylan 识别零差错；Vivian 一处近音；Uncle_Fu 语速最慢（34 字 10.4 秒）；Eric 错得最多。
- Grok Bot：原样写识别成 Rockball / Rocobot；`格罗克波特` 识别正确。
- Cue：原样写有时被吞掉；`{Cue|Q}` 后正常。
- Muse：种子 7 时第 2 场读成 Mills，换种子 11 后正确，但第 7 场又出错；所以用逐场种子。
- 速度：M4 上每场 12–30 秒（第一次要加载模型）。
