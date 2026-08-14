# -*- coding: utf-8 -*-
"""校验内容库 + 生成节气/节日话术审阅稿（V3：三条线）"""
import json, os, re
from datetime import datetime

ROOT = "/Users/wuducike/WorkBuddy/欧乐家"
db = json.load(open(os.path.join(ROOT, "wechat-calendar", "data", "content.json"), encoding="utf-8"))
items = db["items"]
WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
def wd(s):
    d = datetime.strptime(s, "%Y-%m-%d").date()
    return WD[d.weekday()]

# 校验1：中元/寒衣残留
bad_fest = [i["id"] for i in items if ("中元" in i["title"]+i["content"]) or ("寒衣" in i["title"]+i["content"])]
print("【校验1】中元/寒衣残留:", bad_fest if bad_fest else "无 ✔")

# 校验2：低情商年龄措辞
AGE = re.compile(r"咱们这个年纪|您这个年纪|不管多大年纪|上了年纪|血压经不起|这个年龄段|我们这个年龄|你这个年纪|您这把年纪|咱们这把年纪|还在世|在世")
bad_age = [(i["id"], i["date"], AGE.search(i["content"]).group(0)) for i in items for _ in [0] if AGE.search(i["content"])]
print("【校验2】低情商年龄/探问在世措辞:", bad_age if bad_age else "无 ✔")

# 校验3：节假日+节气含价格
bad_price = [(i["id"], i["date"], i["cat"]) for i in items if i["cat"] in ("festival", "solar") and any(p in i["content"] for p in ("399", "699", "599"))]
print("【校验3】节假日/节气含价格:", bad_price if bad_price else "无 ✔")

# 校验4：节气数量
solar = [i for i in items if i["cat"] == "solar"]
print("【校验4】节气条数:", len(solar), "(应为 25)")

# 校验5：周五主推 与 节气/节假日 日期零重合
extra_dates = {i["date"] for i in items if i["kind"] == "extra"}
fri_dup = [i["id"] for i in items if i["kind"] == "friday" and i["date"] in extra_dates]
print("【校验5】周五主推与节气/节假日日期重合:", fri_dup if fri_dup else "无 ✔")

# 校验6：周五主推 内容零节日/节气词（话题不重合）
OVERLAP_WORDS = ["中秋","国庆","腊八","平安夜","圣诞","元旦","小年","除夕","春节",
    "元宵","龙抬头","劳动节","端午",
    "立春","雨水","惊蛰","春分","清明","谷雨","立夏","小满","芒种","夏至","小暑","大暑",
    "立秋","处暑","白露","秋分","寒露","霜降","立冬","小雪","大雪","冬至","小寒","大寒"]
fri_topic = [(i["id"], [w for w in OVERLAP_WORDS if w in i["title"]+i["content"]])
             for i in items if i["kind"] == "friday"]
fri_topic = [x for x in fri_topic if x[1]]
print("【校验6】周五主推含节日/节气词:", fri_topic if fri_topic else "无 ✔")

# 校验7：给客户贴"老房/老旧"标签 或 常识性错误（柴火/火柴）
DEFINE = re.compile(r"老房子|老房厨房|老房|老旧厨房|老旧|柴火|火柴|放柴")
bad_define = [(i["id"], i["date"], DEFINE.search(i["title"]+i["content"]).group(0))
              for i in items for _ in [0] if DEFINE.search(i["title"]+i["content"])]
print("【校验7】给客户贴老房标签/常识错误(柴火火柴):", bad_define if bad_define else "无 ✔")

# 校验8：暗示"随叫随到上门清洁/维修"类过度承诺（卖厨电非家政）
ONSITE = re.compile(r"喊师傅|顺路帮|帮您弄|去给他清洁|灶台脏|上门清洁|随叫随到|师傅顺带|顺路帮您|顺带帮您|师傅顺带帮您")
bad_on = [(i["id"], i["date"], ONSITE.search(i["title"]+i["content"]).group(0))
          for i in items for _ in [0] if ONSITE.search(i["title"]+i["content"])]
print("【校验8】暗示随叫随到上门(过度承诺/师傅顺带):", bad_on if bad_on else "无 ✔")

# 校验9：已删除的家庭/性别/他人角色节日不得残留
DELETED_FEST = ["父亲节", "母亲节", "儿童节", "妇女节", "情人节", "七夕", "教师节", "重阳"]
bad_del = [(i["id"], i["date"], m) for i in items for m in DELETED_FEST
           if m in (i["title"] + i["content"])]
print("【校验9】已删家庭/性别节日残留:", bad_del if bad_del else "无 ✔")

