# -*- coding: utf-8 -*-
"""
欧乐家 · 微信营销话术自动推送
每周五 09:30 把当天要发的话术推到企业微信群，销售长按复制直接发客户。

用法：
  python push.py               # 推送"今天/最近的下一条"
  python push.py --date 2026-08-14
  python push.py --dry         # 只打印不发送（自检用）
"""
import json, os, sys, argparse, urllib.request, urllib.error
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONTENT = os.path.join(ROOT, "wechat-calendar", "data", "content.json")
CONFIG = os.path.join(HERE, "config.json")
STATUS = os.path.join(ROOT, "wechat-calendar", "data", "push_status.json")
# 已发送 id 的“单一数据源”：存于仓库内，云端发送后由 workflow 写回，本地打开日历时实时拉取
PUSHED = os.path.join(ROOT, "wechat-calendar", "data", "pushed_ids.json")
LOG = os.path.join(HERE, "push.log")
WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def log(msg):
    line = "[%s] %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_json(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def record_pushed(ids):
    """把已发送 id 写入仓库内的 pushed_ids.json（云端写回 + 本地烘焙共用单一数据源）。"""
    try:
        data = load_json(PUSHED, {}) or {}
    except Exception:
        data = {}
    s = set(data.get("pushed_ids") or [])
    for i in ids:
        s.add(i)
    data["pushed_ids"] = sorted(s)
    data["updated_at"] = date.today().isoformat()
    try:
        with open(PUSHED, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log("✗ 写 pushed_ids.json 失败: %s" % e)


def post(webhook, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(webhook, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        res = json.loads(r.read().decode("utf-8"))
    if res.get("errcode") != 0:
        raise RuntimeError("企微返回错误: %s" % res)
    return res


def pick(items, target, allow_next=False):
    """选出目标日内容。默认严格匹配当天（无排期则静默跳过），
    allow_next=True 时才顺延取之后最近的一条（人工手动预览用）。"""
    same = [i for i in items if i["date"] == target]
    if same or not allow_next:
        return same
    later = sorted([i for i in items if i["date"] > target], key=lambda x: x["date"])
    return later[:1]


def upcoming_extras(items, target, days=7):
    """未来 N 天内的节日加发，提前预告"""
    t = datetime.strptime(target, "%Y-%m-%d").date()
    out = []
    for i in items:
        if i["kind"] != "extra":
            continue
        d = datetime.strptime(i["date"], "%Y-%m-%d").date()
        if t < d <= t + timedelta(days=days):
            out.append(i)
    return out


def build_card(db, it, extras):
    """任务卡（markdown）"""
    d = datetime.strptime(it["date"], "%Y-%m-%d").date()
    cat = db["cats"][it["cat"]]["name"]
    kind = "节日加发（短版）" if it["kind"] == "extra" else "周五主推"

    L = []
    L.append("# 📣 本次微信营销任务")
    L.append("**%d月%d日（%s）%s 准点发送**" % (d.month, d.day, WD[d.weekday()], it["time"]))
    L.append("")
    L.append("> 板块：**%s**　类型：%s\n> 主题：**%s**\n> 切入点：%s" % (cat, kind, it["title"], it["hook"]))
    L.append("")
    if it.get("asset"):
        L.append('<font color="warning">📷 本条必须配图：%s</font>' % it["asset"])
        L.append("")
    L.append("**发送要点**")
    for i, t in enumerate(it["tips"], 1):
        t = t.replace("★", "")
        L.append("%d. %s" % (i, t))
    L.append("")
    if extras:
        L.append("**⏰ 本周还有加发**")
        for e in extras:
            ed = datetime.strptime(e["date"], "%Y-%m-%d").date()
            L.append("· %d月%d日（%s）%s" % (ed.month, ed.day, WD[ed.weekday()], e["title"]))
        L.append("")
    L.append('<font color="comment">话术全文见下一条，长按可直接复制。发送前务必替换 {称呼}{销售名}{小区名}。</font>')
    return "\n".join(L)


def build_text(it):
    """纯话术（text 类型，长按即得干净文本）"""
    return it["content"]


def kind_label(it):
    """给提醒卡用的人话类型标签"""
    if it["kind"] == "friday":
        return "周五主推"
    if it["cat"] == "solar":
        return "节气关怀"
    if it["cat"] == "festival":
        return "节假日问候"
    return "加发"


def build_remind(db, items_tomorrow, extras):
    """前一日 17:00 给销售部的『明日群发预告』（内部知会，非客户话术）"""
    t = items_tomorrow[0]
    d = datetime.strptime(t["date"], "%Y-%m-%d").date()
    L = []
    L.append("# 🔔 明日群发预告")
    L.append("")
    L.append("**明天 %d月%d日（%s）%s** 将在群里发送一条微信营销消息，请各位销售提前留意 👇"
             % (d.month, d.day, WD[d.weekday()], t["time"]))
    L.append("")
    for it in items_tomorrow:
        cat = db["cats"][it["cat"]]["name"]
        L.append("> 板块：**%s**　类型：%s" % (cat, kind_label(it)))
        L.append("> 主题：**%s**" % it["title"])
        L.append("> 切入点：%s" % it["hook"])
        L.append("")
    L.append("**请提前准备**")
    L.append("1. 消息发出后客户可能来问，先心里有数")
    L.append("2. 话术里的 {称呼} {销售名} {小区名} 记得换成真实信息")
    L.append("3. 有客户回复，30 分钟内响应")
    L.append("")
    if extras:
        L.append("**📅 随后一周还有加发**")
        for e in extras:
            ed = datetime.strptime(e["date"], "%Y-%m-%d").date()
            L.append("· %d月%d日（%s）%s" % (ed.month, ed.day, WD[ed.weekday()], e["title"]))
        L.append("")
    L.append('<font color="comment">明细任务卡与可复制话术，将在发送当天 09:30 推送。本条仅为提前知会。</font>')
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--next", action="store_true", help="当天无排期时顺延推送下一条")
    ap.add_argument("--remind", action="store_true", help="提醒模式：推送明天的群发预告（前一天 17:00 用）")
    ap.add_argument("--msg-file", default=None, help="读取文件内容作为自定义消息发送（群公告用）")
    args = ap.parse_args()

    db = load_json(CONTENT)
    if not db:
        log("✗ 找不到内容库 %s" % CONTENT)
        sys.exit(1)

    cfg = load_json(CONFIG, {}) or {}
    webhook = (os.environ.get("WEBHOOK") or cfg.get("webhook") or "").strip()

    # ---- 自定义群公告发送 ----
    if args.msg_file:
        try:
            with open(args.msg_file, encoding="utf-8") as f:
                msg = f.read().strip()
        except Exception as e:
            log("✗ 读取消息文件失败: %s" % e)
            sys.exit(1)
        if not webhook:
            print("【自定义消息预览】\n" + msg)
            log("✗ 未配置 webhook，已改为本地预览。")
            return
        post(webhook, {"msgtype": "text", "text": {"content": msg}})
        log("✓ 已发送自定义消息（%d 字）" % len(msg))
        return

    target = args.date or date.today().isoformat()
    picks = pick(db["items"], target, allow_next=args.next)

    # ---- 提醒模式：前一天 17:00 推「明日群发预告」 ----
    if args.remind:
        t = datetime.strptime(target, "%Y-%m-%d").date()
        tomorrow = (t + timedelta(days=1)).isoformat()
        picks = [i for i in db["items"] if i["date"] == tomorrow]
        if not picks:
            log("· 明天 %s 无排期内容，跳过提醒" % tomorrow)
            return
        extras = upcoming_extras(db["items"], tomorrow)
        card = build_remind(db, picks, extras)
        if args.dry or not webhook:
            print("\n" + "=" * 56)
            print("【明日预告 markdown】\n" + card)
            print("=" * 56 + "\n")
            if not webhook and not args.dry:
                log("✗ 未配置 webhook，已改为本地预览。")
            return
        post(webhook, {"msgtype": "markdown", "markdown": {"content": card}})
        log("✓ 已推送明日预告 %s（%d 条）" % (tomorrow, len(picks)))
        return
    if not picks:
        log("· %s 无排期内容，跳过" % target)
        return

    extras = upcoming_extras(db["items"], target)
    sent = 0

    for it in picks:
        card = build_card(db, it, extras if it["kind"] == "friday" else [])
        text = build_text(it)

        if args.dry or not webhook:
            print("\n" + "=" * 56)
            print("【任务卡 markdown】\n" + card)
            print("-" * 56)
            print("【话术 text】\n" + text)
            print("=" * 56 + "\n")
            if not webhook and not args.dry:
                log("✗ 未配置 webhook，已改为本地预览。请填写 push/config.json")
            continue

        post(webhook, {"msgtype": "markdown", "markdown": {"content": card}})
        post(webhook, {"msgtype": "text", "text": {"content": text}})
        sent += 1
        log("✓ 已推送 %s [%s] %s" % (it["date"], db["cats"][it["cat"]]["name"], it["title"]))

    if sent:
        ids = [i["id"] for i in picks]
        record_pushed(ids)
        # 本地运行：更新配置状态横幅 + 重新烘焙 HTML；云端运行由 workflow 负责写回仓库
        _st = load_json(STATUS, {}) or {}
        _st["configured"] = True
        _st["last_push"] = datetime.now().strftime("%m-%d %H:%M")
        _st["last_items"] = ids
        try:
            with open(STATUS, "w", encoding="utf-8") as f:
                json.dump(_st, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        if os.environ.get("GITHUB_ACTIONS") == "true":
            log("· 云端运行：已写入 pushed_ids.json，将由 workflow 写回仓库")
        else:
            # 本地：把“已发布”状态烘焙进日历 HTML，打开即正确显示
            try:
                import subprocess
                subprocess.run([sys.executable, os.path.join(ROOT, "build", "merge.py")], check=False)
            except Exception:
                pass
    elif not webhook:
        with open(STATUS, "w", encoding="utf-8") as f:
            json.dump({"configured": False}, f, ensure_ascii=False, indent=2)


def main_handler(event, context):
    # 已废弃：本项目改用 GitHub Actions（push.py 的 __main__ 入口），不再需要云函数入口。
    raise NotImplementedError("main_handler 已废弃，请使用 GitHub Actions 工作流调用 `python push.py`")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("✗ 推送失败: %s" % e)
        sys.exit(1)
