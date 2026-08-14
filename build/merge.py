# -*- coding: utf-8 -*-
"""合并内容库 + 注入 SOP 指南，输出 wechat-calendar/data/content.json"""
import json, os, sys
from datetime import date
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from content_lib import build_items

items = build_items()
items.sort(key=lambda x: (x["date"], x["kind"] != "friday"))

CATS = {
    "daily":    {"name": "日常问候", "color": "#3B82F6", "desc": "节气养生、用气安全、生活关怀。全年占比最高，是维系关系的基本盘，绝不带价格。"},
    "solar":    {"name": "节气关怀", "color": "#0EA5E9", "desc": "24 节气当天发送，顺时关怀（通风/饮食/添衣/用气安全），用户提供的专属措辞，零推销。"},
    "festival": {"name": "节假日问候", "color": "#EF4444", "desc": "中国所有节假日+传统节日+现代节日祝福。纯祝福零推销，老年客群认同感最强，一个节日都不能漏。"},
    "case":     {"name": "安装效果", "color": "#10B981", "desc": "真实装机实拍、服务故事、口碑case。用事实建立信任，必须配真实图片。"},
    "promo":    {"name": "活动优惠", "color": "#F59E0B", "desc": "价格与活动信息。全年严格控制在20%以内，超了客户就屏蔽你了。"},
}

GUIDE = {
    "title": "50-60岁客群 · 微信沟通铁律",
    "rules": [
        {"k": "称呼先行", "v": "每条开头必须换成真实称呼：张哥 / 李孃孃 / 王叔。群发感是第一杀手，一个「亲」就废掉整条。"},
        {"k": "断句换行", "v": "每行不超过 15 字，多用空行。老花眼看不了大段文字，密密麻麻的直接划走。"},
        {"k": "表情克制", "v": "每条 3-6 个，用具象温暖类（☀️🍲🌷❤️🙏），禁用年轻人梗表情（🤡💀🫠）和网络缩写。"},
        {"k": "不催不逼", "v": "禁用「限时」「仅剩」「抢」「最后一天」。改用「不着急」「您先了解」「需要了招呼一声」。"},
        {"k": "安全牌最重", "v": "用气安全 / 洗澡安全 / 清洗技巧这类内容，回复率和转发率远高于促销，还免费建立专业形象。"},
        {"k": "真人落款", "v": "结尾必须署销售真名（——欧乐家 小李），不要署公司名。客户认人不认品牌。"},
        {"k": "本地方言", "v": "轻量使用：安逸、要得、莫、孃孃、娃儿些、巷子头。每条 1-2 个即可，多了显做作。"},
        {"k": "价格铁律", "v": "燃气灶 399 / 油烟机 699 / 热水器 599，四免、先装后付、8年质保、旧机抵扣。数字一个都不能错。"},
        {"k": "发完不追", "v": "客户没回不要补第二条。下周五自然还有一条，节奏比单次转化重要。"},
        {"k": "回复优先", "v": "有客户回复，销售必须 30 分钟内响应。周五 10:00-12:00 与节假日 09:30-11:00 是必须在线的时段。"},
    ],
    "forbidden": ["亲", "小哥哥/小姐姐", "yyds/绝绝子/家人们", "限时秒杀 / 仅剩X席", "全网最低 / 史上最便宜", "夺命连环问（在吗？在吗？）", "长语音（客户不方便听）", "大段无换行文字"],
}

