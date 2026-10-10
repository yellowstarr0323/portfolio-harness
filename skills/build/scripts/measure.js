// export.py가 headless Chrome에서 실행하는 측정 스크립트.
// 파이썬 문자열 안에 두면 % 와 역슬래시 이스케이프 때문에 여러 번 깨져서 별도 파일로 뺐다.
// 밑줄 두 개로 감싼 대문자 이름(MERGE_PX, MIN_PT)은 export.py가 설정값으로 바꿔 넣는 자리표시자다.
function fill(sheet) {
  const box = sheet.getBoundingClientRect();
  const cs = getComputedStyle(sheet);
  const lo = parseFloat(cs.paddingTop), hi = sheet.clientHeight - parseFloat(cs.paddingBottom);
  const sheetBg = cs.backgroundColor;
  const iv = [];
  const add = r => {
    if (r.width <= 0 || r.height <= 0) return;
    const a = Math.max(lo, r.top - box.top), b = Math.min(hi, r.bottom - box.top);
    if (b > a) iv.push([a, b]);
  };
  const tw = document.createTreeWalker(sheet, NodeFilter.SHOW_TEXT);
  while (tw.nextNode()) {
    const n = tw.currentNode;
    if (!n.data.trim()) continue;
    const rg = document.createRange();
    rg.selectNodeContents(n);
    for (const r of rg.getClientRects()) add(r);
  }
  for (const el of sheet.querySelectorAll('*')) {
    const r = el.getBoundingClientRect();
    if (r.height > (hi - lo) * 0.9) continue;          // 쪽 전체를 덮는 장식 띠·래퍼는 내용으로 치지 않는다
    const tag = el.tagName.toLowerCase();
    if (['img', 'svg', 'canvas', 'video', 'picture'].includes(tag)) { add(r); continue; }
    const s = getComputedStyle(el);
    const bg = s.backgroundColor;
    const hasBg = (bg !== sheetBg && bg !== 'transparent' && !/rgba\([^)]*,\s*0\)$/.test(bg))
                  || s.backgroundImage !== 'none';
    const bw = k => (s['border' + k + 'Style'] !== 'none' ? parseFloat(s['border' + k + 'Width']) || 0 : 0);
    // 배경이 있거나 세로선(왼쪽·오른쪽 테두리 — 인용선, 카드 막대)이 있으면 상자 전체가 보이는 내용이다.
    // 위·아래 선만 있는 요소(구분선 달린 래퍼)는 선 두께만 센다. 래퍼 위에 선 하나만 있어도 래퍼 전체를
    // 채움으로 세던 탓에 1쪽 채움이 48% → 75%로 부풀려졌다(2026-10-10).
    if (hasBg || bw('Left') > 0 || bw('Right') > 0) { add(r); continue; }
    if (bw('Top') > 0) add({ top: r.top, bottom: r.top + bw('Top'), width: r.width, height: bw('Top') });
    if (bw('Bottom') > 0) add({ top: r.bottom - bw('Bottom'), bottom: r.bottom, width: r.width, height: bw('Bottom') });
  }
  iv.sort((x, y) => x[0] - y[0]);
  const merged = [];
  for (const [a, b] of iv) {
    const last = merged[merged.length - 1];
    if (last && a - last[1] < __MERGE_PX__) last[1] = Math.max(last[1], b);
    else merged.push([a, b]);
  }
  let covered = 0, gap = { size: 0, from: lo, to: lo }, prev = lo;
  for (const [a, b] of merged) {
    covered += b - a;
    if (a - prev > gap.size) gap = { size: a - prev, from: prev, to: a };
    prev = Math.max(prev, b);
  }
  if (hi - prev > gap.size) gap = { size: hi - prev, from: prev, to: hi };
  return { content: hi - lo, covered, gap, sparseOk: sheet.hasAttribute('data-sparse-ok') };
}
function smallText() {
  const out = [];
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (tw.nextNode()) {
    const n = tw.currentNode, el = n.parentElement;
    if (!n.data.trim() || !el) continue;
    const rg = document.createRange();
    rg.selectNodeContents(n);
    if (!rg.getClientRects().length) continue;           // 숨겨진 글자
    let pt = parseFloat(getComputedStyle(el).fontSize) * 0.75;
    if (el instanceof SVGElement && el.getScreenCTM()) {   // viewBox로 확대·축소된 SVG 글자는 실제 크기로 환산
      const m = el.getScreenCTM();
      pt *= Math.hypot(m.a, m.b);
    }
    if (pt < __MIN_PT__) out.push({ pt: Math.round(pt * 10) / 10, text: n.data.trim().slice(0, 30) });
  }
  return out;
}
function typeScale(sheet) {
  // 쪽 안 보이는 글자를 실제 크기(pt)·굵기별로 모아 글자 수를 센다
  const out = {};
  const tw = document.createTreeWalker(sheet, NodeFilter.SHOW_TEXT);
  while (tw.nextNode()) {
    const n = tw.currentNode, el = n.parentElement;
    const t = n.data.replace(/\s+/g, '');
    if (!t || !el) continue;
    const rg = document.createRange();
    rg.selectNodeContents(n);
    if (!rg.getClientRects().length) continue;
    const cs = getComputedStyle(el);
    let pt = parseFloat(cs.fontSize) * 0.75;
    if (el instanceof SVGElement && el.getScreenCTM()) { const m = el.getScreenCTM(); pt *= Math.hypot(m.a, m.b); }
    const key = (Math.round(pt * 2) / 2) + 'pt/' + (parseInt(cs.fontWeight) >= 600 ? 'bold' : 'reg');
    out[key] = (out[key] || 0) + t.length;
  }
  return out;
}
function roles(sheet, idx) {
  const root = getComputedStyle(document.documentElement);
  const bodyPt = parseFloat(root.getPropertyValue('--fs-body')) || 11;
  const sectionPt = parseFloat(root.getPropertyValue('--fs-section')) || 18;
  const subtitlePt = parseFloat(root.getPropertyValue('--fs-subtitle')) || 14;
  const bigEmphasis = [];
  const isTitle = el => /^H[1-4]$/.test(el.tagName) || ['section-title', 'page-title', 'name'].includes(el.dataset.role);
  const pt = el => parseFloat(getComputedStyle(el).fontSize) * 0.75;
  const box = sheet.getBoundingClientRect();
  const out = [];
  for (const el of sheet.querySelectorAll('*')) {
    if (!el.getClientRects().length || el instanceof SVGElement) continue;
    const d = getComputedStyle(el).display;
    const ownText = [...el.childNodes].some(n => n.nodeType === 3 && n.data.trim());
    if (ownText && ['block', 'list-item', 'table-cell', 'grid', 'flex'].includes(d)) {
      const len = el.textContent.replace(/\s+/g, '').length, p = Math.round(pt(el) * 10) / 10;
      const text = el.textContent.trim().replace(/\s+/g, ' ').slice(0, 24);
      if (len >= 60 && p > bodyPt + 0.5) out.push(`sheet ${idx + 1}: ${len}자 문장이 ${p}pt로 본문(${bodyPt}pt)보다 큼 — "${text}…"`);
      if (len >= 100 && p < bodyPt - 0.5) out.push(`sheet ${idx + 1}: ${len}자 문장이 ${p}pt로 본문(${bodyPt}pt)보다 작음 — "${text}…"`);
    }
    if (ownText && !isTitle(el) && !el.closest('h1,h2,h3,h4,[data-role="section-title"],[data-role="page-title"],[data-role="name"]')
        && pt(el) >= sectionPt - 0.1) {
      out.push(`sheet ${idx + 1}: 강조가 너무 큼 — "${el.textContent.trim().replace(/\s+/g, ' ').slice(0, 24)}"이 ${Math.round(pt(el) * 10) / 10}pt (강조는 --fs-subtitle까지. 이름·프로젝트 이름·섹션 제목이면 h1~h4나 data-role="name"·"page-title"·"section-title"을 단다)`);
    }
    if (ownText && !isTitle(el) && !el.closest('h1,h2,h3,h4,[data-role="section-title"],[data-role="page-title"],[data-role="name"],[data-role="tagline"],[data-role="headline"]')
        && !el.closest('[data-role="before-after"], [data-role="measure-cond"]')
        && pt(el) >= subtitlePt - 0.1 && parseInt(getComputedStyle(el).fontWeight) >= 600
        && !bigEmphasis.some(b => b.contains(el))) {
      bigEmphasis.push(el);
    }
    if (/^H[1-4]$/.test(el.tagName) || el.dataset.role === 'section-title') {
      if (pt(el) < bodyPt) out.push(`sheet ${idx + 1}: 제목 "${el.textContent.trim().slice(0, 20)}"이 ${pt(el)}pt로 본문보다 작음`);
    }
    if (el.dataset.role === 'page-number') {
      const r = el.getBoundingClientRect();
      const right = r.left - box.left > box.width * 0.6, bottom = r.top - box.top > box.height * 0.88;
      if (!right || !bottom) out.push(`sheet ${idx + 1}: 쪽 번호 "${el.textContent.trim()}"가 오른쪽 아래가 아님`);
    } else if (ownText && /^\s*\d+\s*\/\s*\d+\s*$/.test(el.textContent) && !el.closest('[data-role="page-number"]')) {
      out.push(`sheet ${idx + 1}: 쪽 번호처럼 보이는 "${el.textContent.trim()}"에 data-role="page-number"가 없음 (쪽 번호는 오른쪽 아래에만)`);
    }
  }
  for (const b of bigEmphasis)
    out.push(`sheet ${idx + 1}: 측정된 before → after가 아닌 글이 소제목 크기로 굵게 강조됨 — "${b.textContent.trim().replace(/\s+/g, ' ').slice(0, 20)}" (크게 강조하는 건 측정 조건이 있는 before → after만, 나머지는 본문 크기 굵게)`);
  for (const im of sheet.querySelectorAll('img[data-kind="capture"]')) {
    const w = im.getBoundingClientRect().width;
    if (im.naturalWidth && w / im.naturalWidth < 0.5)
      out.push(`sheet ${idx + 1}: 화면 캡처 ${im.getAttribute('src')}가 원본의 ${Math.round(100 * w / im.naturalWidth)}%로 줄어 안의 글자를 읽기 어려움`);
  }
  return out;
}
function projectHeads() {
  // 프로젝트 이름 바로 다음에 보이는 글이 한 줄 설명인지 본다
  const problems = [], titles = [...document.querySelectorAll('[data-role="page-title"]')];
  const texts = [];
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (tw.nextNode()) {
    const n = tw.currentNode;
    if (!n.data.trim() || !n.parentElement || n.parentElement.closest('#__measure')) continue;
    const rg = document.createRange(); rg.selectNodeContents(n);
    if (rg.getClientRects().length) texts.push(n);
  }
  for (const t of titles) {
    const name = t.textContent.trim();
    // 기간 줄은 이름과 같은 줄(오른쪽)에 있을 때만 이름과 한 줄 설명 사이에 와도 된다
    const tr = t.getBoundingClientRect();
    const sameLine = el => { const r = el.getBoundingClientRect(); return r.top < tr.bottom && r.bottom > tr.top; };
    const next = texts.find(n => (t.compareDocumentPosition(n) & Node.DOCUMENT_POSITION_FOLLOWING) && !t.contains(n)
      && !(n.parentElement.closest('[data-role="project-meta"]') && sameLine(n.parentElement.closest('[data-role="project-meta"]'))));
    const summary = next && next.parentElement.closest('[data-role="project-summary"]');
    if (!summary) problems.push(`"${name}" 다음 글이 한 줄 설명이 아니라 "${next ? next.data.trim().slice(0, 30) : '(없음)'}"`);
    else if (summary.textContent.trim().length < 4) problems.push(`"${name}"의 한 줄 설명이 비어 있음`);
    const head = t.closest('[data-project]');
    if (!head) { problems.push(`"${name}" 첫머리에 data-project="<slug>"가 없음 (로고·화면을 프로젝트에 묶는 표시)`); continue; }
    const meta = head.querySelector('[data-role="project-meta"]');
    const period = /^\s*\d{4}\.\d{2}(\.\d{2})?\s*~\s*(\d{4}\.\d{2}(\.\d{2})?|운영 중|개발 중)(\s|·|$)/;
    if (!meta) problems.push(`"${name}" 첫머리에 기간 줄(data-role="project-meta")이 없음`);
    else if (!period.test(meta.textContent)) problems.push(`"${name}" 기간이 "시작 ~ 종료" 또는 "시작 ~ 운영 중/개발 중" 형식이 아님 — "${meta.textContent.trim().slice(0, 30)}"`);
    const slug = head.dataset.project, missing = (head.dataset.imageMissing || '').split(/\s+/);
    if (!head.querySelector('img[data-kind="logo"]') && !missing.includes('logo'))
      problems.push(`"${name}" 첫머리에 로고(img[data-kind="logo"])가 없음`);
    const screens = [...document.querySelectorAll(`img[data-kind="screen"][data-project="${slug}"]`)].filter(im => im.getClientRects().length);
    if (!screens.length && !missing.includes('screen'))
      problems.push(`"${name}"의 서비스 화면(img[data-kind="screen"][data-project="${slug}"])이 없음`);
  }
  // 프로젝트 블록 순서 (사용자 결정 2026-10-09)
  const ORDER = ['page-title', 'project-meta', 'project-summary', 'project-team', 'project-tech',
                 'project-features', 'project-highlights', 'project-detail', 'project-retro'];
  const REQUIRED = ['project-team', 'project-tech'];
  const NAMES = { 'project-team': '팀원', 'project-tech': '사용 기술', 'project-features': '기능 소개',
                  'project-highlights': '주요 성과', 'project-detail': '세부 설명', 'project-retro': '전체 회고',
                  'project-summary': '한 줄 소개', 'project-meta': '기간' };
  const marks = [...document.querySelectorAll(ORDER.map(r => `[data-role="${r}"]`).join(','))]
    .filter(el => !el.parentElement.closest(ORDER.map(r => `[data-role="${r}"]`).join(',')) || el.dataset.role === 'page-title');
  let cur = null;
  const flush = () => {
    if (!cur) return;
    for (const r of REQUIRED) if (!cur.seen.has(r)) problems.push(`"${cur.name}"에 ${NAMES[r]}(data-role="${r}")이 없음`);
  };
  for (const el of marks) {
    const role = el.dataset.role, idx = ORDER.indexOf(role);
    if (role === 'page-title') { flush(); cur = { name: el.textContent.trim(), last: 0, lastRole: role, seen: new Set() }; continue; }
    if (!cur) continue;
    if (idx < cur.last)
      problems.push(`"${cur.name}" 순서 어긋남 — ${NAMES[role]}가 ${NAMES[cur.lastRole] || cur.lastRole} 뒤에 나옴 (이름·기간 → 한 줄 소개 → 팀원 → 사용 기술 → 기능 소개 → 주요 성과 → 세부 설명 → 전체 회고)`);
    else { cur.last = idx; cur.lastRole = role; }
    cur.seen.add(role);
  }
  flush();
  return { count: titles.length, problems };
}
function beforeAfter(sheet, idx) {
  const out = [];
  const arrowNum = /\d[\d,.]*\s*[A-Za-z%$가-힣]*\s*(→|->)\s*[$]?\d/;
  // 1쪽 자기소개(profile 쪽의 headline 블록)는 사용자가 쓴 문장이라 그 안의 "a → b"는 강조 모양으로 바꾸지 않는다.
  // 그 안에 .ba(data-role="before-after")를 직접 쓴 경우의 모양·측정 조건 검사는 아래에서 그대로 한다.
  const intro = '.sheet[data-layout="profile"] [data-role="headline"]';
  for (const el of sheet.querySelectorAll('*')) {
    if (el instanceof SVGElement || el.closest('svg, code, pre, [data-role="before-after"], ' + intro)) continue;
    if (!el.getClientRects().length) continue;
    const own = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.data).join('');
    const whole = el.textContent;
    // 이 요소가 숫자 → 숫자를 처음 담는 가장 안쪽 요소일 때만 센다
    if (arrowNum.test(whole) && ![...el.children].some(c => arrowNum.test(c.textContent)) && own.trim())
      out.push(`sheet ${idx + 1}: before → after "${whole.trim().replace(/\s+/g, ' ').slice(0, 40)}"가 공통 모양(data-role="before-after")이 아님`);
  }
  for (const ba of sheet.querySelectorAll('[data-role="before-after"]')) {
    const t = ba.textContent.trim().replace(/\s+/g, ' ').slice(0, 30);
    if (!ba.querySelector('.before') || !ba.querySelector('.after'))
      out.push(`sheet ${idx + 1}: before → after "${t}"에 .before/.after 표시가 없음`);
    const next = ba.nextElementSibling;
    if (!next || next.dataset.role !== 'measure-cond' || !next.textContent.trim())
      out.push(`sheet ${idx + 1}: before → after "${t}" 바로 아래 측정 조건(data-role="measure-cond")이 없음`);
  }
  return out;
}
function measurePairs() {
  // 개선 전·후 이미지 짝(측정 화면·다이어그램·화면 캡처 등 종류 무관, data-pair로 묶음): 같은 쪽, 같은 크기 틀
  const fails = [], warns = [], groups = {};
  for (const im of document.querySelectorAll('img[data-kind="measure"], img[data-pair]')) {
    if (!im.getClientRects().length) continue;
    const key = im.dataset.pair || '(짝 없음)';
    (groups[key] = groups[key] || []).push(im);
    const sheet = im.closest('.sheet');
    if (!sheet || im.dataset.kind !== 'measure') continue;
    const cs = getComputedStyle(sheet);
    const contentW = sheet.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    const w = im.getBoundingClientRect().width;
    if (w > contentW * 0.52) warns.push(`측정 화면 ${im.getAttribute('src')}가 본문 폭의 ${Math.round(100 * w / contentW)}퍼센트 — 측정 화면은 절반 이하로 작게`);
  }
  for (const [key, ims] of Object.entries(groups)) {
    if (key === '(짝 없음)') continue;
    const sheets = new Set(ims.map(im => [...document.querySelectorAll('.sheet')].indexOf(im.closest('.sheet')) + 1));
    if (sheets.size > 1) fails.push(`측정 화면 짝 "${key}"가 ${[...sheets].join('쪽, ')}쪽으로 갈림 — 전·후는 항상 같은 쪽에 나란히`);
    if (ims.length < 2) warns.push(`측정 화면 짝 "${key}"에 이미지가 ${ims.length}장뿐`);
    const sizes = ims.map(im => { const r = im.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; });
    if (sizes.some(([w, h]) => Math.abs(w - sizes[0][0]) > 2 || Math.abs(h - sizes[0][1]) > 2))
      fails.push(`전·후 이미지 짝 "${key}"의 크기가 다름 (${sizes.map(([w, h]) => w + '×' + h).join(' / ')}px) — 같은 크기 틀로(.measure-pair, 비율이 다르면 --pair-ratio)`);
  }
  // data-pair 없이 "전"·"후" 캡션 이미지가 한 쪽에 같이 있으면 짝 표시를 잊은 것일 수 있다
  const side = (t, w) => new RegExp('(^|\\s)' + w + '(\\s|$|[—\\-:,)])').test(t);
  for (const [i, sheet] of [...document.querySelectorAll('.sheet')].entries()) {
    const figs = [...sheet.querySelectorAll('figure')].filter(f => { const im = f.querySelector('img'); return im && !im.dataset.pair && im.getClientRects().length; });
    const caps = figs.map(f => (f.querySelector('figcaption') || {}).textContent || '');
    if (caps.some(t => side(t, '전')) && caps.some(t => side(t, '후')))
      warns.push(`sheet ${i + 1}: 캡션이 "전"·"후"인 이미지가 data-pair 없이 있음 — 전·후 짝이면 data-pair로 묶어 같은 크기로`);
  }
  for (const box of document.querySelectorAll('[data-role="measure-pair"]')) {
    if (!box.querySelector('img[data-kind="measure"]')) continue;     // 30% 상한은 측정 화면(증빙)만
    const sheet = box.closest('.sheet');
    if (sheet && box.getBoundingClientRect().height > sheet.clientHeight * 0.3)
      warns.push(`측정 화면 묶음이 쪽 높이의 ${Math.round(100 * box.getBoundingClientRect().height / sheet.clientHeight)}퍼센트 — 30퍼센트 이하로`);
  }
  return { fails, warns };
}
function topTexts(sheet) {
  // 쪽 위쪽 10분의 1 안에서 시작하는 짧은 글. 여러 쪽에 같은 글이 있으면 머리글이다
  const box = sheet.getBoundingClientRect(), out = new Set();
  const tw = document.createTreeWalker(sheet, NodeFilter.SHOW_TEXT);
  while (tw.nextNode()) {
    const n = tw.currentNode, t = n.data.trim();
    if (!t || t.length > 60 || (t.match(/[0-9A-Za-z가-힣]/g) || []).length < 2) continue;   // 화살표 같은 기호는 머리글로 치지 않는다
    const rg = document.createRange(); rg.selectNodeContents(n);
    const r = rg.getClientRects()[0];
    if (r && r.top - box.top < box.height * 0.1) out.add(t);
  }
  return [...out];
}
function images() {
  // SVG는 벡터라 원본 픽셀 폭이 없다 — 로드 실패만 보고 흐림(해상도) 검사는 하지 않는다
  const isVector = im => /\.svgz?(?:[?#]|$)/i.test(im.currentSrc || im.src) || /^data:image\/svg\+xml/i.test(im.src);
  return [...document.images].filter(im => im.getClientRects().length).map(im => ({
    src: im.getAttribute('src'), natural: im.naturalWidth, vector: isVector(im),
    rendered: Math.round(im.getBoundingClientRect().width) }));
}
function contrastIssues() {
  // 글자색과 실제 바탕색의 대비(D-DES-1, 4.5:1). 테마는 make_theme.py가 재지만, 페이지 CSS가 띠 위 글자색이나 바탕을 덮으면
  // 글자색 = 바탕색(안 보이는 글자)이 될 수 있다(5차: 띠 위 라벨이 회색으로 남음). 바탕은 조상 중 처음 나오는 불투명 background-color.
  // 그 사이에 배경 이미지(그라디언트 포함)가 있으면 바탕을 알 수 없어 건너뛴다
  const rgba = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const v = m[1].split(/[\s,\/]+/).filter(Boolean).map(parseFloat); return [v[0], v[1], v[2], v.length > 3 ? v[3] : 1]; };
  const over = (fg, bg) => [0, 1, 2].map(i => fg[i] * fg[3] + bg[i] * (1 - fg[3]));
  const lum = c => { const [r, g, b] = c.map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const bgOf = el => {
    const layers = [];
    for (let e = el; e; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') return null;
      const c = rgba(cs.backgroundColor);
      if (c && c[3] > 0) { layers.push(c); if (c[3] >= 1) break; }
    }
    let bg = [255, 255, 255];
    for (const c of layers.reverse()) bg = over(c, bg);
    return bg;
  };
  const out = [], seen = new Set();
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (tw.nextNode()) {
    const n = tw.currentNode, el = n.parentElement;
    if (!n.data.trim() || !el || seen.has(el) || el instanceof SVGElement || el.closest('#__measure')) continue;
    seen.add(el);
    const rg = document.createRange(); rg.selectNodeContents(n);
    if (!rg.getClientRects().length) continue;
    const cs = getComputedStyle(el), fg = rgba(cs.color), bg = bgOf(el);
    if (!fg || !bg) continue;
    const a = lum(over(fg, bg)), b = lum(bg);
    const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    const pt = parseFloat(cs.fontSize) * 0.75, large = pt >= 18 || (pt >= 14 && parseInt(cs.fontWeight) >= 700);
    const sheet = el.closest('.sheet');
    if (ratio < (large ? 3 : 4.5)) out.push({ ratio: Math.round(ratio * 100) / 100, large,
      sheet: sheet ? [...document.querySelectorAll('.sheet')].indexOf(sheet) + 1 : 0, text: n.data.trim().replace(/\s+/g, ' ').slice(0, 30) });
  }
  return out;
}
window.addEventListener('load', () => document.fonts.ready.then(() => {
  const sheets = [...document.querySelectorAll('.sheet')].map((s, i) => ({
    i, scroll: s.scrollHeight, client: s.clientHeight, fill: fill(s), type: typeScale(s), roles: roles(s, i).concat(beforeAfter(s, i)), top: topTexts(s) }));
  const d = document.documentElement;
  const pre = document.createElement('pre');
  pre.id = '__measure';
  pre.textContent = JSON.stringify({ sheets, small: smallText(), images: images(), contrast: contrastIssues(), heads: projectHeads(), pairs: measurePairs(), width: d.scrollWidth, height: d.scrollHeight,
    fonts: [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family) });
  document.body.appendChild(pre);
}));
