---
name: product-promo-video
description: "产品宣传视频制作：把产品资料（用户提供，或从官网自动抓取 logo、slogan、主色、截图）做成带动效、带配音、带字幕和配乐的宣传片 MP4。内置 8 种产品界常见的动效风格（发布会极简、科技光晕、快节奏大字、扁平 MG、杂志编辑、新粗野、赛博故障、便当格），同一份脚本可以一键换风格、换横竖版。当用户说「做个产品宣传视频」「产品宣传片」「产品介绍视频」「promo video」「launch video」「给 XX 官网做个视频」「换个风格再出一版」时触发。"
---

# Product Promo Video

把产品做成 30–60 秒的宣传片：**脚本（brief.json）→ 配音 → HTML 动效 → 逐帧渲染 → 混音 → MP4**。

画面全部是 HTML/CSS，由一个按时间推进的运行时驱动，无头 Chrome 逐帧截图，所以文字清晰、
每一帧都能复现，换风格、换品牌色、换横竖版都不用重做素材。

和 [store-release-kits](https://github.com/SpaceZephyr/store-release-kits) 的关系：
`store-promo-shots` 做商店静态宣传图，这个 Skill 做动态宣传片，两者用的截图可以通用。

## 硬规矩

1. **界面必须是真的。** 产品截图来自官网或用户给的真实截图，不画产品里没有的界面。
2. **数字必须有出处。** 用户量、增长率这类数字要么用户给，要么查财报或官方公告，并在
   kicker 里写上时间（如「2026 年第二季度」）。查不到就不放 stats 场景。
3. **logo 用原件。** 优先用矢量 SVG，其次是透明底的 PNG 原图。不要拿带背景的截图当 logo，也不要自己画。
4. **不用 emoji。** 标题、旁白、标签、卡片里都不能出现 emoji，会显得不专业。卡片图标用
   [Lucide](https://lucide.dev/icons) 线性图标，按名字引用（`"icon": "gamepad-2"`），颜色自动跟随风格。
   `make.py` 渲染前会扫描整份 brief，发现 emoji 直接报错并列出位置。颜文字（如 `(゜-゜)つロ`）和箭头不算 emoji。
5. 做别人家的产品（比如拿 B 站当示例）只能用于演示和内部提案，不要冒充官方发布。

## 流程

### 1. 收集产品资料

用户给了资料就用用户的。没给就从官网抓：

```bash
cd <本 Skill 目录>/scripts
npm install --silent   # 第一次用时装 puppeteer-core 和 lucide-static（图标）
node fetch_brand.mjs https://example.com <工作目录>/brand
```

抓回来的东西：`brand.json`（标题、描述、关键词、导航文字、主色候选、logo 候选）、
`logo-*.png`、`logo-*-raw.*`（logo 原图）、`icon-*`、`shot-desktop*.png`（三屏）、`shot-mobile.png`，
以及 `img-*`：页面正文里所有宽度 ≥ 600 的配图和视频封面。发布文章、产品页里的界面图和场景图通常都在这里，
比首屏截图好用得多。

抓完**一定要人工看一遍**，常见的坑见 [references/brand-extraction.md](references/brand-extraction.md)：
- 产品首页常常只有登录框或一句口号，真正的界面图在**发布文章 / 产品介绍页**里，两处都要抓
- logo 截图会带上背后的 banner，要用 `-raw` 原图，或者去别的页面（App 下载页、登录页）找 SVG
- logo 只出现在宣传图里时，用 `extract_logo.py` 抠成透明底（见下）
- 主色候选按面积排序，排第一的不一定是品牌色，要和 logo 颜色对一下
- slogan 往往不在页面上，要查（官网 title、App Store 副标题、品牌广告）
- 有的站会对无头浏览器弹 Cloudflare 验证，连续抓几次后更容易触发；抓不到正文就用截图和搜索结果

从宣传图里抠 logo：

```bash
python3 scripts/extract_logo.py og-image.png logo.png --mode white   --box 540,440,1420,660  # 彩色底上的白字
python3 scripts/extract_logo.py og-image.png logo.png --mode on-dark  --box 400,150,1200,560  # 黑底上的彩色/发光字
python3 scripts/extract_logo.py banner.png   logo.png --mode on-light                         # 白底上的深色字
```

需要从截图里裁局部界面时，直接用 PIL 按像素裁（截图是 2 倍图，网页上的坐标要乘 2）。

必须出现在片子里的：**logo、slogan、主色、核心使用场景、真实界面**。

### 2. 写脚本 brief.json

照抄 [assets/brief.template.json](assets/brief.template.json)。每个场景一个对象，`say` 是这一场的旁白。
场景时长由旁白长度自动决定，不用手动对时间。

可用场景类型：

| type | 画面 | 必填 |
| --- | --- | --- |
| `logo` | logo 入场 + slogan | `tagline` |
| `slogan` | 大标题，一句话说清产品 | `title` |
| `feature` | 文案一侧，截图一侧（浏览器框或手机框），可慢推镜到重点 | `title` `image` |
| `cards` | 场景卡片网格（2–6 张，线性图标或图片） | `items[{icon/image,label,desc}]` |
| `stats` | 数字滚动 | `items[{value,label}]` |
| `tags` | 标签流：`danmaku` 弹幕飞过 / `cloud` 散点弹出 / `marquee` 整行滚动 | `items[]` |
| `gallery` | 多张截图墙缓慢平移，中间压一句话 | `images[]` |
| `end` | logo + slogan + 行动按钮 | `cta` |

常规结构（40 秒左右，6–8 场）：logo → slogan → 2~3 个 feature/cards → stats 或 tags → end。
脚本和配音的写法见 [references/script-writing.md](references/script-writing.md)。

### 3. 选风格

八种风格，详细说明、配色、适合什么产品见 [references/styles.md](references/styles.md)：

| 风格 | 一句话 | 适合 |
| --- | --- | --- |
| `apple-keynote` | 黑底大字，模糊淡入，慢 | 硬件、旗舰功能、高端品牌 |
| `saas-glow` | 深色光斑网格，截图 3D 立起来 | 软件、AI、开发者工具、B 端 |
| `kinetic` | 巨字砸入，闪切，每场换底色 | 短视频平台投放、活动、年轻品牌 |
| `flat-mg` | 几何图形漂浮，逐字弹跳，色块转场 | 消费 App、社区、教育 |
| `editorial` | 纸感衬线，遮罩上推，页码 | 内容、文化、生活方式 |
| `neo-brutal` | 粗描边硬投影，阶梯运动 | 独立开发、创意工具、潮牌 |
| `cyber-glitch` | 霓虹扫描线，乱码解码，故障转场 | 游戏、电竞、潮流科技 |
| `bento` | 浅灰圆角卡片，缩放入场 | 功能多的产品、效率工具 |

用户没指定时，按产品调性挑 2–3 个差别大的风格各出一版让用户选。品牌色会自动覆盖风格的强调色。

### 4. 先出静帧，再渲染

```bash
python3 scripts/make.py brief.json --style flat-mg --preview    # 只出 HTML + 每场静帧（几十秒）
python3 scripts/make.py brief.json --style flat-mg              # 出成片（40 秒的片子约 2 分钟）
python3 scripts/make.py brief.json --style kinetic --format 9:16  # 竖版
python3 scripts/make.py brief.json --style kinetic --remix      # 只改了配乐/音量时，不重渲画面
```

**每次都先 `--preview`，再拼一张总览图自己检查**：

```bash
ffmpeg -y -loglevel error -pattern_type glob -i "out/<style>-16x9/stills/s*.jpg" \
  -vf "scale=640:-1,tile=2x4:padding=6" -frames:v 1 out/<style>-16x9/contact.jpg
```

检查清单：文字有没有溢出或折行难看、标题有没有压到卡片或数字、字幕有没有挡住内容、
截图里有没有登录弹窗、logo 颜色在这个底色上看不看得清。改完再出成片。

成片出来后再抽几帧看动效：入场时刻、转场中间各抽一帧（`ffmpeg -ss <秒> -i x.mp4 -frames:v 1`）。
场景起止时间在 `out/<style>/timeline.json` 里。

### 5. 交付

产出在 `brief 所在目录/out/<style>-<format>/`：
- `<name>-<style>-<format>.mp4`：成片（H.264 + AAC）
- `index.html`：浏览器直接打开就是实时预览，`?t=12.5` 停在某一秒
- `stills/`、`timeline.json`、`voice/`、`bgm.wav`

告诉用户：用了哪个配音引擎、配乐是合成的临时曲（正式投放建议换授权音乐）、数据出处。

## 配音和配乐

- 配音引擎按顺序尝试：`edge-tts`（微软在线音色，最自然）→ macOS `say`（婷婷，机械感较重）。
  `voice.engine` 可指定 `edge` / `say` / `kokoro` / `none`；每场也可以用 `voiceFile` 换成真人录音。
  edge-tts 偶尔会被微软接口拒绝（403），这时会自动退回 say，**交付时要说明用的是哪个**。
- 每种风格有默认音色和语速（见 `make.py` 的 `STYLE_META`），可用 `voice.voice` / `voice.rate` 覆盖。
- 配乐 `"bgm": "auto"` 会按风格合成一段无版权的临时曲（`scripts/bgm.py`，五种情绪）。
  正式片写 `"bgm": "music/xxx.mp3"` 用授权音乐。旁白响起时配乐会自动压低。

## 改造和扩展

- 单场改转场：场景里写 `"transition": "circle"`（可选 cut fade blur push pushUp zoom circle shapeWipe flash glitchCut stripes）
- 单场换底色主题：在 brief 的 `css` 字段里写额外 CSS
- 品牌字体：`"fontFile": "fonts/xxx.ttf"`
- 改颜色：`product.colors.accent / accent2`，或 `tokens` 覆盖任意变量（bg、fg、sub、card…）
- 新增风格：`templates/styles.js` 加一项（tokens + 文字/图片/卡片入场 + 转场 + 背景），
  `templates/styles.css` 加皮肤，`make.py` 的 `STYLE_META` 加配乐和音色，`references/styles.md` 写说明
- 新增动效预设：`templates/runtime.js` 的 `TEXT` / `IMAGE` / `TRANS`

## 案例

[`examples/`](examples/) 里有五个真实产品的完整案例（brief.json + 总览图），同一套 Skill、不同风格：

| 产品 | 风格 | 素材来源 |
| --- | --- | --- |
| 哔哩哔哩 | flat-mg / kinetic / saas-glow / cyber-glitch / kinetic 竖版 | bilibili.com、app.bilibili.com、2026Q2 财报 |
| Meta Muse | bento | muse.ai |
| SpaceXAI Grok Bot | editorial | x.ai/bot、x.ai/news/introducing-grok-bot |
| OpenAI dots | apple-keynote | openai.com/dots |
| Manus Cue | neo-brutal | cue.im、manus.im/blog/introducing-manus-2-0 |

## 依赖

Node 18+、ffmpeg、Chrome（或 puppeteer 缓存的 chrome-headless-shell）、Python 3 + numpy（合成配乐用）。
可选：`uvx`（edge-tts）。不调用任何图像生成 API。

## 边界

- 不生成产品界面，不做实拍。需要演示交互流程时，让用户录屏后放进 `feature`（目前只支持静态图，录屏需要先截关键帧）。
- 合成配乐只是临时曲，不能替代正式配乐。
- 中文字体用系统的 PingFang（最粗是 Semibold）。想要更重的字，在 brief 里用 `fontFile` 指定字体文件。