# 校验10：节假日祝福仅面向客户本人，不得带入家人/他人角色
FAMILY = re.compile(r"家人|阖家|全家|陪家人|父母|孩子|子女|儿女|老伴|伴侣|娃儿|孙娃|老两口")
bad_fam = [(i["id"], i["date"], FAMILY.search(i["title"]+i["content"]).group(0))
           for i in items for _ in [0] if i["cat"] == "festival" and FAMILY.search(i["title"]+i["content"])]
print("【校验10】节假日祝福带入家人/他人角色:", bad_fam if bad_fam else "无 ✔")

# 校验11：反常识描述拦截（创作后自查 · 防回归）
# 涵盖：潮气/水汽"渗进"柜体家具（潮气不会物理渗入柜体，属编造担心）、
#       柴火/火柴（现代厨电电子点火，备火柴既过时又危险）、
#       给客户住宅下"老房/老旧"定义、以及其他已确认的常识错误表述。
COMMONSENSE_BAD = [
    "渗进橱柜", "渗进柜", "渗进柜子", "潮气渗", "水汽渗", "湿气渗",
    "渗进厨房", "渗进墙", "潮气钻进", "湿气钻进",
    "放柴", "柴火", "火柴", "备根火柴", "留块干燥处放火柴",
    "老房子", "老房厨房", "老房", "老旧厨房", "老旧",
    "灶台脏了去给他清洁", "喊师傅来弄", "顺路帮您弄", "随叫随到",
]
bad_cs = [(i["id"], i["date"], m) for i in items for m in COMMONSENSE_BAD
          if m in (i["title"] + i["content"])]
print("【校验11】反常识描述(潮气渗柜/柴火/老房标签等):", bad_cs if bad_cs else "无 ✔")

# 校验12：先入为主 / 恐吓式描述（如「您记到」「三句唠叨」「不是吓您」「出过事」）
PREACH = re.compile(r"您记到|三句唠叨|不是吓您|是真出过事|出过事|见得多，怕您疏忽|念叨句实在的|怕您疏忽|花两分钟值当|唠叨您记到")
bad_pre = [(i["id"], i["date"], PREACH.search(i["title"]+i["content"]).group(0))
           for i in items for _ in [0] if PREACH.search(i["title"]+i["content"])]
print("【校验12】先入为主/恐吓式描述(您记到/三句唠叨/不是吓您等):", bad_pre if bad_pre else "无 ✔")

# 校验13：建议客户自己动手维修/调整/危险 DIY 或 引导式"请师傅"话术
# 拦截两类：
#  (a) 气路/水路/电路连接的拆解 DIY（客户自行操作有安全/损坏风险，不教）；
#  (b) 引导式"请师傅/跟我们说"话术（用户明确要求删除，简单操作直接给 DIY 方案，不推师傅）。
DIY_BAD = ["关了水阀拆下冲冲", "换个阀、紧一紧管，清爽多了",
           "师傅顺带帮您看一眼", "自己弄不动也莫急", "顺路帮您弄",
           "自己动手拆机", "自己洗风轮", "洗风轮自己", "调调就好",
           "得请师傅", "请师傅", "跟我们说一声", "师傅顺带", "顺路帮您", "顺带帮您"]
bad_diy = [(i["id"], i["date"], m) for i in items for m in DIY_BAD
           if m in (i["title"] + i["content"])]
print("【校验13】危险DIY / 引导式'请师傅'话术:", bad_diy if bad_diy else "无 ✔")

# 校验14：装机实拍(case) 每月仅 1 次，不堆积到某一月
from collections import Counter as _Counter
_case_month = _Counter(i["date"][:7] for i in items if i["cat"] == "case" and i["kind"] == "friday")
_bad_month = [(m, c) for m, c in _case_month.items() if c != 1]
print("【校验14】装机实拍每月数量(应均为1):", _bad_month if _bad_month else "均1 ✔")

# 校验15：安装故事(case) 不得出现"免费"等增值服务包装（只讲过程，不表演）
FREE_CASE = [(i["id"], i["date"]) for i in items
             if i["cat"] == "case" and "免费" in (i["title"] + i["content"])]
print("【校验15】安装故事含'免费'增值包装:", FREE_CASE if FREE_CASE else "无 ✔")

# 校验16：客户可见文案不得出现"老年人"等年龄标签措辞
AGE_VISIBLE = re.compile(r"老年人")
bad_age2 = [(i["id"], i["date"], AGE_VISIBLE.search(i["content"]).group(0))
            for i in items for _ in [0] if AGE_VISIBLE.search(i["content"])]
print("【校验16】客户可见文案含'老年人'标签:", bad_age2 if bad_age2 else "无 ✔")