out = {
    "meta": {
        "brand": "重庆欧乐家厨电",
        "owner": "郑涛",
        "audience": "50-60岁为主的中老年家庭客户",
        "team_size": 4,
        "cadence": "三条线职责清晰、互不重合：① 周五主推——每周五 10:00 发送，但仅在「不与节气/节假日冲突」的周五发送；内容为日常关怀/安装效果/活动优惠的固定轮换，绝不含任何节气或节日名称；② 节气关怀——24 节气一律在节气当天 09:30 发送，顺时关怀、绝不提前延后；③ 节假日问候——中国所有节假日（含传统节日/法定/现代节日）一律在节日当天 09:30 发送，绝不提前、绝不延后。若某周五恰逢节气或节假日，该周五主推自动让位，当天只发节气/节假日内容，绝不双发、绝不合并。",
        "range": f"{items[0]['date']} ~ {items[-1]['date']}",
        "total": len(items),
        "generated_at": date.today().isoformat(),
        "products": [
            {"n": "一级能效猛火燃气灶", "p": 399, "sell": "钢化玻璃面板 · 鸳鸯猛火 · 5.2kW · 熄火+童锁双保护 · 全铜火盖"},
            {"n": "大吸力智能抽油烟机", "p": 699, "sell": "高温热清洗 · 一级能效 · 大吸力 · 高油脂分离率"},
            {"n": "13升恒温智能热水器", "p": 599, "sell": "全铜水箱 · 低压启动 · 出水恒温不忽冷忽热"},
        ],
        "service": ["先安装、满意再付款", "自有安装队，非外包", "重庆主城当天下单当天上门，半天装完",
                     "四免：送货/拆旧/安装/清理台面", "核心产品 8 年质保", "旧机以旧换新抵扣"],
    },
    "cats": CATS,
    "guide": GUIDE,
    "items": items,
}

# 读取已发布记录，烘焙进 HTML（不再依赖运行时 fetch / localStorage）
try:
    _ps = json.load(open(os.path.join(ROOT, "wechat-calendar", "data", "push_status.json"), encoding="utf-8"))
    out["pushed_ids"] = _ps.get("pushed_ids", []) or []
except Exception:
    out["pushed_ids"] = []

dst = os.path.join(ROOT, "wechat-calendar", "data", "content.json")
with open(dst, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# 生成自包含单文件日历（内联 css+data+js，便于直接预览，无需 server）
base = os.path.join(ROOT, "wechat-calendar")
_html = open(os.path.join(base, "index.html"), encoding="utf-8").read()
_css = open(os.path.join(base, "css", "style.css"), encoding="utf-8").read()
_js = open(os.path.join(base, "js", "app.js"), encoding="utf-8").read()
_html = _html.replace('<link rel="stylesheet" href="css/style.css">',
                       '<style>\n' + _css + '\n</style>')
_inject = '<script>window.__DATA__ = ' + json.dumps(out, ensure_ascii=False) + ';\n' + _js + '\n</script>'
_html = _html.replace('<script src="js/app.js"></script>', _inject)

# 注入推送通道真实配置状态（不再写死“未配置”）
_push_cfg = os.path.join(ROOT, "push", "config.json")
_push_cfg_ok = False
try:
    _pc = json.load(open(_push_cfg, encoding="utf-8"))
    _push_cfg_ok = bool((_pc.get("webhook") or "").strip())
except Exception:
    _push_cfg_ok = False
if _push_cfg_ok:
    _html = _html.replace('<div class="push-status" id="pushStatus">',
                          '<div class="push-status on" id="pushStatus">')
    _html = _html.replace('<span id="pushTxt">推送通道未配置</span>',
                          '<span id="pushTxt">推送通道已配置 · 自动化每日 09:30</span>')
else:
    _html = _html.replace('<span id="pushTxt">推送通道未配置</span>',
                          '<span id="pushTxt">推送通道未配置 · 请填写 push/config.json</span>')
_sp = os.path.join(base, "calendar_standalone.html")
with open(_sp, "w", encoding="utf-8") as f:
    f.write(_html)
print("✓ 自包含日历已更新:", _sp)

c = Counter(i["cat"] for i in items)
print(f"\n✓ 输出 {dst}")
print(f"  共 {len(items)} 条  |  周五主推 {sum(1 for i in items if i['kind']=='friday')} 条  |  节日加发 {sum(1 for i in items if i['kind']=='extra')} 条")
for k, v in CATS.items():
    print(f"  {v['name']}: {c[k]} 条 ({c[k]*100//len(items)}%)")
print(f"  时间跨度 {items[0]['date']} ~ {items[-1]['date']}")
