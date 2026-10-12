---
name: start
description: 포트폴리오 하네스 진입점. 기존 포트폴리오 확인(있으면 면접관 리뷰) → 레퍼런스 확인 → 인터뷰 → 디자인 추천 → PDF 생성을 순서대로 끝까지 진행한다. "포트폴리오 만들어줘", "포트폴리오 시작", "포트폴리오 이어서 하자" 같은 요청에 사용한다. 다른 단계 스킬(interview, design, build)은 이 스킬이 부른다.
---

# 포트폴리오 만들기 (start)

**먼저 읽는다**: 이 스킬의 기본 디렉터리 기준 `../../../rules/principles.md`(제품 원칙). 읽지 못하면 작업을 시작하지 않고 "원칙 문서를 읽지 못해 멈췄어요"라고 알린다.

## 지킬 것 5가지
선택지로 묻는 곳은 선택지 질문 도구(Claude Code의 AskUserQuestion 등)가 있으면 그걸 쓰고, 없으면 글로 선택지를 보여주고 답을 받는다.

1. 사용자에게 하는 말은 **한국어 존댓말**(…해요)로 쓴다. 기술 이름·고유명사·파일 경로만 원래 표기.
2. 사용자가 주지 않은 경험·수치·사실을 만들지 않는다.
3. 사용자 말투를 포트폴리오 본문에 그대로 옮기지 않는다. 본문은 문어체로 다시 쓴다.
4. 링크나 자료를 열지 못하면 그 턴에 바로 알린다(interview "링크와 자료").
5. 단계가 끝날 때마다 `portfolio/state.md`를 갱신한다. 다음 단계로 넘어갈지 묻지 않는다.

## 흐름

```
0. 이전 기록 확인
1. 기존 포트폴리오 질문 ── 있음 → 리뷰(portfolio-reviewer) → 보고 → 선택
                         │   ├ 고쳐서 새로(디자인 유지) → design "레퍼런스 분석"(기존 PDF) → interview(기존 내용으로 채움) → build
                         │   ├ 내용만 가져오고 디자인 새로 → interview(기존 내용으로 채움) → design "디자인 추천" → build
                         │   └ 여기서 끝 → 끝 보고(리뷰만)
                         └ 없음 → 2
2. 레퍼런스 질문 ── 있음 → design "레퍼런스 분석" → interview(레퍼런스 항목 기준) → build(레퍼런스대로)
                 └ 없음 → interview(기본 항목) → design "디자인 추천" → build
3. build: HTML → PDF → 리뷰와 수정 반복(loop, 최대 3회: portfolio-reviewer 지적 → 사용자 답 → 다시 만들기, 지적 0개면 끝)
4. 끝 보고
```

## 0. 이전 기록 확인
`portfolio/state.md`가 있으면 지금 단계를 한 줄로 보여주고 선택지로 한 번만 묻는다.
- **이어서**: state.md의 `stage`부터 계속한다. `stage: existing`이고 `portfolio/review/existing-review.md`가 있으면 리뷰를 다시 하지 않고 1의 "선택"부터 묻는다.
- **백업하고 새로**: `portfolio/`를 `portfolio.bak-<YYYYMMDD-HHMM>/`로 옮기고 처음부터 한다. 옮긴 경로를 알려준다.

없으면 `portfolio/`를 만들고 바로 1로 간다. 진행 방식 설명은 한 줄이면 된다.

## 1. 기존 포트폴리오 질문
선택지 한 문항: "이미 만들어 둔 포트폴리오가 있나요?"
- **없어요**: 2로 간다.
- **있어요**: "PDF 파일 경로나 웹 주소(Notion·개인 사이트 등)를 보내 주세요"라고 받는다. PDF가 아닌 파일(HTML·이미지·docx 등)이면 "PDF로 내보내서 보내 주세요"라고 다시 부탁한다.

### 받기
- PDF 파일: `portfolio/existing/portfolio.pdf`로 복사한다.
- URL: `python3 <이 스킬 디렉터리>/scripts/url_to_pdf.py <URL> portfolio/existing/portfolio.pdf`
  - `글이 거의 없다`·`PDF 출력 실패`면 그 턴에 알린다: "`<주소>`는 <이유>로 열리지 않아 읽지 못했어요. 공개 설정을 확인하시거나 PDF로 내보내서 보내 주세요." 열지 못한 포트폴리오를 리뷰하지 않는다.
  - `공개되어 있지 않다`(Notion)면: "Notion 페이지가 비공개라 읽지 못했어요. 오른쪽 위 공유 → 웹에 게시를 켜고 다시 보내 주시거나, PDF로 내보내서 보내 주세요."
  - Notion 앱 주소(notion.so·app.notion.com)는 스크립트가 알아서 공개 주소(notion.site)로 바꿔 인쇄한다. 사용자에게 주소를 바꿔 달라고 하지 않는다.
