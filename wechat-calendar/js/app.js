/* 欧乐家 · 微信营销内容日历 */
(function () {
  'use strict';

  var DB = null;
  var STORE_K = 'olj_wx_cal_v1';
  var state = { cur: null, month: null, view: 'calendar' };
  var store = load();

  function load() {
    try { return JSON.parse(localStorage.getItem(STORE_K)) || {}; } catch (e) { return {}; }
  }
  function save() { localStorage.setItem(STORE_K, JSON.stringify(store)); }
  function rec(id) { return store[id] || (store[id] = { st: 'todo', note: '' }); }
  function statusOf(id) {
    var r = rec(id);
    if (r.st && r.st !== 'todo') return r.st;            // 手动标记优先（done/skip）
    if (DB && DB.pushed_ids && DB.pushed_ids.indexOf(id) >= 0) return 'done';  // 自动已发布
    return 'todo';
  }

  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };

  function toast(msg) {
    var t = $('#toast'); t.textContent = msg; t.classList.add('on');
    clearTimeout(t._t); t._t = setTimeout(function () { t.classList.remove('on'); }, 1900);
  }
  function pad(n) { return n < 10 ? '0' + n : '' + n; }
  function ymd(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function parse(s) { var a = s.split('-'); return new Date(+a[0], +a[1] - 1, +a[2]); }
  var WD = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

  function hex2rgba(h, a) {
    var n = parseInt(h.slice(1), 16);
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
  }
  function catVars(cat) {
    var c = DB.cats[cat];
    return 'style="--c:' + c.color + ';--cb:' + hex2rgba(c.color, .1) + '"';
  }

  /* ============ 统计 ============ */
  function renderStats() {
    var items = DB.items, today = ymd(new Date());
    var done = 0, skip = 0, past = 0;
    var byCat = {};
    items.forEach(function (it) {
      var st = statusOf(it.id);
      if (st === 'done') done++;
      if (st === 'skip') skip++;
      if (it.date <= today) past++;
      byCat[it.cat] = (byCat[it.cat] || 0) + 1;
    });
    var next = items.filter(function (it) { return it.date >= today && statusOf(it.id) === 'todo'; })[0];
    var pct = items.length ? Math.round(done / items.length * 100) : 0;
    var overdue = items.filter(function (it) { return it.date < today && statusOf(it.id) === 'todo'; }).length;

    var cards = [
      { v: items.length, l: '排期总条数', s: DB.meta.range.replace(/-/g, '.'), c: '#6366F1' },
      { v: done, l: '已发送', s: '完成率 ' + pct + '%', c: '#10B981', bar: pct },
      { v: overdue, l: '逾期未发', s: overdue ? '需要立即补发' : '进度正常', c: overdue ? '#EF4444' : '#94A3B8' },
      {
        v: next ? next.date.slice(5).replace('-', '/') : '—', l: '下一次推送',
        s: next ? WD[parse(next.date).getDay()] + ' ' + next.time + ' · ' + DB.cats[next.cat].name : '已全部完成',
        c: '#C8511B'
      },
      { v: DB.meta.team_size + ' 人', l: '执行销售团队', s: '统一话术 · 统一节奏', c: '#0EA5E9' }
    ];
    $('#stats').innerHTML = cards.map(function (c) {
      return '<div class="stat" style="--accent:' + c.c + '">' +
        '<div class="v" style="color:' + c.c + '">' + c.v + '</div>' +
        '<div class="l">' + c.l + '</div>' +
        '<div class="s">' + c.s + '</div>' +
        (c.bar != null ? '<div class="bar"><i style="width:' + c.bar + '%"></i></div>' : '') +
        '</div>';
    }).join('');
  }

  /* ============ 图例 ============ */
  function renderLegend() {
    var cnt = {};
    DB.items.forEach(function (i) { cnt[i.cat] = (cnt[i.cat] || 0) + 1; });
    $('#legend').innerHTML = Object.keys(DB.cats).map(function (k) {
      return '<span class="lg"><i style="background:' + DB.cats[k].color + '"></i>' +
        DB.cats[k].name + ' <b>' + (cnt[k] || 0) + '</b></span>';
    }).join('');
    var sel = $('#filterCat');
    Object.keys(DB.cats).forEach(function (k) {
      var o = document.createElement('option');
      o.value = k; o.textContent = DB.cats[k].name; sel.appendChild(o);
    });
  }

  /* ============ 日历 ============ */
  function renderCal() {
    var y = state.month.getFullYear(), m = state.month.getMonth();
    $('#monthLabel').textContent = y + ' 年 ' + (m + 1) + ' 月';

    var first = new Date(y, m, 1);
    var offset = (first.getDay() + 6) % 7;           // 周一为首列
    var start = new Date(y, m, 1 - offset);
    var today = ymd(new Date());
    var map = {};
    DB.items.forEach(function (it) { (map[it.date] = map[it.date] || []).push(it); });

    var html = '';
    for (var i = 0; i < 42; i++) {
      var d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
      var k = ymd(d), out = d.getMonth() !== m, fri = d.getDay() === 5;
      var cls = 'cell' + (out ? ' out' : '') + (fri && !out ? ' fri' : '') + (k === today ? ' today' : '');
      html += '<div class="' + cls + '"><div class="dn">' + d.getDate() +
        (k === today ? '<span class="lunar">今天</span>' : '') + '</div>';
      (map[k] || []).forEach(function (it) {
        var st = statusOf(it.id);
        var stTxt = st === 'done' ? '已发' : st === 'skip' ? '跳过' : '待发';
        html += '<div class="evt' + (it.kind === 'extra' ? ' is-extra' : '') + '" data-id="' + it.id + '" ' + catVars(it.cat) + '>' +
          '<div class="et">' + it.title + (it.kind === 'extra' ? '<span class="badge-extra">加发</span>' : '') + '</div>' +
          '<div class="eb"><span class="etime">' + it.time + '</span>' +
          '<span class="est ' + st + '">' + stTxt + '</span></div></div>';
      });
      html += '</div>';
    }
    $('#calGrid').innerHTML = html;
  }

  /* ============ 清单 ============ */
  function renderList() {
    var q = $('#searchBox').value.trim().toLowerCase();
    var fc = $('#filterCat').value, fs = $('#filterStatus').value;
    var rows = DB.items.filter(function (it) {
      if (fc && it.cat !== fc) return false;
      if (fs && statusOf(it.id) !== fs) return false;
      if (q && (it.title + it.hook + it.content).toLowerCase().indexOf(q) < 0) return false;
      return true;
    });
    if (!rows.length) { $('#listWrap').innerHTML = '<div class="g-card" style="text-align:center;color:var(--tx3)">没有匹配的内容</div>'; return; }

    var html = '', lastM = '';
    rows.forEach(function (it) {
      var d = parse(it.date), mk = d.getFullYear() + '年' + (d.getMonth() + 1) + '月';
      if (mk !== lastM) { html += '<div class="month-sep">' + mk + '</div>'; lastM = mk; }
      var st = statusOf(it.id);
      var stTxt = st === 'done' ? '已发送' : st === 'skip' ? '已跳过' : '待发送';
      html += '<div class="row" data-id="' + it.id + '">' +
        '<div class="rd"><div class="dd">' + d.getDate() + '</div><div class="dw">' + WD[d.getDay()] + '</div></div>' +
        '<div class="rc"><div class="rt">' + it.title + (it.kind === 'extra' ? '<span class="badge-extra">加发</span>' : '') + '</div>' +
        '<div class="rh">' + it.hook + '</div></div>' +
        '<div class="rr"><span class="cat-chip" ' + catVars(it.cat) + '>' + DB.cats[it.cat].name + '</span>' +
        '<span class="est ' + st + '" style="font-size:11px;padding:3px 8px;border-radius:5px">' + stTxt + '</span></div></div>';
    });
    $('#listWrap').innerHTML = html;
  }

  /* ============ 指南 ============ */
  function renderGuide() {
    var g = DB.guide, m = DB.meta;
    var h = '';
    h += '<div class="g-card"><h3>' + g.title + '</h3>' +
      '<p class="sub">这套规则是所有话术的底层。销售可以不背话术，但必须遵守这 ' + g.rules.length + ' 条。</p>' +
      g.rules.map(function (r) {
        return '<div class="rule"><div class="rk">' + r.k + '</div><div class="rv">' + r.v + '</div></div>';
      }).join('') + '</div>';

    h += '<div class="g-card"><h3>绝对禁用清单</h3>' +
      '<p class="sub">出现以下任意一项，这条消息就废了 —— 客户会立刻判定为「群发广告」。</p>' +
      '<div class="forbid">' + g.forbidden.map(function (f) { return '<span>' + f + '</span>'; }).join('') + '</div></div>';

    h += '<div class="g-card"><h3>四大内容板块</h3>' +
      '<p class="sub">全年配比经过设计：关系维护型内容占 66%，销售型内容仅占 16%，这是老年客群不屏蔽你的前提。</p>' +
      '<div class="cat-explain">' + Object.keys(DB.cats).map(function (k) {
        var c = DB.cats[k], n = DB.items.filter(function (i) { return i.cat === k; }).length;
        return '<div class="ce" style="border-left-color:' + c.color + '">' +
          '<div class="cen"><span style="color:' + c.color + '">' + c.name + '</span>' +
          '<span class="cec">' + n + ' 条 · ' + Math.round(n / DB.items.length * 100) + '%</span></div>' +
          '<div class="ced">' + c.desc + '</div></div>';
      }).join('') + '</div></div>';

    h += '<div class="g-card"><h3>产品与价格（铁律，不得改动）</h3>' +
      '<p class="sub">任何话术中出现的价格必须与此处逐字一致。</p>' +
      '<div class="pgrid">' + m.products.map(function (p) {
        return '<div class="pcard"><div class="pn">' + p.n + '</div>' +
          '<div class="pp">¥' + p.p + '</div>' +
          '<div class="ps">' + p.sell + '</div></div>';
      }).join('') + '</div>' +
      '<div style="margin-top:20px"><div class="block-h" style="margin-bottom:9px">服务承诺（信任闭环）</div>' +
      '<div class="svc">' + m.service.map(function (s) { return '<span>' + s + '</span>'; }).join('') + '</div></div></div>';

    h += '<div class="g-card"><h3>周五执行流程</h3><p class="sub">四个销售统一动作，10:00 准点发出。</p>' +
      ['09:30 　话术自动推送到企业微信群，销售提前打开确认',
        '09:40 　按名单准备称呼（张哥/李孃孃/王叔），需配图的先存好图',
        '10:00 　准点发出，逐个发送，不要用群发助手（会被识别）',
        '10:00-12:00　必须在线，客户回复 30 分钟内响应',
        '当天下班前　在本系统标记「已发送」并填写客户反馈备注'
      ].map(function (s, i) {
        return '<div class="rule"><div class="rk">STEP ' + (i + 1) + '</div><div class="rv">' + s + '</div></div>';
      }).join('') + '</div>';

    $('#guideWrap').innerHTML = h;
  }

  /* ============ 抽屉 ============ */
  function openDrawer(id) {
    var it = DB.items.filter(function (x) { return x.id === id; })[0];
    if (!it) return;
    state.cur = it;
    var r = rec(id), d = parse(it.date), c = DB.cats[it.cat];

    $('#dCat').textContent = c.name;
    $('#dCat').setAttribute('style', '--c:' + c.color + ';--cb:' + hex2rgba(c.color, .1));
    $('#dTitle').textContent = it.title;
    $('#dMeta').textContent = it.date + ' ' + WD[d.getDay()] + ' ' + it.time +
      ' 　·　 ' + (it.kind === 'extra' ? '节日加发（短版）' : '周五主推') + ' 　·　 ' + it.hook;

    $('#wxName').textContent = '张孃孃';
    $('#wxTime').textContent = (d.getMonth() + 1) + '月' + d.getDate() + '日 ' + it.time;
    $('#wxBubble').textContent = it.content.replace(/\{称呼\}/g, '张孃孃').replace(/\{销售名\}/g, '小李').replace(/\{小区名\}/g, '龙湖春森彼岸');
    $('#dRaw').textContent = it.content;

    if (it.asset) { $('#assetBlock').style.display = ''; $('#dAsset').textContent = '📷 ' + it.asset; }
    else { $('#assetBlock').style.display = 'none'; }

    $('#dTips').innerHTML = it.tips.map(function (t) {
      return '<li class="' + (t.indexOf('★') === 0 ? 'key' : '') + '">' + t + '</li>';
    }).join('');

    $$('.sbtn').forEach(function (b) { b.classList.toggle('on', b.dataset.st === r.st); });
    $('#dNote').value = r.note || '';

    $('#mask').classList.add('on');
    $('#drawer').classList.add('on');
  }
  function closeDrawer() {
    if (state.cur) { rec(state.cur.id).note = $('#dNote').value; save(); }
    $('#mask').classList.remove('on'); $('#drawer').classList.remove('on');
    state.cur = null; refresh();
  }

  /* ============ 导出 ============ */
  function exportTxt() {
    var lines = ['重庆欧乐家厨电 · 微信营销话术全集',
      '排期 ' + DB.meta.range + ' 　共 ' + DB.items.length + ' 条',
      '发送节奏：' + DB.meta.cadence,
      '导出时间：' + new Date().toLocaleString('zh-CN'),
      '\n发送前务必替换：{称呼} → 客户真实称呼　{销售名} → 你的名字　{小区名} → 真实小区',
      '\n' + '='.repeat(46) + '\n'];
    DB.items.forEach(function (it, i) {
      var d = parse(it.date);
      lines.push('【' + (i + 1) + '】' + it.date + ' ' + WD[d.getDay()] + ' ' + it.time +
        '　[' + DB.cats[it.cat].name + ']' + (it.kind === 'extra' ? '[节日加发]' : ''));
      lines.push('主题：' + it.title + '　（' + it.hook + '）');
      if (it.asset) lines.push('配图：' + it.asset);
      lines.push('-'.repeat(46));
      lines.push(it.content);
      lines.push('-'.repeat(46));
      lines.push('发送要点：');
      it.tips.forEach(function (t) { lines.push('  · ' + t); });
      lines.push('\n' + '='.repeat(46) + '\n');
    });
    var blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = '欧乐家_微信营销话术全集_' + DB.meta.range.replace(/-/g, '') + '.txt';
    a.click(); URL.revokeObjectURL(a.href);
    toast('已导出 ' + DB.items.length + ' 条话术');
  }

  /* ============ 推送状态 ============ */
  function checkPush() {
    fetch('data/push_status.json?t=' + Date.now()).then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (j && j.configured) {
          $('#pushStatus').classList.add('on');
          $('#pushTxt').textContent = j.last_push
            ? '企微推送已开启 · 上次 ' + j.last_push
            : '企微推送已开启 · 每周五 09:30';
        }
      }).catch(function () { });
  }

  function refresh() {
    renderStats();
    if (state.view === 'calendar') renderCal();
    if (state.view === 'list') renderList();
  }

  /* ============ 事件 ============ */
  function bind() {
    $$('.tab').forEach(function (t) {
      t.onclick = function () {
        $$('.tab').forEach(function (x) { x.classList.remove('active'); });
        t.classList.add('active');
        state.view = t.dataset.view;
        $$('.view').forEach(function (v) { v.classList.remove('active'); });
        $('#view-' + state.view).classList.add('active');
        refresh();
      };
    });
    $('#prevM').onclick = function () { state.month.setMonth(state.month.getMonth() - 1); renderCal(); };
    $('#nextM').onclick = function () { state.month.setMonth(state.month.getMonth() + 1); renderCal(); };
    $('#todayBtn').onclick = function () { state.month = new Date(); renderCal(); };

    document.addEventListener('click', function (e) {
      var evt = e.target.closest('.evt,.row');
      if (evt && evt.dataset.id) openDrawer(evt.dataset.id);
    });
    $('#mask').onclick = closeDrawer;
    $('#dClose').onclick = closeDrawer;
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeDrawer(); });

    $$('.sbtn').forEach(function (b) {
      b.onclick = function () {
        if (!state.cur) return;
        rec(state.cur.id).st = b.dataset.st; save();
        $$('.sbtn').forEach(function (x) { x.classList.toggle('on', x === b); });
        renderStats();
        toast(b.dataset.st === 'done' ? '已标记为「已发送」' : b.dataset.st === 'skip' ? '已跳过本条' : '已恢复为待发送');
      };
    });
    $('#dNote').onblur = function () { if (state.cur) { rec(state.cur.id).note = this.value; save(); } };

    $('#btnCopy').onclick = function () {
      if (!state.cur) return;
      var btn = this;
      navigator.clipboard.writeText(state.cur.content).then(function () {
        btn.textContent = '✓ 已复制'; btn.classList.add('ok');
        toast('话术已复制，记得替换称呼和落款');
        setTimeout(function () { btn.textContent = '复制话术'; btn.classList.remove('ok'); }, 2000);
      });
    };
    $('#btnExport').onclick = exportTxt;
    $('#searchBox').oninput = renderList;
    $('#filterCat').onchange = renderList;
    $('#filterStatus').onchange = renderList;
  }

  /* ============ 启动 ============ */
  function boot(j) {
    DB = j;
    var today = new Date();
    var firstPending = DB.items.filter(function (it) { return it.date >= ymd(today); })[0];
    state.month = firstPending ? parse(firstPending.date) : today;
    renderLegend(); renderGuide(); bind(); refresh(); checkPush();
  }
  if (window.__DATA__) {
    boot(window.__DATA__);
  } else {
    fetch('data/content.json?t=' + Date.now())
      .then(function (r) { return r.json(); })
      .then(boot)
      .catch(function (e) {
        document.querySelector('main').innerHTML =
          '<div class="g-card"><h3>内容库加载失败</h3><p class="sub">请通过本地服务访问（不要直接双击打开 html 文件）。</p></div>';
        console.error(e);
      });
  }
})();
