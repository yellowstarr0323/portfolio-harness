---
name: build
description: 포트폴리오 생성 단계. 기록과 디자인(또는 레퍼런스 분석)으로 A4 HTML을 쓰고 PDF로 만든다. start 스킬이 부른다.
---

# PDF 만들기 (build)

**먼저 읽는다**: `../../rules/principles.md`(특히 "우선순위", "중요한 것들").

## 입력
- 기록: `portfolio/profile.md`, `portfolio/projects/*.md`, `portfolio/sources/`
- 디자인: `portfolio/design.md`(시안을 고름) 또는 `portfolio/reference.md`(레퍼런스대로)

## 1. 내용 정하기
- 프로젝트마다 무엇을 앞에 둘지 원칙의 우선순위로 정한다: 문제 해결 → 결과·성과 → 역할·기여 → 판단 → 설명 → 기술 스택.
- 문제 해결 경험은 "문제 → 원인 → 판단 → 해결 → 결과 → 배운 점" 중 기록에 있는 것만으로 쓴다. 없는 단계를 채우지 않는다.
- 기록에 없는 수치·사실은 쓰지 않는다. `(모름)`인 값은 빼고 쓴다.
- 레퍼런스가 있으면 `reference.md`의 쪽 구성·블록 순서를 따른다. 레퍼런스 칸에 맞는 기록이 없으면 칸을 비우지 말고 뺀다.

## 2. 문장
- 본문은 문어체(…했다 / 명사형 종결). **사용자 말투(…했어, …했음, …거든요)를 그대로 옮기지 않는다.**
- 한 문장에 한 가지 사실. 주어가 누구인지 분명히(팀이 한 일과 본인이 한 일을 섞지 않는다).
- 수치는 측정 조건과 같이 쓴다. 조건이 없는 수치는 "약", "체감" 같은 말로 부풀리지 말고 기록 그대로.

## 3. HTML
- 파일: `portfolio/out/index.html`, 스타일은 같은 폴더(`style.css`), 이미지는 `portfolio/out/assets/`.
- **A4 한 장 = `<section class="sheet">` 하나.** `.sheet { width: 210mm; height: 297mm; overflow: hidden; box-sizing: border-box; }`, `@page { size: A4; margin: 0; }`. 쪽 사이 넘김은 `.sheet { page-break-after: always; }`.
- 링크는 `<a href="https://…">`(절대 주소)로 감싼다.
- 디자인은 `design.md` 또는 `reference.md`의 색·글꼴·크기·배치를 그대로 쓴다.

## 4. PDF
```bash
python3 <이 스킬 디렉터리>/scripts/make_pdf.py portfolio/out/index.html portfolio/out/portfolio.pdf
```
- `넘침: n쪽`이면 그 쪽 내용을 줄이거나 다음 쪽으로 옮기고 다시 돌린다. 글자를 8pt 아래로 줄여서 맞추지 않는다.
- `이미지 깨짐`이면 경로를 고친다.
- 통과하면 PDF 첫 쪽과 프로젝트 첫 쪽을 직접 열어(Read) 글자가 겹치거나 잘린 곳이 없는지 본다.

## 5. 끝나면
`portfolio/state.md`의 `stage: done`을 적고 start의 "끝 보고"를 한다.

## 보류: 검사 반복 (loop)
디자인 검사와 문장 검사를 반복하는 단계는 **나중에 붙인다.** 지금은 하지 않는다. 붙일 때 같이 볼 것:
- 기록에 없는 수치가 본문에 들어갔는지 대조하는 검사(지금은 위 "1. 내용 정하기" 규칙만 있다)
- 사용자 말투가 본문에 남았는지
- 링크가 실제로 열리는지
