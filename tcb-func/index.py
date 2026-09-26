# -*- coding: utf-8 -*-
"""欧乐家 · 微信营销话术推送 —— 云函数入口（腾讯云 CloudBase 定时触发器）

为什么从 GitHub Actions 迁到这里
--------------------------------
GitHub Actions 的 schedule 是免费共享调度，官方明确"高负载期会延迟""建议避开整点"，
支持社区更直接说"不建议用于需要执行保证的生产任务"。实测（2026-09-22 延迟 4h53m、
9-25 延迟约 4.5h，相隔仅 3 天）已确认是常态问题，不是偶发。云函数定时触发器
按秒级 cron 触发，国内链路直连企业微信，可根治。

两条定时任务
------------
  09:30:00  -> 发当天任务卡 + 可复制话术
  17:00:00  -> 发明天群发预告

时区（务必看）
--------------
云函数运行环境默认是 UTC，而定时触发器的 cron 按**北京时间**解释。
两者错配会让 09:30 的推送在凌晨 1:30 发出去，所以这里做了三重保障：
  1) 部署时给函数设环境变量 TZ=Asia/Shanghai；
  2) 模式判定优先取 event["Time"]（腾讯云给的 0 时区时间戳）+8 换算；
  3) 落到"当前时刻"兜底。
并且**非预期时刻一律拒绝发送**（返回 refuse），宁可漏发也不要错发。
如需人工补发，设置环境变量 PUSH_MODE=push|remind 即可绕过时间判定。
"""
import os
import re
import sys
import importlib.util
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

_BASE = os.path.dirname(os.path.abspath(__file__))


def _load_by_path(mod_name, path):
    """按文件路径加载模块，避免 import push 命中同名内置模块（本地 Python 实测存在，
    命中后 __file__ 为 None 且拿不到 push.run，静默用错代码）。"""
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


_push = _load_by_path("_oulejia_push", os.path.join(_BASE, "push", "push.py"))

CST = timezone(timedelta(hours=8))
UTC = timezone.utc

# 允许的触发窗口：(小时, 分钟起, 分钟止, 模式)。落在窗口外 => 拒绝发送。
WINDOWS = ((9, 20, 59, "push"), (17, 0, 40, "remind"))


def _bj_now():
    """北京时间。容器时区默认 UTC，这里一律显式 +8 换算，不依赖容器 TZ 设置。"""
    return datetime.now(CST)


_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?)\s*(Z|z|[+-]\d{2}:?\d{2})?$")


def _bj_from_utc(raw):
    """把腾讯云给的 0 时区时间戳换算成北京时间；解析失败返回 None。

    刻意只用 strptime + 明细 regex，不用 datetime.fromisoformat ——
    云函数 runtime 是 Python 3.9，fromisoformat 要到 3.11 才认 "Z" 后缀。
    """
    if not raw:
        return None
    m = _TS_RE.match(str(raw).strip())
    if not m:
        return None
    core, off = m.group(1), m.group(2)
    # "2026-09-26T01:29:59" 长度 19（含秒），"2026-09-26T01:29" 长度 16
    naive = datetime.strptime(core, "%Y-%m-%dT%H:%M:%S" if len(core) == 19 else "%Y-%m-%dT%H:%M")
    if off is None or off in ("Z", "z"):
        tz = UTC
    else:
        sign = 1 if off[0] == "+" else -1
        digits = off[1:].replace(":", "")
        tz = timezone(sign * timedelta(hours=int(digits[:2]), minutes=int(digits[2:4])))
    return naive.replace(tzinfo=tz).astimezone(CST)


def _trigger_bj(event):
    """触发时刻的北京时间。优先 event.Time，其次 event.TriggerInfo.Time，最后当前时刻。"""
    if isinstance(event, dict):
        raw = event.get("Time") or ""
        if not raw:
            ti = event.get("TriggerInfo")
            if isinstance(ti, dict):
                raw = ti.get("Time") or ti.get("time") or ""
        if raw:
            bj = _bj_from_utc(raw)
            if bj:
                return bj
    else:
        try:
            bj = _bj_from_utc(str(event))
            if bj:
                return bj
        except Exception:
            pass
    return _bj_now()


def resolve_mode(event):
    """返回 "push" / "remind"，非预期时刻返回 ""（拒绝发送）。"""
    env = os.environ.get("PUSH_MODE", "").strip().lower()
    if env in ("push", "remind"):
        return env

    bj = _trigger_bj(event)
    h, m = bj.hour, bj.minute
    for hh, m0, m1, mode in WINDOWS:
        if h == hh and m0 <= m <= m1:
            return mode
    return ""


def main_handler(event, context):
    """CloudBase / SCF 入口函数名。"""
    event = event if isinstance(event, dict) else {}
    bj = _trigger_bj(event)
    mode = resolve_mode(event)

    if not mode:
        _push.log(
            "✗ 拒绝发送：触发时刻（北京时间 %s）不在允许窗口（09:20-09:59 / 17:00-17:40）。"
            "若为时区错配，请核对 cron 与环境变量 TZ。人工补发：设置 PUSH_MODE=push|remind。" %
            bj.strftime("%Y-%m-%d %H:%M:%S"))
        return {
            "ok": False,
            "reason": "unexpected_trigger_time",
            "bj_time": bj.strftime("%Y-%m-%d %H:%M:%S"),
        }

    _push.log("· 云函数触发 → 模式=%s，北京时间 %s" % (mode, bj.strftime("%Y-%m-%d %H:%M:%S")))

    opts = SimpleNamespace(
        date=_bj_now().strftime("%Y-%m-%d"),
        dry=False,
        next=False,
        remind=(mode == "remind"),
        msg_file=None,
    )
    _push.run(opts)
    return {"ok": True, "mode": mode, "bj_time": bj.strftime("%Y-%m-%d %H:%M:%S")}
