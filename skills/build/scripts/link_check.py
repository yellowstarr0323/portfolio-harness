#!/usr/bin/env python3
"""링크 검사 — HTML·PDF에서 링크를 누르면 반드시 그 페이지로 가는지 (사용자 결정 D-DES-14).

사용법: link_check.py <index.html> [--pdf <portfolio.pdf>] [--offline]

검사 (모두 실패):
  1. 보이는 글 중 주소처럼 생긴 것(https://…, www.…, github.com/…, velog.io/…, 이메일 등)은 <a href>로 감싼다
     — 주소를 글자로만 쓰면 PDF에서 눌러도 아무 데도 안 간다
  2. <a>의 href는 https://·http://·mailto:·tel: 로 시작하는 절대 주소다. "github.com/x"처럼 쓰면
     파일 기준 상대 경로가 돼서 엉뚱한 곳으로 간다. 빈 href·"#"·javascript: 도 실패. "#아이디"는 그 아이디가 있을 때만
  3. 링크 글자가 주소면, 그 주소의 사이트와 href의 사이트가 같다(다른 페이지로 가는 링크를 막는다)
  4. --pdf: HTML의 모든 http(s)·mailto 링크가 PDF에 누를 수 있는 링크(/URI)로 들어가 있다
  5. 온라인 확인(기본, --offline이면 건너뜀): 주소에 실제로 요청해서 404·410이거나 도메인이 없으면 실패.
     401·403(로그인·봇 차단), 5xx, 시간 초과는 경고 — 사람이 직접 열어 확인한다. 네트워크가 아예 없으면 경고 한 줄
인쇄에서 숨기는 요소(data-print-hidden)는 PDF에 없으므로 제외한다.
종료 코드: 통과 0, 실패 1, 사용법 오류 2. 경고만 있으면 0.
"""
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
SKIP = {"title", "script", "style", "template", "noscript"}
TLDS = r"(?:com|net|org|io|kr|dev|app|me|co|ai|so|site|page|blog|xyz|tech|gg|ly|to|sh|cc|link)"
KNOWN_HOSTS = ("github.com", "gitlab.com", "velog.io", "notion.so", "notion.site", "linkedin.com", "tistory.com",
               "medium.com", "youtube.com", "youtu.be", "brunch.co.kr", "behance.net", "figma.com")
URLISH = re.compile(
    r"(?:https?://[^\s<>()\"']+)"                                         # 스킴이 있는 주소
    r"|(?:\bwww\.[a-z0-9-]+(?:\.[a-z0-9-]+)+[^\s<>()\"']*)"                 # www.
    rf"|(?:\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.{TLDS}/[^\s<>()\"']*)"            # 소문자 도메인 + 경로 (github.com/x)
    r"|(?:\b(?:" + "|".join(re.escape(h) for h in KNOWN_HOSTS) + r")\b(?:/[^\s<>()\"']*)?)"   # 잘 알려진 사이트
    r"|(?:\b[\w.+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+\b)"                        # 이메일
)
UA = "Mozilla/5.0 (portfolio-harness link_check)"
TIMEOUT = 10


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool, bool]] = []   # (태그, 제외 구간 시작?, 링크 시작?)
        self.skip = 0
        self.anchor: dict | None = None
        self.anchors: list[dict] = []
        self.loose: list[str] = []                      # <a> 밖의 보이는 글
        self.ids: set[str] = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag in VOID:
            return
        excluded = tag in SKIP or "data-print-hidden" in a
        is_a = tag == "a" and self.skip == 0 and not excluded
        if is_a:
            self.anchor = {"href": a.get("href"), "text": "", "line": self.getpos()[0]}
        self.stack.append((tag, excluded, is_a))
        if excluded:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        while self.stack:
            t, excluded, is_a = self.stack.pop()
            if excluded:
                self.skip -= 1
            if is_a and self.anchor is not None:
                self.anchors.append(self.anchor)
                self.anchor = None
            if t == tag:
                break

    def handle_data(self, data):
        if self.skip:
            return
        if self.anchor is not None:
            self.anchor["text"] += data
        elif data.strip():
            self.loose.append(data)


def host_of(url: str) -> str:
    u = url if re.match(r"^[a-z]+:", url, re.I) else "https://" + url
    if u.lower().startswith("mailto:"):
        return u.split(":", 1)[1].split("@")[-1].lower()
    h = (urllib.parse.urlsplit(u).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def pdf_uris(pdf: Path) -> set[str]:
    raw = pdf.read_bytes()
    out = set()
    for m in re.finditer(rb"/URI\s*(\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f\s]*>)", raw):
        s = m.group(1)
        if s.startswith(b"("):
            body = re.sub(rb"\\(.)", rb"\1", s[1:-1])
        else:
            body = bytes.fromhex(re.sub(rb"\s", b"", s[1:-1]).decode())
        out.add(body.decode("utf-8", errors="replace"))
    return out


def norm(url: str) -> str:
    """비교용: 스킴·호스트 소문자, 퍼센트 인코딩 통일, 끝 / 무시."""
    try:
        p = urllib.parse.urlsplit(url)
        path = urllib.parse.quote(urllib.parse.unquote(p.path), safe="/@:+-._~!$&'()*,;=")
        return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), path.rstrip("/"), p.query, p.fragment))
    except ValueError:
        return url


