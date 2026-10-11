# portfolio-harness

개발 직군(백엔드·프론트엔드·모바일·풀스택·인프라) 학생용 Claude Code 플러그인.
인터뷰로 프로젝트 경험을 모으고, HTML/PDF 포트폴리오를 만든다. 사용자가 말하지 않은 경험·수치·기술은 지어내지 않는다.

## 필요한 환경

| 항목 | 용도 |
|---|---|
| Python 3.10 이상 | PDF 스크립트 실행 |
| Chrome 또는 Chromium | 쪽 측정과 PDF 출력 |
| poppler (`pdfinfo`) | PDF 쪽수 확인 |

```bash
# Ubuntu
sudo apt install chromium poppler-utils     # 또는 google-chrome 설치

# macOS
brew install --cask google-chrome
brew install poppler
```

## 설치

Claude Code 안에서:

```
/plugin marketplace add yellowstarr0323/portfolio-harness
/plugin install portfolio-harness@portfolio-harness
```

또는 저장소를 받아 바로 불러오기:

```bash
git clone https://github.com/yellowstarr0323/portfolio-harness.git
claude --plugin-dir <clone한 경로>
```

## 사용

1. 빈 작업 폴더에서 `claude`를 실행한다.
2. "포트폴리오 만들어줘"라고 말한다. 이어서 할 때는 "포트폴리오 이어서 하자".

흐름:
- 참고할 포트폴리오 레퍼런스가 **있으면**: 레퍼런스 분석 → 그 구성에 맞춘 인터뷰 → PDF
- **없으면**: 인터뷰 → 내용에 맞는 디자인 시안 추천·선택 → PDF
- PDF가 나오면 면접관 관점 리뷰(`agents/portfolio-reviewer.md`, PDF만 보고 6개 기준)의 지적을 사용자와 함께 고친다. 최대 3회, 지적이 없으면 바로 끝

인터뷰는 개인 정보 → 프로젝트 목록(이름·한 줄 소개·팀 구성·기간·기술 스택·링크) → 프로젝트 상세(역할·수행 작업, Notion·velog 링크 가능) → 이해되지 않는 부분 묻기(레퍼런스가 없으면 이해될 때까지, 있으면 한 번) 순서다.

결과는 작업 폴더 `portfolio/` 아래에 생긴다.

- `portfolio/out/portfolio.pdf` — 결과 PDF
- `portfolio/out/index.html` — HTML 원본
- `portfolio/profile.md`, `portfolio/projects/` — 인터뷰 기록(출처 포함)
- `portfolio/sources/` — 읽은 링크 자료 원본

## 개발자용

```bash
python3 tests/run_tests.py          # 전체 (Chrome·poppler 필요)
python3 tests/run_tests.py --fast   # 문서 구조만
```

구조 결정은 `rules/decisions.md`, 제품 원칙은 `rules/principles.md`.
`upload.json`(리뷰가 끝난 PDF를 테스트 운영자의 Discord 웹훅으로 자동 전송하는 설정, `{"discord_webhook": "…"}`)은 테스트 운영자용이다. 비밀값이라 저장소에 없고(`.gitignore`), 없으면 전송은 꺼져 있다.
E2E 테스트(처음 쓰는 사람 조건): `./scripts/test-start.sh` → 새 세션에서 테스트 → `./scripts/test-end.sh`.
