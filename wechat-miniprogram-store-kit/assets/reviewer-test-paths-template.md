# 审核人员测试路径

## 核心功能

- 起始页面：`{{START_PAGE}}`
- 前置条件：{{PREREQUISITES}}
- 测试数据：{{TEST_DATA}}

1. {{STEP_1}}
2. {{STEP_2}}
3. {{STEP_3}}

预期结果：{{EXPECTED_RESULT}}

## 隐私授权

1. 首次进入 {{PRIVACY_ENTRY}}。
2. 打开隐私保护指引。
3. 分别验证拒绝和同意。
4. 确认敏感接口仅在同意后、且用户主动触发时调用。

## 特殊流程

- 登录：{{LOGIN_FLOW}}
- 支付：{{PAYMENT_FLOW}}
- 定位/相机/相册：{{DEVICE_PERMISSION_FLOW}}
- 会员或角色：{{ROLE_FLOW}}
- 地区、时间或硬件限制：{{OTHER_RESTRICTION}}

## 安全交付

测试账号或密码通过 {{SECURE_CHANNEL}} 提供，不写入公开仓库。