- 받은 PDF의 모든 쪽을 직접 열어(Read, 10쪽이 넘으면 나눠서) 포트폴리오가 맞는지 본다(로그인 안내·다른 문서면 위처럼 알린다).
- 글을 뽑아 둔다: `pdftotext -layout portfolio/existing/portfolio.pdf portfolio/sources/existing-portfolio.md` 후 첫 줄에 `출처: <받은 경로나 URL>`을 넣는다.

### 리뷰
build "리뷰와 수정 반복"의 1~2와 같은 방식이다.
1. `portfolio-reviewer` 서브에이전트를 띄운다. 프롬프트에는 **`portfolio/existing/portfolio.pdf`의 절대 경로만** 넣는다. 사용자가 한 말, 기대, 이 PDF가 기존 포트폴리오라는 사실을 넘기지 않는다. 결과를 `portfolio/review/existing-review.md`에 그대로 저장한다.
2. 지적이 인용한 문장이 PDF에 실제로 있는지 `pdftotext`로 확인한다. 없는 인용의 지적은 버린다.

### 보고
존댓말로 짧게:
- 총점(/30)과 한 줄 판단, 30초 첫인상
- 기준별 점수 한 줄씩(6개)
- 지적 전부(효과가 큰 순서). `[수정]`은 "바로 고칠 수 있는 것", `[질문]`은 "확인이 필요한 것"으로 나눠 보여준다. 내부 표기(`[수정]`·`[질문]`)는 그대로 쓰지 않는다.
- 면접에서 물어볼 질문

### 선택
선택지 한 문항: "이 리뷰를 바탕으로 어떻게 할까요?"
- **고쳐서 새로 만들기(디자인 유지)**: `state.md`에 `reference: existing`. design의 "레퍼런스 분석"을 `portfolio/existing/portfolio.pdf`로 하고(`reference.md`), 인터뷰로 간다.
- **내용만 가져오고 디자인 새로**: 인터뷰로 간다. 디자인은 인터뷰 뒤 추천한다.
- **여기서 끝**: `stage: existing` 그대로 두고 4의 "리뷰만 했을 때" 끝 보고를 한다(`done`을 적지 않는다).

두 "새로" 경로 모두 레퍼런스 질문(2)은 하지 않는다. 인터뷰는 interview의 "기존 포트폴리오에서 가져오기"를 따른다.

## 2. 레퍼런스 질문
선택지 한 문항: "참고하고 싶은 포트폴리오 레퍼런스가 있나요?"
- **있어요**: "파일 경로(PDF·이미지·HTML)나 URL을 보내 주세요"라고 받고, design 스킬의 "레퍼런스 분석"을 한다. 결과는 `portfolio/reference.md`.
- **없어요**: interview 스킬로 간다. 디자인은 인터뷰가 끝난 뒤 내용을 보고 추천한다.

## 상태 파일 `portfolio/state.md`

```markdown
- stage: existing | reference | interview | design | build | done
- existing: 없음 | <경로나 URL> (리뷰: portfolio/review/existing-review.md)
- reference: 없음 | existing | <경로나 URL>
- interview: profile | project-list | project-detail | follow-up | done
- loop: 0/3 | 1/3 | 2/3 | 3/3 | done
- design: <고른 시안 이름 또는 "레퍼런스">
- updated: YYYY-MM-DD HH:MM
```

이어서 할 때는 이 파일만 보고 판단한다. 파일이 있다는 것만으로 단계가 끝났다고 보지 않는다.

## 4. 끝 보고
- PDF 경로와 쪽수
- 프로젝트별로 들어간 내용 한 줄씩
- 리뷰: 회차별 총점 변화, 마지막 한 줄 판단, 남은 지적, 면접에서 물어볼 질문
- 못 읽은 링크·자료, 사용자가 답하지 않아 비운 항목
- 수정하는 법: "고칠 내용을 말씀해 주시면 반영해서 다시 만들게요"
- 기존 포트폴리오에서 시작했으면: 기존 리뷰 총점 → 새 PDF 마지막 총점

### 리뷰만 했을 때(1에서 "여기서 끝")
- 리뷰 결과 경로(`portfolio/review/existing-review.md`)
- "나중에 이 리뷰로 고쳐서 새로 만들고 싶으면 '포트폴리오 이어서 하자'라고 말씀해 주세요" — 이어서 하면 1의 "선택"부터 다시 묻는다.

## 사용자에게 쓰는 말
내부 이름은 그대로 말하지 않는다: `state.md`·`reference.md`·`existing-review.md` → "진행 기록", "레퍼런스 분석 결과", "기존 포트폴리오 리뷰" / interview·design·build → "인터뷰", "디자인 고르기", "PDF 만들기".
