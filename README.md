# portfolio-harness

개발 직군 학생을 위한 **취업용 포트폴리오 제작 도구**입니다. [Claude Code](https://claude.com/claude-code)와 Codex CLI에서 동작합니다(Codex는 아직 실제 실행 검증 전).

Claude가 인터뷰하듯 질문하면 답만 하시면 됩니다. 답한 내용과 주신 자료(GitHub, Notion, velog 등)로 A4 PDF 포트폴리오를 만들고, 채용 면접관 관점에서 검토해 같이 고쳐 나갑니다.

- **대상 직무**: 프론트엔드 · 백엔드 · DevOps · 앱 · 임베디드 · AI · 풀스택 · 게임
- **지어내지 않습니다.** 말씀하지 않은 경험·수치·기술은 넣지 않습니다. 모르는 값은 비워 둡니다.
- 정보 나열보다 **문제를 발견하고 해결한 과정**과 **결과**가 잘 보이게 구성합니다(스타트업 채용 기준).

## 만들어지는 것

- `portfolio/out/portfolio.pdf` — A4 포트폴리오 PDF
- `portfolio/out/index.html` — PDF의 원본 HTML
- `portfolio/profile.md`, `portfolio/projects/` — 인터뷰에서 정리한 기록(어디서 나온 내용인지 출처 포함)
- `portfolio/images/` — 프로젝트별 로고·화면 이미지
- `portfolio/review/` — 면접관 관점 리뷰 결과

`portfolio/`는 git에 올라가지 않습니다.

## 준비물

| 항목 | 설명 |
|---|---|
| Claude Code | 설치하고 로그인해 두세요. 예: `npm install -g @anthropic-ai/claude-code` |
| Python 3.10 이상 | PDF를 만드는 스크립트 실행 |
| Chrome 또는 Chromium | HTML을 PDF로 출력 |
| poppler (`pdfinfo`) | PDF 쪽수 확인 |

```bash
# Ubuntu
sudo apt install chromium poppler-utils     # 또는 google-chrome 설치

# macOS
brew install --cask google-chrome
brew install poppler
```

미리 챙겨 두면 좋은 것:
- **프로젝트마다 로고 1장 + 화면(또는 동작 화면) 1장 이상** — 필수입니다. 이미지 **파일**로 준비해 주세요.
- 프로젝트를 정리해 둔 링크(GitHub 저장소, Notion, velog, 블로그 글 등) — 있으면 질문이 줄어듭니다.

## 설치와 실행

```bash
git clone https://github.com/yellowstarr0323/portfolio-harness.git
cd portfolio-harness
claude
```

- 처음 실행하면 이 폴더를 신뢰할지 묻습니다. **Yes(신뢰)**를 고르세요. 하네스 설정이 이 폴더의 `.claude/`에 있어서 신뢰해야 켜집니다.
- **반드시 이 폴더 안에서 `claude`를 실행하세요.** 다른 폴더에서 실행하면 하네스가 켜지지 않고 일반 Claude로 동작합니다.
- 켜졌는지 확인: 입력창에 `/`를 치면 `start`, `interview`, `design`, `build`가 보여야 합니다.
- 업데이트: `git pull`

### Codex로 쓸 때
```bash
cd portfolio-harness
codex
```
- 처음 실행하면 이 폴더(`.codex/`)를 신뢰할지 묻습니다. 신뢰를 고르세요.
- `/hooks`를 입력해 PDF 자동 전송 훅을 검토하고 승인하세요. Codex는 훅마다 승인해야 실행하고, 훅 파일이 바뀌면 다시 승인해야 합니다.
- 켜졌는지 확인: `/skills`에 `start`, `interview`, `design`, `build`가 보여야 합니다.
- Codex 샌드박스 설정에 따라 링크 읽기·PDF 만들기가 막힐 수 있습니다(아직 확인 전). 막히면 해당 명령을 허용해 주세요.

## 사용법

입력창에 **"포트폴리오 만들어줘"**라고 말하면 시작합니다. 이후 단계는 Claude가 알아서 이어 갑니다.

### 1. 레퍼런스 질문
"참고하고 싶은 포트폴리오 레퍼런스가 있나요?"
- **있어요**: 파일(PDF·이미지·HTML) 경로나 URL을 주세요. 레퍼런스의 구성을 분석해 그 항목대로 인터뷰하고, 그 디자인대로 만듭니다.
- **없어요**: 인터뷰가 끝난 뒤 내용에 맞는 디자인을 추천해 드립니다.

### 2. 인터뷰
빈칸이 있는 양식을 드리면 채워서 보내시면 됩니다.
1. **개인 정보**: 이름, 직무 분야(8개 중 하나), 연락처, 링크, 학력, 수상·자격증, 활동. 선택 항목은 비워도 됩니다.
2. **프로젝트 목록**: 이름 | 한 줄 소개 | 팀 구성 | 기간 | 기술 스택 | 링크
3. **프로젝트 상세**: 맡은 역할과 직접 수행한 작업. 정리해 둔 글이 있으면 링크로 주셔도 됩니다. 이때 **로고와 프로젝트 화면 이미지**도 받습니다.
4. **추가 질문**: 주신 설명과 자료를 다 읽은 뒤, 이해되지 않는 부분(문제의 원인, 결과 수치, 기술을 고른 이유 등)을 묻습니다. 모르는 건 "모르겠어요"라고 하시면 비워 두고 다시 묻지 않습니다.

### 3. 디자인 고르기 (레퍼런스가 없을 때)
실제 내용으로 만든 시안 2~3개를 미리보기 이미지와 함께 보여 드립니다. 하나를 고르거나 "이 시안에 이 색으로"처럼 말씀하시면 됩니다.

### 4. PDF 만들기와 리뷰
1. A4 PDF를 만듭니다.
2. 면접관 관점의 리뷰어가 PDF만 보고 6가지 기준으로 평가합니다: 문제 해결 과정, 결과의 근거, 대안 비교, 직무 역량, 30초 안에 핵심이 보이는지, 오류·모순.
3. 리뷰 지적 중 오탈자나 배치처럼 바로 고칠 수 있는 건 알아서 고치고, 사실 확인이 필요한 건 질문으로 묻습니다. 답하시면 반영해서 다시 만듭니다. 고치고 싶지 않은 항목은 "그대로 둘게요"라고 하시면 됩니다.
4. 이 과정을 **최대 3번** 반복하고, 지적이 없으면 바로 끝납니다.

### 5. 끝 보고
PDF 경로, 리뷰 점수 변화, 남은 지적, 면접에서 나올 만한 질문을 알려 드립니다.

## 이어서 하기 · 다시 만들기 · 고치기

- **중간에 끊겼을 때**: 같은 폴더에서 `claude`를 실행하고 "포트폴리오 이어서 하자"라고 하세요. 진행 기록(`portfolio/state.md`)을 보고 이어 갑니다.
- **처음부터 다시**: "포트폴리오 만들어줘" → "백업하고 새로"를 고르세요. 기존 결과는 `portfolio.bak-<날짜시각>/`으로 옮겨집니다.
- **완성 뒤 고치기**: 고칠 내용을 말씀하시면 반영해서 다시 만듭니다.

## 자주 묻는 문제

| 증상 | 해결 |
|---|---|
| 하네스가 안 켜지고 일반적인 질문만 한다 | `portfolio-harness` 폴더 안에서 `claude`를 실행했는지, 처음 실행 때 폴더를 신뢰(Yes)했는지 확인하세요 |
| 이미지를 붙여넣었는데 다시 달라고 한다 | 대화창에 붙여넣기(Ctrl+V)한 이미지는 파일로 저장되지 않습니다. **파일을 창으로 끌어다 놓거나 경로를 적어 주세요** |
| "링크를 읽지 못했어요"라고 한다 | 비공개 저장소, 로그인이 필요한 페이지(Notion 비공개 등), 잘못된 주소일 수 있습니다. 공개로 바꾸거나 내용을 복사해 붙여넣어 주세요 |
| PDF가 안 만들어진다 | Chrome·poppler가 설치돼 있는지 확인하세요 |

## 개발자용

개발 규칙은 `DEVELOPMENT.md`, 구조 결정은 `rules/decisions.md`, 제품 원칙은 `rules/principles.md`에 있습니다.

```
.claude/
├─ skills/
│  ├─ start/       진입점 — 레퍼런스 질문, 단계 순서, 진행 기록, 끝 보고
│  ├─ interview/   인터뷰, 필수 이미지 확인(scripts/check_images.py)
│  ├─ design/      레퍼런스 분석 / 디자인 시안 추천
│  └─ build/       HTML → PDF(scripts/make_pdf.py), 리뷰·수정 반복
├─ agents/portfolio-reviewer.md   PDF만 보고 면접관 관점 평가
├─ hooks/send_on_done.py          리뷰가 끝난 최종 PDF 자동 전송(테스트 운영용)
└─ settings.json                   Claude Code 훅 설정
.agents/skills → ../.claude/skills  Codex용(심볼릭 링크, 같은 스킬)
.codex/
├─ agents/portfolio-reviewer.toml   Codex용 리뷰어(scripts/sync_codex.py가 만든다)
└─ hooks.json                       Codex 훅 설정(같은 send_on_done.py)
CLAUDE.md / AGENTS.md               진입 지시문(AGENTS.md는 sync_codex.py가 CLAUDE.md에서 만든다)
```

```bash
python3 tests/run_tests.py          # 전체 (Chrome·poppler 필요)
python3 tests/run_tests.py --fast   # make_pdf 제외
```

`upload.json`(리뷰가 끝난 PDF를 테스트 운영자의 Discord 웹훅으로 자동 전송하는 설정, `{"discord_webhook": "…"}`)은 테스트 운영자용입니다. 비밀값이라 저장소에 없고(`.gitignore`), 없으면 전송은 꺼져 있습니다. 쓰려면 이 폴더 루트에 둡니다.
