---
name: store-promo-shots
description: "Batch-compose App Store, WeChat Mini Program, Chrome Web Store and web promo images from real product screenshots: pick a layout, write the headline copy, apply a brand theme, and render pixel-exact PNGs for every required store size in one pass. Use when a user has screenshots of an iOS/macOS app, a web app, a browser extension or a mini program and asks for store screenshots, feature graphics, promotional tiles, marquee images, share cards or launch visuals."
---

# Store Promo Shots

把真实截图批量合成为各商店要的宣传图：**文案 + 背景 + 截图**三层，一次出全套尺寸。

这个 Skill 只负责「合成」。截图本身、商店文案、隐私政策由三个发布 Kit 负责：
[`app-store-release-kit`](../app-store-release-kit/)、
[`wechat-miniprogram-store-kit`](../wechat-miniprogram-store-kit/)、
[`chrome-extension-store-kit`](../chrome-extension-store-kit/)。
它们跑完拿到的截图，直接喂给这里。

## 先说一条硬规矩

**截图必须来自真实运行的界面。** 苹果对着截图审功能，画一张产品里没有的界面上去，
会按「与实际功能不符」驳回。这个 Skill 做的是给真截图加文案、背景和设备框，
不生成假界面。用户要是拿不出截图，先去把应用跑起来截，别替他画。

## 怎么开始

1. 找截图。优先用发布 Kit 已经产出的那份，其次问用户截图目录在哪。
   确认每张图对应哪个功能，以及它是手机、桌面网页还是小程序。
2. 确认品牌：主色、文字色、字体走无衬线还是衬线、设备框要白边还是黑边。
   用户给不出就从截图里取主色，并明确告诉他你取了什么颜色。
3. 写一份 `promo.json`（照抄 [assets/promo.template.json](assets/promo.template.json)）。
4. 渲染：

   ```bash
   python3 scripts/render_promo.py promo.json
   ```

5. 把出图给用户看，按反馈改 `promo.json` 再跑一次。改文案和配色不用重新截图。

只想先看一张：`--slide 2`；只出一个尺寸：`--only iphone-6.9`。

## 序列怎么排

商店列表页**只露出前两张**，所以第一张永远放最想让人看见的东西，不要放设置页。

一套 5 张的常规排法：

| 位置 | 放什么 | 建议版式 |
| --- | --- | --- |
| 1 | 一句话说清楚这产品是什么 | `statement` 或 `headline-top-bleed` |
| 2 | 最强的那个功能 | `headline-top-bleed` |
| 3 | 第二个功能，换个节奏 | `headline-top-float` 或 `headline-bottom` |
| 4 | 差异化的点 / 效果对比 | `tilted` 或 `before-after` |
| 5 | 广度：多界面、多端、生态 | `stack` |

五张全用同一个版式会很闷，三张之后一定换一次构图或换一次底色。

## 八种版式

详细说明和什么时候用哪个，见 [references/layouts.md](references/layouts.md)。

| 版式 | 长什么样 | 适合 |
| --- | --- | --- |
| `headline-top-bleed` | 文案在上，截图从底部出血 | 默认首选，信息量和展示面积最平衡 |
| `headline-top-float` | 文案在上，完整设备居中留白 | 界面本身好看、想让人看全 |
| `headline-bottom` | 设备在上，文案在下 | 序列里换节奏 |
| `statement` | 纯文案，没有截图 | 第一张开场，或最后一张做行动号召 |
| `tilted` | 设备带透视倾斜 | 单张最抓眼，别连用两张 |
| `full-bleed` | 截图铺满，文案压顶部 | 照片、视频这类内容型产品 |
| `before-after` | 两张上下对比，带 BEFORE/AFTER | 修图、清理、优化类 |
| `stack` | 三台设备叠放 | 展示广度或多端 |

## 文案规则

- 主标题一行不超过 8 个汉字，两行封顶。渲染器会按可用宽度自动缩字号，
  但缩到很小就说明这句话本身太长了，回去改文案，别指望缩字号救。
- 副标题可以没有。有就写具体的东西（「语音、粘贴、分享都能进」），
  不要写「高效便捷」这种。
- 想让句子里某几个字跳出来，用 `**` 包起来：`到点提醒**不到点不打扰**`。
  加粗的那几个字会保持粗体，其余部分自动退到常规字重。
- 换行用 `\n`，自己控制断句，别让它在奇怪的地方折行。

更多见 [references/copy-rules.md](references/copy-rules.md)。

## 尺寸

`sizes` 里写几个就出几套，同一份 manifest 竖版横版都能用：
竖版自动用手机框，横版自动换成浏览器窗口框（Chrome 扩展和网页应用是桌面的，
塞一只整手机很怪）。单张想强制指定，在那张 slide 上写 `"frame": "phone" | "browser" | "none"`。

常用：`iphone-6.9`（App Store 现行主力）、`ipad-13`、`wx-share`（小程序 5:4 分享卡）、
`chrome-marquee`（1400×560 首页推荐位）、`chrome-tile`（440×280 列表小图）、`og`（1200×630）。
全表见 [references/store-sizes.md](references/store-sizes.md)。

## 主题

六个预设：`light` `dark` `brand` `editorial` `gradient` `ink`。
`theme` 写在顶层是整套统一，写在单张 slide 上是只改那一张——
参考图里常见的做法就是五张里穿插一张深色或一张品牌色，让序列有呼吸。

任何一项都能单独覆盖：`bg` 支持纯色和 CSS 渐变，`fg` 文字色，`sub` 副标题色，
`device` 取 `white` / `black` / `none`，`font` 取 `sans` / `serif`。

## 实现说明

文案、背景、设备框全部是 HTML/CSS，用无头 Chrome 按精确像素截图。
所以文字是矢量渲染，永远清晰，不会出现图像模型把字画糊的情况；
换品牌色就是改一个变量，不用重做一套图。

需要本机装了 Chrome / Chromium / Edge 任意一个，不需要联网，不调任何图像 API。

## 边界

- 不生成界面。截图得是真的。
- 不做视频预览（App Preview）。
- 小程序码、二维码这类必须从官方后台导出，这里只留位置。
- 出图是设计稿，提交前自己再核一遍当前商店的尺寸要求，规则会变。
