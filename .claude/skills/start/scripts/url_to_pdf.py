#!/usr/bin/env python3
"""웹에 올린 기존 포트폴리오(Notion·개인 사이트 등) URL → PDF. 리뷰어(portfolio-reviewer)는 PDF만 읽는다.

사용법: url_to_pdf.py <http(s) URL> <출력.pdf>

- headless Chrome으로 그 주소를 그대로 인쇄한다(JS 렌더링을 기다린다).
- 출력 PDF에서 글자를 뽑아 너무 적으면 실패로 본다: 로그인 화면·비공개·빈 페이지·렌더링 실패일 수 있다.
  이때 PDF를 지운다(열지 못한 포트폴리오를 리뷰하지 않도록).
- 성공해도 내용이 실제 포트폴리오인지는 모델이 PDF를 열어 확인한다(로그인 안내문이 길면 통과할 수 있다).
종료 코드: 성공 0, 실패 1, 실행 불가 2.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "build" / "scripts"))
from make_pdf import chrome, pdf_pages  # noqa: E402

MIN_CHARS = 200   # 이보다 글이 적으면 포트폴리오를 읽었다고 보지 않는다


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not re.match(r"https?://", argv[0]):
        print(__doc__.strip().splitlines()[2])
        return 2
    for tool in ("pdfinfo", "pdftotext"):
        if not shutil.which(tool):
            print(f"{tool}가 없다 (Ubuntu: sudo apt install poppler-utils, macOS: brew install poppler)")
            return 2
    url, out = argv[0], Path(argv[1]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    chrome(["--no-pdf-header-footer", f"--print-to-pdf={out}", url])
    if not out.exists():
        print(f"PDF 출력 실패: {url}")
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
