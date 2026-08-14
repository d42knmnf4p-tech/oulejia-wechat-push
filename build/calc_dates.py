# -*- coding: utf-8 -*-
from datetime import date, timedelta
from lunarcalendar import Converter, Solar, Lunar
from lunarcalendar.festival import festivals

start = date(2026, 8, 10)
end   = date(2027, 3, 8)

# 1) 所有周五
print("=== 周五清单 ===")
d = start
fridays = []
while d <= end:
    if d.weekday() == 4:
        fridays.append(d)
    d += timedelta(days=1)
for f in fridays:
    ln = Converter.Solar2Lunar(Solar(f.year, f.month, f.day))
    print(f"{f.isoformat()}  农历{ln.month}月{ln.day}")

print(f"\n共 {len(fridays)} 个周五")

# 2) 节日 & 节气
print("\n=== 节日/节气 ===")
rows = []
for y in (2026, 2027):
    for fest in festivals:
        try:
            dt = fest(y)
        except Exception:
            continue
        if dt is None: continue
        if isinstance(dt, Solar):
            dt = date(dt.year, dt.month, dt.day)
        if hasattr(dt, 'to_date'): dt = dt.to_date()
        if not isinstance(dt, date):
            try: dt = date(dt.year, dt.month, dt.day)
            except Exception: continue
        if start <= dt <= end:
            rows.append((dt, fest.__name__ if hasattr(fest,'__name__') else str(fest)))
for dt, name in sorted(set(rows)):
    print(f"{dt.isoformat()}  {name}  ({'一二三四五六日'[dt.weekday()]})")

# 3) 关键农历节日手工核验
print("\n=== 农历关键日核验 ===")
checks = [
    (2026, 7, 15, "中元"), (2026, 8, 15, "中秋"), (2026, 9, 9, "重阳"),
    (2026, 12, 8, "腊八"), (2026, 12, 23, "小年"), (2026, 12, 30, "除夕候选"),
    (2027, 1, 1, "春节"), (2027, 1, 15, "元宵"), (2027, 2, 2, "龙抬头"),
]
for ly, lm, ld, nm in checks:
    try:
        s = Converter.Lunar2Solar(Lunar(ly, lm, ld, isleap=False))
        dd = date(s.year, s.month, s.day)
        print(f"{nm}: {dd.isoformat()} ({'一二三四五六日'[dd.weekday()]})")
    except Exception as e:
        print(f"{nm}: ERR {e}")
