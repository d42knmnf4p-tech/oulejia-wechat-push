# -*- coding: utf-8 -*-
"""一键部署：把 wechat-push 云函数 + 定时触发器装到腾讯云 CloudBase。

用法（在仓库根目录执行）：
    python tcb-func/deploy.py --env <envId>            # 已有环境，直接部署
    python tcb-func/deploy.py --create                 # 环境不存在时自动建环境并部署
    python tcb-func/deploy.py --env <envId> --create   # 两者都传亦同

前置：
  1. tcb 已登录（SecretId/SecretKey 已配置）
  2. 仓库根目录有 .env.local，参照 tcb-func/.env.local.example：
        WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
        GITHUB_TOKEN=github_pat_xxx   （可选，用于回写日历"已发"状态）

部署流程：
  1. 先跑 selftest.py，不通过立即退出（宁可不部署，也不能部署一个错的代码）
  2. 生成 .cloudbaserc.json（含密钥，部署结束删除，绝不进仓库）
  3. tcb fn deploy wechat-push
  4. 建两条定时触发器：09:30 发当天 / 17:00 发预告
  5. 打印验证指引（tcb fn invoke 冒烟 + 日志核对触发时刻）

边界：本脚本只操作传入的欧乐家环境，不碰 CRM 的 wudu-test-* 环境。
"""
import os
import sys
import json
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUNC = os.path.join(ROOT, "tcb-func")
ENV_FILE = os.path.join(ROOT, ".env.local")
# 必须是 cloudbaserc.json（无点前缀）—— tcb CLI 只认这个名字，且 .gitignore 已忽略它
GEN_CFG = os.path.join(FUNC, "cloudbaserc.json")
DEFAULT_ALIAS = "oulejia"

# 关键约束：腾讯云一个云函数只能挂【一个】定时触发器，后建的会覆盖先建的。
# 所以必须建两个函数，各挂一条，靠函数名区分职责。
# wechat-push 不设 PUSH_MODE —— 让它继续走时间窗口判定，
# 万一被别的时刻误触也只会拒绝发送，不会重复发。
FUNCTIONS = [
    {
        "name": "wechat-push",
        "desc": "欧乐家微信营销：每天 09:30 发当天任务卡 + 可复制话术",
        "env": {},
        "trigger": ("push-daily", "0 30 9 * * * *"),
    },
    {
        "name": "wechat-remind",
        "desc": "欧乐家微信营销：每天 17:00 发明日群发预告",
        "env": {"PUSH_MODE": "remind"},
        "trigger": ("push-remind", "0 0 17 * * * *"),
    },
]


def die(msg, code=1):
    print("\n✗ %s" % msg)
    sys.exit(code)


def say(step, msg):
    print("\n== %s %s ==" % (step, msg))


def run(cmd, cwd=None, capture=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=capture, text=True)
    return r


def out_text(r):
    """tcb 的 - Loading data... 等进度行混在 stdout 里，取 JSON 部分。"""
    return "\n".join(l for l in (r.stdout or "").splitlines() if l.strip())


