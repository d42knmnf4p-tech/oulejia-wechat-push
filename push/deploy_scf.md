# 欧乐家微信营销 · 腾讯云函数 SCF 部署说明

目的：把推送逻辑部署到云端，**每天 09:30 自动发当天话术、17:00 发明日预告到企微群**，彻底不依赖 Mac 本机与 WorkBuddy 应用。

> 前置：① 一个腾讯云账号（已实名）；② 企微群机器人 Webhook（已在 `push/config.json` 的 `webhook` 字段）。
> 费用：SCF 按调用计费，本场景每天 2 次、每次几百毫秒，长期近乎免费（有免费额度）。

---

## 一、准备函数包（zip）

把以下文件按结构放到一个目录，打包成 zip：

```
oulejia-push/
├── push.py                      # 已含 main_handler 云函数入口
├── config.json                  # {"webhook": "https://qyapi.weixin.qq.com/...", "group_name": "欧乐家微信营销"}
└── wechat-calendar/
    └── data/
        └── content.json         # 由 build/merge.py 生成的一年内容库（85 条）
```

> 说明：`push.py` 路径解析基于自身位置，所以 `push.py` 与 `wechat-calendar/` 的相对关系必须保持如上（content.json 在 `wechat-calendar/data/` 下）。
> **零第三方依赖**：`push.py` 只用 Python 标准库（urllib/json），无需 pip 安装，选标准 Python3 运行时即可。
> 不需要上传 `merge.py` / `verify_review.py`（云端只负责发群，不重生成 HTML）。

## 二、创建云函数

1. 腾讯云控制台 → **云函数 SCF** → 新建函数 → **自定义创建**
2. 函数名称：`oulejia-wechat-push`
3. 运行环境：**Python 3.10**（或 3.9+）
4. 上传方式：选择上面的 zip
5. 执行方法：`push.main_handler` （文件名.函数名）
6. 提交

## 三、建两个定时触发器（Timer）

在函数「触发管理」→ 新建触发器，建两个：

| 触发器 | 触发周期 | Cron 表达式 | 附加信息（消息） |
|---|---|---|---|
| 发送当天 | 每天 09:30 | `30 9 * * *` | `{"mode":"push"}` |
| 明日预告 | 每天 17:00 | `0 17 * * *` | `{"mode":"remind"}` |

> ⚠️ **时区**：SCF 定时器默认以**函数所在地域时区**运行。在触发器配置里把时区设为 **(UTC+8) 上海**，再填上面的北京时间表达式即可；若选 UTC，则需换算（09:30 北京 = 01:30 UTC）。
> 「附加信息」里填的 JSON 就是 `main_handler(event)` 收到的 `event`，据此决定发当天还是发预告。

## 四、验证

1. 函数代码页点「测试」，用默认测试模板，把测试事件改成：
   ```json
   {"mode":"push"}
   ```
   点运行，返回应含 `"ok": true, "msg": "已推送 N 条"`，企微群收到消息即成功。
2. 再测 `{"mode":"remind"}`，群应收到「明日群发预告」。
3. 正式上线后，每天 09:30 / 17:00 自动运行，无需任何人工干预。

## 五、日常维护

- **改话术**：在本机用 `build/content_lib.py` 改 → 跑 `build/merge.py` 重生成 `content.json` → 把新 `content.json` 重新上传/覆盖到函数包（或在 SCF 控制台在线编辑该函数文件）。
- **换 webhook**：改 `config.json` 重新上传。
- **暂停**：在触发器里禁用即可。

## 六、与「本机方案」的关系（重要）

- 走了云端就**不要**再 load 本机的 launchd plist（`~/Library/LaunchAgents/com.oulejia.wechat.*.plist`），否则会**双发**。
- 本机 `push.py` 的 CLI 模式（`--date` / `--remind` / `--dry`）仍保留，作为**手动补发/自检**用；手动补发会更新本机 `push_status.json` 的 `pushed_ids`，让本机日历 HTML 正确显示「已发」。
- **已知限制**：云端定时发送时，本机日历 HTML 的「已发」状态默认不会自动变化（发送发生在云端，本机 `pushed_ids` 不更新）。如需本机日历也实时同步云端发送状态，需再加一个「云端写回状态」的增强（例如云端把已发 id 写入 COS/GitHub 公开文件，本机 HTML 改为 fetch 该远程状态）——可作为下一步，按需再做。
