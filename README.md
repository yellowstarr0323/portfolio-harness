# portfolio-harness

개발 직군(백엔드·프론트엔드·모바일·풀스택·인프라) 학생용 Claude Code 플러그인.
인터뷰로 프로젝트·문제 해결·결과에 관한 사실을 모으고, 근거가 있는 내용만으로 HTML/PDF 포트폴리오를 만든다.
사용자가 말하지 않은 경험·수치·기술은 지어내지 않는다.

## 필요한 환경

시작할 때 `skills/build/scripts/env_check.py`가 아래를 검사한다. 없어도 인터뷰는 진행되고, PDF를 만들기 전까지만 설치하면 된다.

| 항목 | 용도 |
|---|---|
| Python 3.10 이상 | 하네스 스크립트 실행 |
| Chrome 또는 Chromium (`google-chrome`, `google-chrome-stable`, `chromium`, `chromium-browser` 중 하나) | 쪽 측정과 PDF 출력 |
| poppler (`pdfinfo`, `pdftotext`, `pdftoppm`) | PDF 쪽수·텍스트 대조, 쪽 이미지 |
| 네트워크 (`cdn.jsdelivr.net`, `fonts.googleapis.com`) | 웹폰트. 안 되면 글꼴이 바뀐 PDF가 나온다 |

설치 명령:

```bash
# Ubuntu
sudo apt install chromium        # 또는 google-chrome 설치
sudo apt install poppler-utils

# macOS
brew install --cask google-chrome
brew install poppler
```

직접 점검: `python3 skills/build/scripts/env_check.py`

## 설치

(a) 마켓플레이스로 설치 — Claude Code 안에서:

```
/plugin marketplace add yellowstarr0323/portfolio-harness
/plugin install portfolio-harness@portfolio-harness
```

셸에서 한 번에 설치할 수도 있다(Claude Code 2.1.275 이상):

```bash
claude plugin install portfolio-harness --marketplace yellowstarr0323/portfolio-harness
```

(b) 저장소를 받아 바로 불러오기:

```bash
git clone https://github.com/yellowstarr0323/portfolio-harness.git
claude --plugin-dir <clone한 경로>
```

## 사용

1. 빈 작업 폴더를 만들고 그 안에서 `claude`를 실행한다.
2. "포트폴리오 만들어줘"라고 말한다. 이어서 할 때는 "포트폴리오 이어서 하자".

흐름: 인터뷰 → 자료 정리 → 디자인 → PDF 만들기 → 문장 검사. 단계는 하네스가 알아서 넘긴다.

작업 폴더 안 `portfolio/` 아래에 결과가 생긴다.

- `portfolio/out/portfolio.pdf` — 결과 PDF
- `portfolio/out/index.html` — HTML 원본 (`out/` 폴더만 있으면 열린다)
- `portfolio/facts/` — 말한 내용을 출처와 함께 기록한 폴더
- `portfolio/sources/` — 받은 자료 원본과 인터뷰 기록

## 개발자용

하네스(스킬·에이전트·스크립트)를 고친 뒤 회귀 테스트를 돌린다.

```bash
python3 tests/run_tests.py          # 전체 (headless Chrome·poppler·네트워크 필요)
python3 tests/run_tests.py --fast   # export.py 제외
```

E2E 테스트(처음 쓰는 사람 조건): `./scripts/test-start.sh` → 새 세션에서 테스트 → `./scripts/test-end.sh`. 훅·플러그인 설정은 세션 시작 때 읽히므로 start·end 뒤에는 새 세션을 연다.

`upload.json`(완성 PDF를 테스트 운영자의 Discord 웹훅으로 보내는 설정)은 테스트 운영자용이다. 비밀값이라 저장소에 없고(`.gitignore`), 없으면 전송은 꺼져 있다.
