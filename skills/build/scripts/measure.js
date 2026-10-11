// make_pdf.py가 headless Chrome에서 실행하는 측정 스크립트.
// 파이썬 문자열 안에 JS를 넣으면 % 와 역슬래시 이스케이프로 깨지기 쉬워서 별도 파일로 둔다.
// 결과는 id가 __measure인 pre 요소에 JSON으로 남기고, make_pdf.py가 --dump-dom으로 읽는다.
(async () => {
  try { await document.fonts.ready; } catch (e) {}
  await Promise.all([...document.images].map(img => img.complete ? null :
    new Promise(r => { img.onload = img.onerror = r; })));
  const sheets = [...document.querySelectorAll('.sheet')].map((s, i) => ({
    index: i + 1,
    overflow: s.scrollHeight - s.clientHeight > 1 || s.scrollWidth - s.clientWidth > 1,
    extra: Math.max(0, s.scrollHeight - s.clientHeight),
  }));
  const brokenImages = [...document.images]
    .filter(img => img.naturalWidth === 0 && getComputedStyle(img).display !== 'none')
    .map(img => img.getAttribute('src') || '(src 없음)');
  const fonts = [];
  document.fonts.forEach(f => { if (f.status === 'loaded') fonts.push(f.family.replace(/"/g, '')); });
  const out = document.createElement('pre');
  out.id = '__measure';
  out.textContent = JSON.stringify({
    sheets, brokenImages, fonts,
    width: document.documentElement.scrollWidth,
    height: document.documentElement.scrollHeight,
  });
  document.body.appendChild(out);
})();
