<div align="center">

# 金融保安.skill

### 投简历之前，先把不该说的、不能证实的和可能发错的拦下来

![金融保安.skill 主视觉](skills/finance-security-guard/assets/hero.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-333333.svg)](LICENSE)
![Agent Skill](https://img.shields.io/badge/Agent_Skill-Standard-4f8b62)
![Runtime](https://img.shields.io/badge/Runtime-Codex_%C2%B7_Claude_Code_%C2%B7_Cursor-8f43d8)
![Local First](https://img.shields.io/badge/Privacy-Local_First-f5b800)

**简历证据检查 · 隐私清理 · 公开发布审计 · 投递前预检**

[它能做什么](#它能做什么) · [怎么用](#怎么用) · [效果示例](#效果示例) · [安全原则](#安全原则) · [安装](#安装)

</div>

---

## 它能做什么

金融求职材料最危险的地方，往往不是“不够好看”，而是：

- 把 JD 里的要求写成自己已经做过的经历；
- 简历、邮件、行研作品和面试话术互相打架；
- 公开仓库里混入真实邮箱、手机号、本机路径或授权码；
- 收件人、标题、附件没核对，就准备真实发送；
- PDF、DOCX 没读到正文，AI 却假装已经看过。

`金融保安.skill` 把检查放在生成、公开和发送之前：

| 阶段 | 做什么 | 产出 |
| --- | --- | --- |
| ① 收材料 | 按简历、JD、项目、附件分类保存原件 | 文件清单与路由回执 |
| ② 查证据 | 区分候选人事实、岗位要求、缺口与禁止使用内容 | 证据台账 |
| ③ 查隐私 | 检查手机号、邮箱、本机路径和疑似秘密字段 | 脱敏检查结果 |
| ④ 守动作 | 核对收件人、主题、附件、dry-run 和即时确认 | `READY / REVIEW / BLOCKED` |

它不会替你做招聘决策，也不会为了提高匹配度虚构经历。

---

## 和通用 AI 有什么不同

通用 AI 倾向于“先给一版听起来不错的答案”。金融保安先问：

1. 这句话来自简历、项目文件，还是用户刚刚确认？
2. 这是候选人事实，还是 JD 对理想候选人的要求？
3. 文件正文真的读取了吗？
4. 这份材料是私人整理、公开发布，还是准备真实发送？
5. 外部动作发生前，是否完成了当次确认？

```text
用户材料
→ 文件登记
→ 证据分类
→ 隐私检查
→ 缺口提示
→ 生成或修改材料
→ 发送前预检
→ 用户即时确认
```

---

## 怎么用

### 本地网页

下载仓库后：

```powershell
.\install.ps1
.\start.ps1
```

也可以双击 `start.cmd`。

网页会引导你选择：

- **申请一个岗位**：简历 + JD + 可选项目材料；
- **准备一场面试**：简历 + 可选 JD 和笔记；
- **检查求职材料**：批量检查现有文件；
- **整理公开作品**：按公开发布标准检查项目和报告。

文件只交给 `127.0.0.1` 上的本地服务。页面不会自动上传或发送。

### 在 Agent 中调用

```text
这是我的简历、目标 JD 和项目材料。
请使用 $finance-security-guard 先检查证据和隐私，
再告诉我哪些内容可以用于投递，哪些必须补充或删除。
```

### 命令行

```powershell
# 隐私扫描
python .\skills\finance-security-guard\scripts\finance_guard.py scan `
  --input ".\examples\fictional-application"

# 独立自测
python .\skills\finance-security-guard\scripts\finance_guard.py selftest

# 发送或公开前检查
python .\skills\finance-security-guard\scripts\finance_guard.py preflight `
  --manifest ".\manifest.json"
```

---

## 效果示例

同一批虚构材料，金融保安不会输出一个“87 分匹配度”，而会给出可行动的判断：

| 检查项 | 结果 |
| --- | --- |
| Excel 数据整理 | 有简历证据，可以使用 |
| Wind / iFinD | JD 要求，但候选人材料没有证据 |
| 招聘邮箱 | 来自 JD，提示人工核对，不自动视为泄露 |
| PDF 正文 | 文件已保存，但没有抽取就明确标记未读取 |
| 外部动作 | `NONE`，没有上传、公开或发送 |

完整虚构输入位于 [`examples/fictional-application`](examples/fictional-application)。

---

## 安全原则

### 永远阻断

- 密码、SMTP 授权码、Token、Cookie、API Key、私钥；
- 把没有证据的经历写成已完成事实；
- 收件人不明确、附件缺失或仍有占位符；
- 未完成 dry-run 与即时确认的真实发送；
- 公开包中的私人简历、真实投递日志和本机用户路径。

### 需要人工确认

- JD 中的招聘邮箱；
- 私人工作区里的本机路径；
- 无法判断用途的邮箱或联系方式；
- 证据不足但可能真实存在的能力描述。

### 不会做

- 绕过 CAPTCHA、OTP、登录或授权；
- 存储邮箱授权码；
- 自动群投、自动交易或自动发布；
- 根据学校或实习品牌替招聘方筛选候选人；
- 把“正则命中次数”包装成真实泄露人数。

---

## 仓库结构

```text
finance-security-guard/
├─ skills/finance-security-guard/
│  ├─ SKILL.md                  # Agent 边界、角色、流程与红线
│  ├─ agents/openai.yaml        # Skill 展示信息
│  ├─ assets/setup.html         # 本地引导网页
│  ├─ scripts/finance_guard.py  # 扫描、路由、预检与自测
│  ├─ scripts/launch_guard.py   # 本地服务启动器
│  └─ references/               # 安全策略、工作区契约、发布门槛
├─ examples/                    # 完全虚构的可复现实例
├─ install.ps1                  # 安装到 Codex Skills
├─ start.ps1                    # 打开本地网页
└─ start.cmd                    # Windows 双击启动
```

所有用户运行数据进入被 Git 忽略的 `workspace/`，不会随仓库提交。

---

## 安装

```powershell
git clone https://github.com/shenlingxuan831/finance-security-guard.git
cd finance-security-guard
.\install.ps1
.\start.ps1
```

环境要求：

- Windows；
- 推荐安装 `uv`，脚本会自动准备 Python 3.12；
- 或直接安装 Python 3.10 及以上版本；
- 无第三方 Python 依赖。

---

## 当前边界

当前版本属于 **Demo-Ready**：

- 本地引导、文本检查、证据摘录、隐私扫描、路由和预检已可运行；
- PDF、DOCX、XLSX 会保存并明确标记为未读取；
- 尚未接入 PDF/DOCX 正文抽取；
- 尚未内置真实 SMTP 发送器；
- 不承诺求职结果，也不构成投资或职业保证。

---

## License

[MIT](LICENSE)。项目主视觉为本项目原创生成资产。
