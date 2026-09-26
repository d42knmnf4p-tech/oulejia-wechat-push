# -*- coding: utf-8 -*-
"""云函数入口本地自检 —— 部署前必跑（tcb-func/deploy.py 会自动调用）。

安全约束：整个自检过程不得设置 WEBHOOK，否则会真的往企业微信群发消息。
这里强制摘掉 WEBHOOK，跑完再恢复。

跑法：
    python tcb-func/selftest.py
退出码 0 = 全绿，非 0 = 有失败项，禁止部署。
"""
import os
import sys
import json
import importlib.util

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

_SAVED_WEBHOOK = os.environ.pop("WEBHOOK", None)   # 摘掉，防止误发


def _run_tests():
    spec = importlib.util.spec_from_file_location("idx", os.path.join(BASE, "index.py"))
    idx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(idx)

    fails = []

    def chk(name, got, want):
        ok = got == want
        print("  %-40s got=%-10r %s" % (name, got, "OK" if ok else "-> FAIL, want %r" % want))
        if not ok:
            fails.append(name)

    print("=== 1. 模式判定 / 时区换算（最易搞反，重点验）===")
    # 腾讯云 event.Time 是 0 时区，北京时间 = UTC + 8
    cases = [
        ("2026-09-26T01:29:59Z", "push"),    # 北京 09:29:59
        ("2026-09-26T01:30:00Z", "push"),    # 北京 09:30:00 边界
        ("2026-09-26T01:59:59Z", "push"),
        ("2026-09-26T01:00:00Z", ""),        # 北京 09:00 —— 不在窗口
        ("2026-09-25T08:59:59Z", ""),        # 北京 16:59:59 —— 不在窗口
        ("2026-09-25T09:00:00Z", "remind"),  # 北京 17:00:00 边界
        ("2026-09-25T09:40:00Z", "remind"),
        ("2026-09-25T09:41:00Z", ""),        # 北京 17:41 —— 不在窗口
        ("2026-09-26T17:30:00Z", ""),        # 北京次日 01:30：时区错配也不会凌晨乱发
        ("2026-09-26T01:30:00+00:00", "push"),   # 带偏移量的另一种写法
    ]
    for raw, want in cases:
        chk("event.Time=%s" % raw, idx.resolve_mode({"Time": raw, "Type": "Timer"}), want)

    print("=== 2. 解析失败时不误判，退回当前时刻 ===")
    chk("坏时间戳 -> 按本地当前时刻", idx.resolve_mode({"Time": "not-a-time"}), idx.resolve_mode({}))

    print("=== 3. PUSH_MODE 强制覆盖（人工补发用）===")
    os.environ["PUSH_MODE"] = "remind"
    chk("PUSH_MODE=remind", idx.resolve_mode({"Time": "2026-09-26T01:30:00Z"}), "remind")
    os.environ["PUSH_MODE"] = "push"
    chk("PUSH_MODE=push", idx.resolve_mode({"Time": "2026-09-25T09:00:00Z"}), "push")
    os.environ.pop("PUSH_MODE", None)

    print("=== 4. 完整 handler（预览，不发送）===")
    pf = os.path.join(BASE, "wechat-calendar", "data", "pushed_ids.json")
    before = json.load(open(pf, encoding="utf-8"))["pushed_ids"]
    res = idx.main_handler({"Time": "2026-09-26T01:30:00Z", "Type": "Timer"}, None)
    print("  返回: %s" % json.dumps(res, ensure_ascii=False))
    after = json.load(open(pf, encoding="utf-8"))["pushed_ids"]
    chk("未写 pushed_ids（预览不发）", after, before)
    chk("ok=True", res.get("ok"), True)

    print("=== 5. 拒绝分支（错配时区不能乱发）===")
    res2 = idx.main_handler({"Time": "2026-09-26T17:30:00Z"}, None)
    print("  返回: %s" % json.dumps(res2, ensure_ascii=False))
    chk("拒绝时 ok=False", res2.get("ok"), False)

    print("\n结果: %s" % ("全部通过 ✓" if not fails else "失败项 -> %s" % fails))
    if fails:
        sys.exit(1)


try:
    _run_tests()
finally:
    if _SAVED_WEBHOOK is not None:
        os.environ["WEBHOOK"] = _SAVED_WEBHOOK
