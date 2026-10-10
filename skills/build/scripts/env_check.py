#!/usr/bin/env python3
"""PDF를 만드는 데 필요한 환경 점검 — 인터뷰를 다 하고 마지막 PDF 단계에서 실패하지 않게 시작할 때 돌린다.

사용법: env_check.py [--offline]

검사
- Python 3.10 이상 (스크립트가 `str | None` 같은 문법을 쓴다)
- Chrome/Chromium (export.py가 쪽 실측과 PDF 출력에 쓴다)
- poppler: pdfinfo·pdftotext(export.py 쪽수·텍스트 대조), pdftoppm(디자인 검사 쪽 이미지)
- 네트워크: 웹폰트 CDN(cdn.jsdelivr.net, fonts.googleapis.com)에 닿는지 — 안 되면 글꼴이 바뀐 PDF가 나온다.
  --offline이면 건너뛴다(회귀 테스트)
종료 코드: 모두 통과 0, 하나라도 없음 1. 출력 마지막 줄은 "환경 점검: 통과" 또는 "환경 점검: 실패 n개".
"""
import platform
import shutil
import sys
import urllib.request

CHROME = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
POPPLER = ("pdfinfo", "pdftotext", "pdftoppm")
HOSTS = ("https://cdn.jsdelivr.net/", "https://fonts.googleapis.com/")


def install_hint(what: str) -> str:
    system = platform.system()
    if what == "chrome":
        return {"Darwin": "brew install --cask google-chrome",
                "Windows": "https://www.google.com/chrome/ 에서 설치"}.get(system, "sudo apt install chromium (또는 google-chrome 설치)")
    return {"Darwin": "brew install poppler",
            "Windows": "https://github.com/oschwartz10612/poppler-windows/releases 에서 받아 bin 폴더를 PATH에 추가"}.get(system, "sudo apt install poppler-utils")


def reachable(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "portfolio-harness-env-check"})
        with urllib.request.urlopen(req, timeout=6):
            return True
    except urllib.error.HTTPError:
        return True                                   # 서버가 답했다 = 네트워크는 된다
    except Exception:                                 # noqa: BLE001 — DNS·연결·시간 초과
        return False


def main(argv: list[str]) -> int:
    fails = []
    v = sys.version_info
    if v < (3, 10):
        fails.append(f"Python {v.major}.{v.minor} — 3.10 이상이 필요하다")
    else:
        print(f"OK    Python {v.major}.{v.minor}")

    chrome = next((shutil.which(n) for n in CHROME if shutil.which(n)), None)
    if chrome:
        print(f"OK    Chrome: {chrome}")
    else:
        fails.append(f"Chrome/Chromium이 없다 — 설치: {install_hint('chrome')}")

    missing = [t for t in POPPLER if not shutil.which(t)]
    if missing:
        fails.append(f"poppler({', '.join(missing)})가 없다 — 설치: {install_hint('poppler')}")
    else:
        print("OK    poppler: " + ", ".join(POPPLER))

    if "--offline" in argv:
        print("SKIP  네트워크 (--offline)")
    else:
        down = [h for h in HOSTS if not reachable(h)]
        if down:
            fails.append(f"웹폰트 서버에 닿지 않는다({', '.join(down)}) — 인터넷 연결을 확인한다. 이대로면 글꼴이 바뀐 PDF가 나온다")
        else:
            print("OK    네트워크: 웹폰트 서버 연결됨")

    for f in fails:
        print(f"없음  {f}")
    print("\n환경 점검: " + ("통과" if not fails else f"실패 {len(fails)}개 — PDF를 만들기 전에 설치한다"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
