# 从官网拿品牌素材

`scripts/fetch_brand.mjs` 用真实浏览器打开官网（桌面 1440×900 @2x + 手机 390×844 @3x），
截图前会清掉登录弹窗、气泡和 cookie 条，然后输出候选素材。**它给的是候选，最终用哪个要人来定。**

## 逐项核对

### logo

1. 先看 `logo-N-raw.*`：网页上 logo 用的原图，通常是透明底。分辨率低于 400px 宽时放到 1080p 画面里会糊。
2. 有 `logo-N.svg` 就用 SVG。单色 logo 在 brief 里设 `"logoMono": true`，颜色会跟着风格走
   （黑底变白、粗野风变黑、MG 风用品牌色）。
3. 都不理想时，去同一品牌的其他页面找 SVG：App 下载页、登录页、开发者平台、品牌资源页（brand / press / media kit）。
   用 puppeteer 打开这些页面，找 `svg` 元素里尺寸合适、class 带 logo 的那个，存成 `.svg`。
4. `logo-N.png` 是元素截图，经常带着背后的 banner，一般不要直接用。

> B 站示例：首页 logo 是 220px 宽的白色 PNG，太小；`app.bilibili.com` 导航栏里有完整的矢量 SVG（`svg.navbar_logo`），用的是这个。

### 主色

`colors` 按「可见面积 × 权重」排序，灰色已排除。排第一的经常是按钮或链接的蓝色，不一定是品牌主色。
和 logo、官方 icon 的颜色对一下；知名品牌直接用官方色值（B 站粉 `#FB7299`、蓝 `#00AEEC`）。

### slogan

页面上通常找不到 slogan。按顺序找：
1. `title` 和 `description` 里的短句
2. App Store / 应用商店的副标题
3. 品牌最近的广告片、开屏、官方账号简介
4. 都没有就问用户，或者根据产品定位写一句，并告诉用户这句是你写的

### 截图

- `shot-desktop.png` 首屏，`shot-desktop-2/3.png` 往下两屏，`shot-mobile.png` 手机版首屏。
- 检查有没有残留的弹窗、半透明遮罩、加载中的骨架屏。有就加长 `--wait` 重抓，或手动截。
- 首页内容是实时的（推荐流、轮播图），每次抓都不一样。片子里出现的第三方内容（封面、昵称）只用于演示。
- 需要登录才能看的功能页，请用户提供截图。

### 场景和功能

`navTexts`（导航文字）和 `keywords` 是写「使用场景」最直接的来源：
B 站的导航里有番剧、知识、游戏、音乐、美食……挑 4–6 个最有代表性的做 `cards`。

## 数据

用户量、营收、增长这类数字一定要查最新的官方来源（财报、官方公告），在 kicker 里写时间。
不确定就不放，宁可少一个 stats 场景。

## 实战记录（2026-10 做 AI 智能体产品案例时）

| 产品 | 首页能拿到什么 | 真正好用的素材在哪 |
| --- | --- | --- |
| Muse（muse.ai） | 登录框 + 一句口号 | 页面下方的吉祥物图、og-image；logo 是 SVG（`muse-logo.svg`） |
| Grok Bot | `x.ai/grok-bot` 是 404 | 产品页 `x.ai/bot` 有完整应用窗口截图；发布文章 `x.ai/news/introducing-grok-bot` 有正文；logo 只在 og-image 里，用 `extract_logo.py --mode white` 抠 |
| dots | `openai.com/dots` 发布文章 | 正文配图里有 6 张官方界面图（`img-*.webp`）；logo 是黑底发光字，`--mode on-dark` 抠，只适合深色风格 |
| Cue | `manus.im/cue` 是 404 | 发布文章里找到独立官网 `cue.im`：中文 slogan、四项身份能力、界面图、`logo-black.svg` 都在这里 |

经验：
- 产品名猜出来的网址经常是 404，先搜官方发布文章，再从文章里的链接找产品官网。
- 发布文章（blog / news）写的是官方口径的卖点，适合写旁白；产品官网的界面图更完整。两边都抓。
- 同一站点短时间连续抓好几次会被 Cloudflare 拦（openai.com、x.ai 都遇到过），抓到的素材及时存好，不要反复重抓。
- 白色 logo 放在浅色风格里看不见，在 brief 的 `css` 里写 `.logo img { filter: brightness(0); }` 压成黑色。
