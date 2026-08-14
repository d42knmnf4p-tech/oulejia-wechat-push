/* 日历系统自检：jsdom 真实加载页面 + app.js，断言关键渲染 */
const { JSDOM } = require('/Users/wuducike/.workbuddy/binaries/node/workspace/node_modules/jsdom');
const fs = require('fs');
const path = require('path');

const ROOT = '/Users/wuducike/WorkBuddy/欧乐家/wechat-calendar';
let pass = 0, fail = 0;
const ok = (c, m) => { c ? (pass++, console.log('  ✓ ' + m)) : (fail++, console.log('  ✗ ' + m)); };

const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const db = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/content.json'), 'utf8'));

const dom = new JSDOM(html, { runScripts: 'outside-only', url: 'http://127.0.0.1:8123/', pretendToBeVisual: true });
const { window } = dom;

// 打桩 fetch / clipboard / localStorage
const memStore = {};
window.fetch = (u) => {
  if (String(u).indexOf('content.json') >= 0)
    return Promise.resolve({ ok: true, json: () => Promise.resolve(db) });
  return Promise.resolve({ ok: false, json: () => Promise.resolve(null) });
};
Object.defineProperty(window, 'localStorage', {
  value: { getItem: k => memStore[k] || null, setItem: (k, v) => memStore[k] = v, removeItem: k => delete memStore[k] }
});
window.navigator.clipboard = { writeText: () => Promise.resolve() };

const app = fs.readFileSync(path.join(ROOT, 'js/app.js'), 'utf8');
try { window.eval(app); } catch (e) { fail++; console.log('  ✗ app.js 执行异常: ' + e.message); }

setTimeout(() => {
  const d = window.document;
  console.log('\n[内容库]');
  ok(db.items.length === 36, `内容 36 条（实际 ${db.items.length}）`);
  ok(db.items.every(i => i.content && i.tips.length && i.title), '每条都有正文/要点/标题');
  ok(db.items.every(i => /\{称呼\}/.test(i.content)), '每条都含 {称呼} 占位符');
  ok(db.items.every(i => /\{销售名\}/.test(i.content)), '每条都含 {销售名} 落款占位符');
  const promo = db.items.filter(i => i.cat === 'promo');
  ok(promo.length / db.items.length <= 0.2, `活动优惠占比 ${Math.round(promo.length / db.items.length * 100)}% ≤ 20%`);
  ok(promo.every(i => /399|699|599/.test(i.content)), '促销条目均含正确价格');
  const fest = db.items.filter(i => i.cat === 'festival');
  ok(fest.every(i => !/399|699|599/.test(i.content)), '节日祝福零价格（无推销）');
  const dates = db.items.map(i => i.date);
  ok(new Set(dates).size >= 30, '日期无异常重复');
  ok(db.items.filter(i => i.kind === 'friday').every(i => new Date(i.date + 'T00:00:00').getDay() === 5), '主推全部落在周五');
  const banned = ['亲爱的', 'yyds', '绝绝子', '秒杀', '仅剩', '最后一天', '全网最低'];
  ok(db.items.every(i => !banned.some(b => i.content.includes(b))), '无违禁营销词');

  console.log('\n[页面渲染]');
  ok(d.querySelectorAll('.stat').length === 5, `统计卡 5 张（实际 ${d.querySelectorAll('.stat').length}）`);
  ok(d.querySelectorAll('#legend .lg').length === 4, '板块图例 4 项');
  ok(d.querySelectorAll('#calGrid .cell').length === 42, `日历 42 格（实际 ${d.querySelectorAll('#calGrid .cell').length}）`);
  const evts = d.querySelectorAll('#calGrid .evt');
  ok(evts.length > 0, `当前月渲染出 ${evts.length} 条排期`);
  ok(d.querySelector('#monthLabel').textContent.includes('2026'), '月份标题正常：' + d.querySelector('#monthLabel').textContent);
  ok(d.querySelectorAll('#guideWrap .g-card').length === 5, `执行铁律 5 个模块（实际 ${d.querySelectorAll('#guideWrap .g-card').length}）`);
  ok(d.querySelectorAll('#guideWrap .rule').length >= 15, '规则条目齐全');
  ok(d.querySelector('#guideWrap').textContent.includes('399'), '指南含价格铁律');

  console.log('\n[交互]');
  const first = d.querySelector('#calGrid .evt');
  if (first) {
    first.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    ok(d.querySelector('#drawer').classList.contains('on'), '点击排期打开详情抽屉');
    ok(d.querySelector('#wxBubble').textContent.length > 20, '微信气泡预览已填充');
    ok(!d.querySelector('#wxBubble').textContent.includes('{称呼}'), '预览已替换占位符为真实称呼');
    ok(d.querySelectorAll('#dTips li').length > 0, '发送要点已渲染');
    const doneBtn = d.querySelector('.sbtn.done');
    doneBtn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    ok(doneBtn.classList.contains('on'), '可标记「已发送」');
    ok(!!memStore['olj_wx_cal_v1'], '状态已写入本地存储');
    ok(JSON.parse(memStore['olj_wx_cal_v1'])[Object.keys(JSON.parse(memStore['olj_wx_cal_v1']))[0]].st === 'done', '存储内容正确');
  } else { fail++; console.log('  ✗ 当前月无排期，交互未测'); }

  const listTab = Array.from(d.querySelectorAll('.tab')).find(t => t.dataset.view === 'list');
  listTab.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  ok(d.querySelectorAll('#listWrap .row').length === 36, `清单视图 36 行（实际 ${d.querySelectorAll('#listWrap .row').length}）`);
  ok(d.querySelectorAll('#listWrap .month-sep').length >= 7, '按月分组正常');

  console.log(`\n===== ${pass} 通过 / ${fail} 失败 =====`);
  process.exit(fail ? 1 : 0);
}, 260);
