#!/usr/bin/env python3
"""웹에 올린 기존 포트폴리오(Notion·개인 사이트 등) URL → PDF. 리뷰어(portfolio-reviewer)는 PDF만 읽는다.

사용법: url_to_pdf.py <http(s) URL> <출력.pdf>

- headless Chrome으로 그 주소를 그대로 인쇄한다(JS 렌더링을 기다린다).
- Notion 앱 주소(notion.so·app.notion.com)는 headless에서 중간 안내 페이지의 로딩 스피너에 멈춘다(10-12 확인).
  그래서 Notion 공개 페이지 API(getPublicPageData)로 공개 여부를 보고, 공개면 Notion이 알려주는
  `<워크스페이스>.notion.site` 주소로 바꿔 인쇄한다. 비공개면 인쇄하지 않고 실패한다.
  이 API는 같은 요청에도 MemcachedCrossCellError(500)를 섞어 돌려주므로 두 호스트를 번갈아 몇 번 다시 묻는다.
- 출력 PDF에서 글자를 뽑아 너무 적으면 실패로 본다: 로그인 화면·비공개·빈 페이지·렌더링 실패일 수 있다.
  이때 PDF를 지운다(열지 못한 포트폴리오를 리뷰하지 않도록).
- 성공해도 내용이 실제 포트폴리오인지는 모델이 PDF를 열어 확인한다(로그인 안내문이 길면 통과할 수 있다).
종료 코드: 성공 0, 실패 1, 실행 불가 2.
"""
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "build" / "scripts"))
from make_pdf import chrome, pdf_pages  # noqa: E402

MIN_CHARS = 200   # 이보다 글이 적으면 포트폴리오를 읽었다고 보지 않는다
NOTION_APP_HOSTS = ("notion.so", "www.notion.so", "app.notion.com")
NOTION_API_HOSTS = ("app.notion.com", "www.notion.so")
NOTION_TRIES = 8


def notion_page_id(url: str) -> str | None:
    """Notion 앱 주소면 페이지 id(uuid 형식), 아니면 None."""
    u = urlparse(url)
    if u.hostname not in NOTION_APP_HOSTS:
        return None
    m = re.search(r"([0-9a-f]{32})$", u.path.rstrip("/").replace("-", ""), re.I)
    if not m:
        return None
    h = m.group(1).lower()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def fetch_public_data(host: str, page_id: str) -> dict:
    req = urllib.request.Request(f"https://{host}/api/v3/getPublicPageData", method="POST",
                                 data=json.dumps({"blockId": page_id}).encode(),
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except ValueError:
            return {"isNotionError": True}
    except (OSError, ValueError):
        return {"isNotionError": True}


def resolve_notion(url: str, fetch=fetch_public_data, wait: float = 0.5) -> tuple[str | None, str]:
    """(인쇄할 주소, 알림). 비공개면 주소는 None. Notion 주소가 아니거나 API가 끝내 답하지 않으면 원래 주소."""
    page_id = notion_page_id(url)
    if not page_id:
        return url, ""
    for i in range(NOTION_TRIES):
        data = fetch(NOTION_API_HOSTS[i % len(NOTION_API_HOSTS)], page_id)
        if data.get("isNotionError"):
            time.sleep(wait)
            continue
        if data.get("requireLogin") or data.get("publicAccessRole") in (None, "none"):
            return None, "Notion 페이지가 공개되어 있지 않다(로그인 필요). 공유 → 웹에 게시를 켜야 한다"
        if site := data.get("requireInterstitial"):
            return site, f"Notion 공개 주소로 바꿔 인쇄: {site}"
        return url, ""
    return url, "Notion 공개 여부를 확인하지 못해 원래 주소로 인쇄한다"


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not re.match(r"https?://", argv[0]):
        print(__doc__.strip().splitlines()[2])
        return 2
    for tool in ("pdfinfo", "pdftotext"):
        if not shutil.which(tool):
            print(f"{tool}가 없다 (Ubuntu: sudo apt install poppler-utils, macOS: brew install poppler)")
            return 2
    url, out = argv[0], Path(argv[1]).resolve()
    target, note = resolve_notion(url)
    if note:
        print(note)
    if target is None:
        print("실패: PDF를 만들지 않았다")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    try:
        chrome(["--no-pdf-header-footer", f"--print-to-pdf={out}", target])
    except subprocess.TimeoutExpired:
        out.unlink(missing_ok=True)
        print(f"PDF 출력 실패: {target} — 페이지 로딩이 끝나지 않았다(120초). 공개 설정을 확인하거나 PDF로 내보내 받는다")
        return 1
    if not out.exists():
        print(f"PDF 출력 실패: {target}")
        return 1
    text = subprocess.run(["pdftotext", "-layout", str(out), "-"], capture_output=True, text=True).stdout
    chars = len(re.sub(r"\s", "", text))
    if chars < MIN_CHARS:
        out.unlink()
        print(f"글이 거의 없다({chars}자): 로그인 필요·비공개·빈 페이지·렌더링 실패일 수 있다. PDF를 만들지 않았다")
        return 1
    print(f"통과: {out} ({pdf_pages(out)}쪽, 글자 {chars}자)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
