---
name: start
description: 포트폴리오 하네스 진입점. 레퍼런스 확인 → 인터뷰 → 디자인 추천 → PDF 생성을 순서대로 끝까지 진행한다. "포트폴리오 만들어줘", "포트폴리오 시작", "포트폴리오 이어서 하자" 같은 요청에 사용한다. 다른 단계 스킬(interview, design, build)은 이 스킬이 부른다.
---

# 포트폴리오 만들기 (start)

**먼저 읽는다**: 이 스킬의 기본 디렉터리 기준 `../../../rules/principles.md`(제품 원칙). 읽지 못하면 작업을 시작하지 않고 "원칙 문서를 읽지 못해 멈췄어요"라고 알린다.

## 지킬 것 5가지
1. 사용자에게 하는 말은 **한국어 존댓말**(…해요)로 쓴다. 기술 이름·고유명사·파일 경로만 원래 표기.
2. 사용자가 주지 않은 경험·수치·사실을 만들지 않는다.
3. 사용자 말투를 포트폴리오 본문에 그대로 옮기지 않는다. 본문은 문어체로 다시 쓴다.
4. 링크나 자료를 열지 못하면 그 턴에 바로 알린다(interview "링크와 자료").
5. 단계가 끝날 때마다 `portfolio/state.md`를 갱신한다. 다음 단계로 넘어갈지 묻지 않는다.

## 흐름

```
0. 이전 기록 확인
1. 레퍼런스 질문 ── 있음 → design "레퍼런스 분석" → interview(레퍼런스 항목 기준) → build(레퍼런스대로)
                 └ 없음 → interview(기본 항목) → design "디자인 추천" → build
2. build: HTML → PDF → 리뷰와 수정 반복(loop, 최대 3회: portfolio-reviewer 지적 → 사용자 답 → 다시 만들기, 지적 0개면 끝)
3. 끝 보고
```

## 0. 이전 기록 확인
`portfolio/state.md`가 있으면 지금 단계를 한 줄로 보여주고 AskUserQuestion으로 한 번만 묻는다.
- **이어서**: state.md의 `stage`부터 계속한다.
- **백업하고 새로**: `portfolio/`를 `portfolio.bak-<YYYYMMDD-HHMM>/`로 옮기고 처음부터 한다. 옮긴 경로를 알려준다.

없으면 `portfolio/`를 만들고 바로 1로 간다. 진행 방식 설명은 한 줄이면 된다.

## 1. 레퍼런스 질문
AskUserQuestion 한 문항: "참고하고 싶은 포트폴리오 레퍼런스가 있나요?"
- **있어요**: "파일 경로(PDF·이미지·HTML)나 URL을 보내 주세요"라고 받고, design 스킬의 "레퍼런스 분석"을 한다. 결과는 `portfolio/reference.md`.
- **없어요**: interview 스킬로 간다. 디자인은 인터뷰가 끝난 뒤 내용을 보고 추천한다.

## 상태 파일 `portfolio/state.md`

```markdown
- stage: reference | interview | design | build | done
- reference: 없음 | <경로나 URL>
- interview: profile | project-list | project-detail | follow-up | done
- loop: 0/3 | 1/3 | 2/3 | 3/3 | done
- design: <고른 시안 이름 또는 "레퍼런스">
- updated: YYYY-MM-DD HH:MM
```

이어서 할 때는 이 파일만 보고 판단한다. 파일이 있다는 것만으로 단계가 끝났다고 보지 않는다.

## 3. 끝 보고
- PDF 경로와 쪽수
- 프로젝트별로 들어간 내용 한 줄씩
- 리뷰: 회차별 총점 변화, 마지막 한 줄 판단, 남은 지적, 면접에서 물어볼 질문
- 못 읽은 링크·자료, 사용자가 답하지 않아 비운 항목
- 수정하는 법: "고칠 내용을 말씀해 주시면 반영해서 다시 만들게요"

## 사용자에게 쓰는 말
내부 이름은 그대로 말하지 않는다: `state.md`·`reference.md` → "진행 기록", "레퍼런스 분석 결과" / interview·design·build → "인터뷰", "디자인 고르기", "PDF 만들기".