# 节气清单
solar_s = sorted(solar, key=lambda x: x["date"])
print("\n【节气加发清单】共 %d 条（当天 09:30）:" % len(solar_s))
for i in solar_s:
    print("  %s(%s) %s" % (i["date"], wd(i["date"]), i["title"]))

# 节日清单
fest = sorted([i for i in items if i["cat"] == "festival"], key=lambda x: x["date"])
print("\n【节假日加发清单】共 %d 条（当天 09:30）:" % len(fest))
for i in fest:
    print("  %s(%s) %s" % (i["date"], wd(i["date"]), i["title"]))

# 周五主推（仅非节气/非节假日周五）
fri = sorted([i for i in items if i["kind"] == "friday"], key=lambda x: x["date"])
print("\n【周五主推（与节气/节假日零重合）】共 %d 条:" % len(fri))
for i in fri:
    print("  %s(%s) %s" % (i["date"], wd(i["date"]), i["title"]))

# 生成审阅稿
L = []
L.append("# 欧乐家 · 节气 & 节假日微信话术审阅稿（V6 · 三条线 · 零重合 · 祝福仅对客户本人 · 安装故事去表演去免费 · 去老年人/请师傅引导）\n")
L.append("> **发送铁律（三条线互不重合）**：① 周五主推——每周五 10:00 发送，但**仅在不与节气/节假日冲突的周五**发送，内容绝不含任何节气或节日名称；② 节气关怀——24 节气一律在**节气当天 09:30** 发送；③ 节假日问候——中国所有节假日在**节日当天 09:30** 发送。**节气与节假日一律当天发，绝不提前、绝不延后**；若某周五恰逢节气或节假日，周五主推自动让位，当天只发节气/节假日内容，绝不双发、绝不合并。\n")
L.append("> 本次修订：① 节气线独立成线，严格按用户提供的 24 节气措辞重写；② 节假日按用户提供的通用节日措辞重写，清明/冬至并入节气线；③ 已清除低情商措辞与探问在世；④ 节气与节假日祝福均零价格；⑤ **周五主推改为中性模板池自动填充，已彻底剔除所有以节气/节日为主题的周五条目（含原「节前预告」），并与节气/节假日日期零重合**；⑥ **已彻底删除带家庭角色/性别/他人的节日（父亲节/母亲节/儿童节/妇女节/情人节/七夕/教师节/重阳），所有节假日祝福仅面向客户本人，不带任何其他人员；中秋/平安夜/除夕/春节原「家人/阖家/陪家人」表述已改写为仅对客户的关怀**。\n")
L.append("> 内容总量 %d 条（周五主推 %d + 节气加发 %d + 节假日加发 %d），活动优惠占比 %d%%。\n" % (
    len(items), sum(1 for i in items if i["kind"] == "friday"),
    len(solar), len(fest),
    sum(1 for i in items if i["cat"] == "promo") * 100 // len(items)))
L.append("\n---\n")

L.append("## A. 节气当天加发（%d 条，逐条原文）\n" % len(solar_s))
L.append("> 在节气**当天** 09:30 发送，顺时关怀，零推销。\n")
for n, i in enumerate(solar_s, 1):
    L.append("### %d. %s　`%s（%s）`\n" % (n, i["title"], i["date"], wd(i["date"])))
    L.append("```text\n" + i["content"] + "\n```\n")
L.append("\n---\n")

L.append("## B. 节假日当天加发（%d 条，逐条原文）\n" % len(fest))
L.append("> 在节日**当天** 09:30 发送，纯关心零推销。\n")
for n, i in enumerate(fest, 1):
    L.append("### %d. %s　`%s（%s）`\n" % (n, i["title"], i["date"], wd(i["date"])))
    L.append("```text\n" + i["content"] + "\n```\n")
L.append("\n---\n")

L.append("## C. 周五主推（%d 条，仅非节气/非节假日周五，与节气节假日零重合）\n" % len(fri))
L.append("> 以下均为**中性固定内容**（日常关怀/安装效果/活动优惠），不含任何节气或节日名称；所有「节气或节假日当天」的周五已自动让位，不在本表中。\n")
for n, i in enumerate(fri, 1):
    L.append("### %d. %s　`%s（%s）`\n" % (n, i["title"], i["date"], wd(i["date"])))
    L.append("```text\n" + i["content"] + "\n```\n")
L.append("\n---\n")
L.append("*请逐条核对：语气是否柔和自然、有无需删除的节日、有无仍偏硬的措辞。确认后告诉我即可。所有内容目前仅预览，未发出任何一条。*\n")

out = os.path.join(ROOT, "wechat-calendar", "节假日话术审阅稿.md")
open(out, "w", encoding="utf-8").write("\n".join(L))
print("\n✓ 审阅稿已生成:", out)
