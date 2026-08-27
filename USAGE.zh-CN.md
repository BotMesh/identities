# 在 ClawUp 上使用数字员工（中文使用指南）

本仓库提供 [ClawUp](https://clawup.org) identity（预配置技能包）。选择 identity 创建
agent 后，你就拥有一个住在飞书/Telegram 里的业务助理：**语音记客户、盯任务、管日程、走报销**。

| Identity | 包含技能 | 适合 |
|---|---|---|
| `digital-employee` 数字员工 | biz-core · crm-leads · pm-tasks · my-calendar · flow-expense · xlsx（官方）· skill-creator（官方） | 完整业务助理 |

---

## 一、创建 agent（约 10 分钟）

### 1. 注册 identity（管理员做一次即可）

登录 ClawUp 后台 → **Settings → Identities → Create New Identity**，从本仓库对应的
`identities/<名称>/identity.json` 里复制三样东西填入表单：

- **Slug / Name / Description**：照抄即可
- **技能列表**：把 `skills` 数组里的地址逐条粘贴（形如
  `github.com/BotMesh/identities/skills/biz-core`），平台会在建 agent 时自动下载安装

### 2. 创建 agent

- **New Agent** → Runtime 选 **OpenClaw**（identity 自动预装只对 OpenClaw 生效）
- Identity 选择上一步注册的 **Digital Employee**
- 模型：填自己的 API key，或使用平台托管计费

> **想用 Hermes 运行时？** Hermes 不支持 identity 预装，改为手动安装（效果相同）：
> ```bash
> hermes skills install github.com/BotMesh/identities/skills/biz-core
> hermes skills install github.com/BotMesh/identities/skills/crm-leads
> hermes skills install github.com/BotMesh/identities/skills/pm-tasks
> hermes skills install github.com/BotMesh/identities/skills/my-calendar
> hermes skills install github.com/BotMesh/identities/skills/flow-expense
> ```

### 3. 连接聊天渠道

- **飞书**：创建时选 Feishu，**扫码即完成**（App ID/Secret 自动填好），无需任何配置
- **Telegram**：先在 @BotFather 建 bot 拿 token，填入 ClawUp，向 bot 发消息后按提示输入配对码
- 建议两个都连：**语音消息在 Telegram 上支持最稳**，飞书语音请先实测一条

### 4. 初始化（对 agent 说三句话）

1. `帮我初始化业务数据库`（agent 会运行 biz-core 的 init_db.py，幂等可重复）
2. `我是 XX，在上海，时区 Asia/Shanghai，报销超过 500 元要单独跟我确认`
3. 让 agent 建 4 个定时任务：
   - 每天 08:00 —— 晨报（今日日程 + 到期任务）
   - 工作日 09:30 —— 任务跟进摘要
   - 每 15 分钟 —— 提醒扫描（不到点不发消息）
   - 每月 1 日 09:00 —— 报销月报 + 对账

---

## 二、日常怎么用（直接说人话）

### 📇 记客户（支持语音）

> 🎤 "刚见了华信的采购总监王莉，对 B 方案有兴趣，预算大概四十万，下周三前要给她发测算表。"

agent 会：自动转写 → 整理成客户档案（公司/联系人/阶段/金额/下一步）→ 同一客户自动归档
→ 顺手生成"发测算表"的待办 → 回一张确认卡片。
**没听清的它一定会问**（比如"大概四十万"会反问"记 40 万对吗？"），确认后才落档。

查询："华信现在什么进展？"／"这个月的新客户按金额排一下"
改错：对着确认卡片说"金额不对，是 45 万"

### ✅ 盯任务

- "官网改版立个项，拆一下任务，两个本周五前完成"
- "测算表那个任务标完成"／"设计稿卡住了，等李工回复"（卡住必须说原因）
- 每个工作日 09:30 自动收到：今天到期 / 已超期 / 卡住超 3 天 / 阻塞中，按项目分组

### 📅 管日程

- 🎤 "明天下午三点约张总看方案，提前半小时提醒我"
- "半小时后提醒我关火"（一次性提醒也行）
- 提醒精度约 ±15 分钟，重要会议建议提前量设 30 分钟以上

### 🧾 报销（说一句 → 拍发票 → 确认）

- 🎤 "报销昨天打车 86，去见华信客户" → 随手把发票拍照发给它
- 小额确认即入账；**超过 500 元会单独再确认一次**
- 每月 1 号自动收到上月汇总
- **对账**：随时问"报销都付清了吗？"——agent 运行复式记账核对，
  应付账户归零 = 每笔批准的报销都且仅支付了一次（服务器装了 `hledger`
  的话还会做机器校验；没装也不影响记账，只是少了校验环节）

---

## 三、数据在哪里、如何备份

- 所有数据在 agent 工作区的 `~/biz/` 目录：SQLite 数据库 + markdown 档案 +
  append-only 台账/日记账，**没有任何 SaaS 依赖**，结构详见
  [skills/biz-core/SCHEMA.md](skills/biz-core/SCHEMA.md)
- 备份 = 打包 `~/biz/` 一个目录；ClawUp 本身也会自动备份整个工作区，
  并支持 **Fork From** 一键克隆到新 agent
- 关键纪律（skills 内置，无需操心）：所有写入走脚本校验，AI 不直接改数据文件；
  金额、日期、人名没听清必回问；台账只增不改

## 四、常见问题

**Q：语音发了没反应？**
先用 Telegram 试（语音转写支持最明确）；飞书语音如有问题，打字完全不受影响。

**Q：想加新流程（请假、用印）？**
对 agent 说需求即可——`flow-expense` 就是流程模板骨架，配合官方 skill-creator，
新流程通常半天内可用。

**Q：想把资料变成它的知识？**
把产品资料、价格表、制度文档发给它说"学习这个"（Hermes 的 `/learn`），
自动转成按需加载的知识库。

**Q：几个人能一起用吗？**
当前版本是单人助理。需要老板审批、团队共用时，可升级 ClawUp Teams 多角色模式。

---

*English documentation: see [README.md](README.md). Issues welcome at
[BotMesh/identities](https://github.com/BotMesh/identities/issues).*