def probe(url: str) -> tuple[str, str]:
    """('ok'|'fail'|'warn'|'offline', 설명)."""
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return "ok", str(r.status)
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (400, 403, 405, 501):
                continue                                # HEAD를 안 받는 서버가 있다 — GET으로 다시
            if e.code in (404, 410):
                return "fail", f"HTTP {e.code} — 없는 페이지"
            if e.code in (401, 403):
                return "warn", f"HTTP {e.code} — 로그인이 필요하거나 자동 요청을 막는 페이지. 직접 열어 확인한다"
            return "warn", f"HTTP {e.code}"
        except urllib.error.URLError as e:
            reason = e.reason
            if isinstance(reason, socket.gaierror):
                if reason.errno in (socket.EAI_NONAME, getattr(socket, "EAI_NODATA", -5)):
                    return "fail", "도메인이 없다(DNS 조회 실패)"
                return "offline", f"DNS 오류 {reason}"
            if isinstance(reason, ConnectionRefusedError):
                return "fail", "연결 거부 — 그 주소에 서버가 없다"
            if isinstance(reason, OSError) and getattr(reason, "errno", None) in (101, 113):   # 네트워크 없음
                return "offline", str(reason)
            return "warn", f"연결 실패 {reason}"
        except (TimeoutError, socket.timeout):
            return "warn", "시간 초과"
    return "warn", "확인 못 함"


def check(html: str, pdf: Path | None, online: bool) -> tuple[list[str], list[str], list[str]]:
    p = Links()
    p.feed(html)
    fails, warns, notes = [], [], []
    for chunk in p.loose:
        for m in URLISH.finditer(chunk):
            fails.append(f"주소가 링크가 아니다 — `{m.group(0)}` (글자로만 있으면 PDF에서 눌러도 안 간다. <a href=\"https://…\">로 감싼다)")
    hrefs = []
    for a in p.anchors:
        href, text = (a["href"] or "").strip(), " ".join(a["text"].split())
        where = f"{a['line']}번째 줄 `{text[:40] or '(글자 없음)'}`"
        if not href or href == "#" or href.lower().startswith("javascript:"):
            fails.append(f"{where}: href가 비었거나 아무 데도 안 간다 (`{href}`)")
            continue
        if href.startswith("#"):
            if href[1:] not in p.ids:
                fails.append(f"{where}: 문서 안 링크 `{href}`의 대상 id가 없다")
            continue
        if not re.match(r"^(https?://[^\s/]+|mailto:[^\s@]+@[^\s@]+\.[^\s@]+|tel:\+?[\d-]+)", href, re.I):
            fails.append(f"{where}: href `{href}`가 절대 주소가 아니다 — https:// 또는 mailto:로 시작해야 한다")
            continue
        m = URLISH.search(text)
        if m and href.lower().startswith(("http", "mailto")) and host_of(m.group(0)) != host_of(href):
            fails.append(f"{where}: 글자는 `{host_of(m.group(0))}`인데 실제 연결은 `{host_of(href)}` — 다른 곳으로 간다")
        hrefs.append(href)
    notes.append(f"링크 {len(hrefs)}개" + (f": {', '.join(sorted(set(hrefs)))[:300]}" if hrefs else ""))

    if pdf is not None and hrefs:
        uris = {norm(u) for u in pdf_uris(pdf)}
        missing = [h for h in dict.fromkeys(hrefs) if h.lower().startswith(("http", "mailto")) and norm(h) not in uris]
        for h in missing:
            fails.append(f"PDF에서 눌러도 안 열린다 — `{h}`가 PDF 링크에 없다")
        if not missing:
            notes.append(f"PDF 링크: {len(set(norm(h) for h in hrefs if h.lower().startswith(('http', 'mailto'))))}개 모두 누를 수 있음")

    if online:
        results = {}
        for h in dict.fromkeys(x for x in hrefs if x.lower().startswith("http")):
            results[h] = probe(h)
        if results and all(k == "offline" for k, _ in results.values()):
            warns.append("네트워크가 없어 링크 접속을 확인하지 못했다 — 연결된 곳에서 다시 돌린다")
        else:
            for h, (kind, why) in results.items():
                if kind == "fail":
                    fails.append(f"링크가 열리지 않는다 — `{h}`: {why}")
                elif kind in ("warn", "offline"):
                    warns.append(f"링크 확인 필요 — `{h}`: {why}")
            if results:
                notes.append(f"접속 확인: {sum(1 for k, _ in results.values() if k == 'ok')}/{len(results)}개 열림")
    return fails, warns, notes


def main(argv: list[str]) -> int:
    args = argv[1:]
    online = "--offline" not in args
    args = [a for a in args if a != "--offline"]
    pdf = None
    if "--pdf" in args:
        i = args.index("--pdf")
        if i + 1 >= len(args):
            print(__doc__.strip().splitlines()[2])
            return 2
        pdf = Path(args[i + 1])
        del args[i:i + 2]
    if len(args) != 1 or not Path(args[0]).is_file():
        print(__doc__.strip().splitlines()[2])
        return 2
    fails, warns, notes = check(Path(args[0]).read_text(encoding="utf-8"), pdf, online)
    for n in notes:
        print(n)
    for w in warns:
        print(f"경고: {w}")
    for f in fails:
        print(f"실패: {f}")
    print(f"링크 검사: {'통과' if not fails else f'실패 {len(fails)}건'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
