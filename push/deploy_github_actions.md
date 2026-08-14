# 欧乐家微信营销 · GitHub Actions 免费自动推送

完全免费、无需绑卡、纯云端运行，不依赖本机 Mac 和 WorkBuddy。
每天 09:30 发当天话术任务卡+话术，17:00 发明日群发预告，由 GitHub 服务器定时触发。

## 前提
- 一个 GitHub 账号（免费）。
- 企微群机器人 Webhook（已在 push/config.json，实测 errcode:0）。

## 步骤

### 1. 建仓库
- 在 GitHub 新建一个**私有**仓库（推荐，避免内容公开），例如 `oulejia-wechat-push`。
- 把整个项目目录（含 `push/`、`wechat-calendar/`、`build/`）推上去。
  - 注意：`.github/workflows/push.yml` 必须一起提交，否则 Actions 不会生效。

### 2. 加密钥（绝不写进代码）
- 仓库 → Settings → Secrets and variables → Actions → New repository secret
- Name 填 `WEBHOOK`，Value 填完整 webhook 地址：
  `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=7c605bd5-581d-4cf3-a16e-da4e539b92cd`
- 保存。

### 3. 开启 Actions
- 仓库 → Actions 页面，找到「欧乐家微信营销推送」工作流，点 Enable。
- 默认 master/main 分支的 schedule 即可触发。

### 4. 手动验证一次
- Actions 页面 → 该工作流 → Run workflow（手动触发）。
- 看日志：应出现 `✓ 已推送明日预告 …` 或 `✓ 已推送 …`。
  - 手动触发走「发送当天」逻辑（因为你点的是 workflow_dispatch）；要测预告就等 17:00 自动跑，或临时把 cron 改一下本地验证。
- 群里应收到一条消息，确认链路通。

### 5. 之后全自动
- 每天 09:30 / 17:00 自动跑，无需任何人为操作。
- 唯一前提：GitHub 服务器在线（基本 100% 在线）。

## 注意事项
- **内容更新**：改了话术后，本地跑 `build/merge.py` 重生成 `content.json`，记得 `git push` 把新的 `content.json` 推上去，云端才会用新版。日历已排到 2027-08，日常无需动。
- **定时精度**：GitHub 共享 runner 的定时任务偶尔会延迟几分钟（少数情况十几分钟）。营销消息晚几分钟可接受；若要求严格准点，再用腾讯云 SCF（带绑卡免费额度）。
- **别双发**：本机 launchd plist 未加载、WorkBuddy 自动化已不可靠，都已不自动跑；只走 GitHub Actions 一条通道即可。
- **状态同步**：云端发送时本机日历 HTML 的「已发」标记不会自动变（发送在云端，本机 pushed_ids 不更新）。群内真实发送不受影响。需要本机也同步可加「云端写回」增强。