def load_env_local():
    if not os.path.exists(ENV_FILE):
        die("缺少 %s\n   请复制 tcb-func/.env.local.example 生成，至少需要 WEBHOOK。" % ENV_FILE)
    env = {}
    with open(ENV_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


# 云函数要跑的完整运行时 = 主仓代码的一份副本。
# 以前靠手工复制，改了 push/push.py 忘了同步 → 云函数跑的是旧代码，且部署不报错。
# 这里在部署前强制覆盖，杜绝两份漂移。
SYNC_MAP = [
    ("push", "push", (".py",)),
    ("wechat-calendar", "wechat-calendar", (".html", ".js", ".css", ".json")),
]


def sync_code_copy(env):
    """把仓库里的运行时代码同步进 tcb-func/ 部署包。

    只覆盖白名单后缀，忽略日志/推送状态等运行时产物，
    并在结束后校验 push.py 两份内容一致。
    """
    import shutil

    copied = []
    for src_rel, dst_rel, exts in SYNC_MAP:
        src = os.path.join(ROOT, src_rel)
        dst = os.path.join(FUNC, dst_rel)
        if not os.path.isdir(src):
            print("  ! 跳过同步：源目录不存在 %s" % src_rel)
            continue
        for root, _dirs, files in os.walk(src):
            for fn in files:
                if not fn.endswith(exts):
                    continue
                s = os.path.join(root, fn)
                d = os.path.join(dst, os.path.relpath(s, src))
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy2(s, d)
                copied.append(os.path.relpath(d, ROOT))

    main_py = os.path.join(ROOT, "push", "push.py")
    func_py = os.path.join(FUNC, "push", "push.py")
    if os.path.exists(main_py) and os.path.exists(func_py):
        a = open(main_py, encoding="utf-8").read()
        b = open(func_py, encoding="utf-8").read()
        if a != b:
            die("云函数副本 push/push.py 与主仓不一致。\n"
                "    说明同步逻辑失效了，请检查 SYNC_MAP 或手动比对两个文件。")
    print("  已同步 %d 个文件到部署包（push.py 一致性校验通过 ✓）" % len(copied))


def env_list():
    """返回 [{envId, packageName, ...}]。tcb env list --json 不带 alias 字段，只能按 envId 认。

    坑：tcb 3.7.x 的字段是 'envId'，3.8.4 改成 'EnvId'，硬编码任一都会 KeyError。
    这里按候选键名逐个取，兼容两版 CLI。
    """
    r = run(["tcb", "env", "list", "--json"])
    txt = out_text(r)
    try:
        data = json.loads(txt)
    except Exception:
        return []
    envs = data.get("data") or []
    if isinstance(envs, dict):            # 兜底：万一某版包成 {data: {list: [...]}}
        for v in envs.values():
            if isinstance(v, list):
                envs = v
                break
    out = []
    for e in envs:
        if not isinstance(e, dict):
            continue
        eid = (e.get("envId") or e.get("EnvId") or e.get("EnvironmentId") or "").strip()
        if not eid:
            continue
        e["envId"] = eid
        out.append(e)
    return out


def ensure_env(arg, create, alias):
    """确定目标环境 id。缺失时视 create 决定是否新建。"""
    envs = env_list()
    ids = [e["envId"] for e in envs]

    if arg:
        if arg in ids:
            return arg
        if not create:
            die("环境 %s 不在当前账号列表（现有：%s）。\n"
                "若是新环境，请加 --create 参数。" % (arg, ", ".join(ids) or "无"))

    if not create:
        die("未指定环境。先 `tcb env list` 查看，或加 --create 让脚本帮你建。")

    before = set(ids)
    print("→ 未找到目标环境，创建中（alias=%s，个人版 1 个月）…" % alias)
    r = run(["tcb", "env", "create", "--alias", alias,
             "--package", "baas_personal", "--region", "ap-shanghai",
             "--duration", "1", "--yes"])
    print(out_text(r) or (r.stderr or ""))
    if r.returncode != 0:
        die("环境创建失败。常见原因：账户余额不足（Insufficient account balance），"
            "请到 https://console.cloud.tencent.com/expense/recharge 充值后重试。")

    created = set(e["envId"] for e in env_list()) - before
    if not created:
        die("环境创建命令返回成功，但列表里没出现新环境，请到控制台确认后再执行本脚本。")
    new_id = sorted(created)[0]
    print("  已创建环境: %s" % new_id)
    return new_id


def main():
    args = sys.argv[1:]
    env_arg, create, alias, do_selftest = None, False, DEFAULT_ALIAS, True
    for i, a in enumerate(args):
        if a == "--env" and i + 1 < len(args):
            env_arg = args[i + 1]
        elif a == "--alias" and i + 1 < len(args):
            alias = args[i + 1]
        elif a == "--create":
            create = True
        elif a in ("-h", "--help"):
            print(__doc__)
            return
        elif a == "--no-selftest":
            do_selftest = False

    if do_selftest:
        say("1/5", "本地自检")
        r = run([sys.executable, os.path.join(FUNC, "selftest.py")], cwd=ROOT)
        print(r.stdout)
        if r.returncode != 0:
            print(r.stderr)
            die("自检未通过，已终止部署。")
        print("  自检通过 ✓")

    env = load_env_local()
    if not env.get("WEBHOOK"):
        die(".env.local 里没有 WEBHOOK，无法注入云函数。")
    env.setdefault("GITHUB_REPO", "d42knmnf4p-tech/oulejia-wechat-push")

    env_id = ensure_env(env_arg, create, alias)

    say("2/5", "生成 cloudbaserc（密钥仅存在于临时文件）")
    common_env = {
        "TZ": "Asia/Shanghai",
        "WEBHOOK": env["WEBHOOK"],
        "GITHUB_TOKEN": env.get("GITHUB_TOKEN", ""),
        "GITHUB_REPO": env.get("GITHUB_REPO", ""),
        "GITHUB_BRANCH": env.get("GITHUB_BRANCH", ""),
    }
    sync_code_copy(env)

    cfg = {
        "version": "2.0",
        "envId": env_id,
        "functions": [{
            "name": fn["name"],
            "runtime": "Python3.9",
            # 格式必须是 <文件名>.<函数名>，函数名要与 index.py 里的入口一致
            "handler": "index.main_handler",
            "description": fn["desc"],
            "timeout": 60,
            # 触发器不在配置里：CloudBase CLI 部署时不读 triggers，
            # 改为下面用 --trigger-name / --cron 显式创建，避免重复创建报错
            "envVariables": dict(common_env, **fn["env"]),
        } for fn in FUNCTIONS],
    }
    with open(GEN_CFG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print("  已生成 %s（部署结束即删除）" % GEN_CFG)

    try:
        say("3/5", "部署云函数")
        # 注意：tcb fn deploy 不接受 --env（环境只能来自 cloudbaserc.json 的 envId），
        # 也不接受默认的 functions/<name>/ 目录结构，必须用 --dir 指出代码目录。
        for fn in FUNCTIONS:
            print("  → %s" % fn["name"])
            r = run(["tcb", "fn", "deploy", fn["name"], "--force",
                     "--runtime", "Python3.9", "--install-dependency", "false",
                     "--dir", FUNC], cwd=FUNC)
            print(out_text(r) or (r.stderr or ""))
            if r.returncode != 0:
                print(r.stderr or "")
                die("云函数 %s 部署失败。" % fn["name"])

        say("4/5", "定时触发器（每个函数只挂一条，注意不要重复）")
        for fn in FUNCTIONS:
            tname, cron = fn["trigger"]
            r2 = run(["tcb", "fn", "trigger", "create", fn["name"],
                      "--trigger-name", tname, "--cron", cron], cwd=FUNC)
            txt = out_text(r2) or (r2.stderr or "")
            ok = "created successfully" in txt or "已存在" in txt
            print("  [%s] %s -> %s  %s" % (fn["name"], tname, cron,
                                           "OK" if ok else txt.strip()))
        print("  cron 按北京时间解释：09:30 发当天 / 17:00 发预告")
        print("  ⚠ 一个函数只能有一条定时器，多建会互相覆盖，务必逐个核对 detail")

        say("5/5", "完成")
        print("  环境: %s" % env_id)
        for fn in FUNCTIONS:
            print("  函数: %-14s 定时: %s %s" % (fn["name"], fn["trigger"][1], fn["desc"]))
        print("\n下一步（按顺序做，重点确认没有时区错配）：")
        print("  1) 两个函数分别冒烟：")
        for fn in FUNCTIONS:
            print("       tcb fn invoke %s --data '{\"Time\":\"2026-10-02T01:30:00Z\"}' --json"
                  % fn["name"])
        print("     期望返回 {\"ok\": true, \"mode\": \"push\"|\"remind\"}；")
        print("     返回 unexpected_trigger_time 即为时区错配。")
        print("  2) 逐函数核对定时器（一个函数只能有一条，看错就是被覆盖了）：")
        for fn in FUNCTIONS:
            print("       tcb fn detail %s | 看 Triggers" % fn["name"])
        print("  3) 确认准时后，再到 GitHub 停用两条定时（保留 workflow 做手动兜底），避免双发。")
    finally:
        if os.path.exists(GEN_CFG):
            os.remove(GEN_CFG)
            print("\n（已清理含密钥的临时配置文件 %s）" % GEN_CFG)


if __name__ == "__main__":
    main()
