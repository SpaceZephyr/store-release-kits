<h1 align="center">Store Release Kits</h1>

<p align="center"><code>store-release-kits</code></p>

<p align="center"><em>「代码写完以后，把上架这件事也认真做完。」</em></p>

<p align="center">
  <img alt="skills" src="https://img.shields.io/badge/Skills-3-111111">
  <img alt="platforms" src="https://img.shields.io/badge/Platforms-Chrome%20%7C%20WeChat%20%7C%20App%20Store-0A84FF">
  <img alt="output" src="https://img.shields.io/badge/Output-Release%20Kit-5856D6">
  <img alt="runtime" src="https://img.shields.io/badge/Runtime-Python%203-34C759">
</p>

<p align="center">
  License：未声明 · Codex Skills · <a href="https://github.com/SpaceZephyr/store-release-kits/issues">Issues</a>
</p>

Store Release Kits 是一组面向应用上架的 Codex Skills。给它一个真实仓库，它会先读代码和配置，再准备图标、截图、商店文案、隐私政策、审核说明与发布检查包。

不是套一份通用模板就结束。每个 Skill 都按对应平台的权限、素材尺寸、隐私申报和审核流程来工作，并把需要进入代码仓库的文件与独立发布物料分开保存。

## 包含的 Skills

| Skill | 适用平台 | 主要产出 |
| --- | --- | --- |
| [`chrome-extension-store-kit`](chrome-extension-store-kit/) | Chrome Web Store | 多尺寸图标、3 张以上截图、宣传图块、商店文案、权限理由、隐私政策、发布 ZIP |
| [`wechat-miniprogram-store-kit`](wechat-miniprogram-store-kit/) | 微信小程序 | 小程序图标、功能截图、审核资料、隐私保护指引矩阵、域名与资质检查、发布物料包 |
| [`app-store-release-kit`](app-store-release-kit/) | Apple App Store | App 图标、多设备截图、App Store 元数据、App Privacy、Review Notes、TestFlight 与发布检查 |

## 安装

使用 Skills CLI：

```bash
npx skills add SpaceZephyr/store-release-kits
```

安装时选择需要的 Skill。也可以把对应的根目录文件夹复制到 `~/.codex/skills/`。

## 使用

直接告诉 Codex 仓库路径和目标平台：

```text
使用 $chrome-extension-store-kit，为这个浏览器插件准备完整的 Chrome 商店上架物料。
```

```text
使用 $wechat-miniprogram-store-kit，审计这个小程序仓库并生成审核与发布资料。
```

```text
使用 $app-store-release-kit，为这个 iOS App 准备 App Store Connect 元数据、截图和隐私材料。
```

每个 Skill 都带有自己的：

- `SKILL.md`：完整工作流和完成标准
- `scripts/`：仓库审计、物料初始化与校验工具
- `assets/`：README、隐私政策、审核说明和发布清单模板
- `references/`：对应平台的规范与审核注意事项
- `agents/openai.yaml`：Codex 中的显示名称和默认调用提示

## 仓库结构

```text
store-release-kits/
├── chrome-extension-store-kit/
├── wechat-miniprogram-store-kit/
├── app-store-release-kit/
└── README.md
```

三个目录彼此独立，可以单独安装、修改和调用。

## 边界

- 平台后台字段、素材规格和审核规则会变化，正式提交前仍需核对当前后台。
- 静态扫描可以发现风险，不能替代真机测试、平台构建结果或法律判断。
- Skills 不会在没有明确授权时上传构建、提交审核、发布版本或更改商店账号。
- 不要把签名证书、上传私钥、AppSecret、访问令牌或真实用户数据提交到仓库。

## License

当前仓库尚未声明开源许可证。除非仓库后续明确添加 License，请不要默认获得复制、修改或再分发权。
