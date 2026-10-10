---
name: audit
description: 포트폴리오 서술 감사. 완성된 out/index.html의 문장을 facts 원문(심층 모드에서는 sources 원본까지)과 대조해 인과 날조·측정 축 혼합·작업 압축·수치 오배치·조건 누락·역할 부풀리기·회고 변형을 찾고, 승인된 수정만 반영한다. "감사해줘", "포트폴리오 검증", "과장된 거 없는지 봐줘", build 직후나 제출 전에 사용.
---

# 서술 감사 (audit)

> **먼저 읽는다** — 이 스킬을 불러오면 표시되는 기본 디렉터리(`Base directory for this skill`) 기준으로 `../../rules/principles.md`(제품 원칙)와 `../../rules/user-decisions.md`(사용자 결정 원본)를 읽는다. 이 문서의 규칙이 그 둘과 다르면 그 둘이 맞다. 같은 세션에서 이미 읽었으면 다시 읽지 않는다. **둘 중 하나라도 읽지 못하면(파일 없음·읽기 실패) 이 스킬의 작업을 시작하지 않는다** — 어떤 파일을 어느 경로로 찾았는지와 "원칙 문서를 읽지 못해 멈췄다"를 첫 줄에 알리고 끝낸다. 원칙 없이 기억이나 이 문서만으로 대신 진행하지 않는다.
>
> **한국어로 말한다** — 사용자에게 하는 모든 말(질문·선택지·중간 안내·끝 보고)은 한국어로 쓴다(원칙 → Target Users). 스크립트 출력·에이전트 보고·영어 자료를 옮길 때도 한국어로 풀어 쓴다. 기술 이름·코드·파일 경로·고유명사만 원래 표기. 사용자가 다른 언어를 요청했을 때만 바꾼다. 격리 실행(개인 설정 없음)에서 끝 보고가 영어로 나온 적이 있다(10-10).

> 사용자에게 말할 때는 `start` 스킬의 "사용자에게 쓰는 말" 표를 따른다. facts·outline·슬롯 같은 내부 이름을 채팅에 그대로 쓰지 않는다.

`check_numbers.py`는 **facts에 없는 수치**를 잡는다. 감사는 수치는 맞는데 **문장이 근거보다 더 말하는 경우**를 잡는다.
판정은 맥락 없는 `auditor` 에이전트가 한다. 문장을 쓴 쪽(build)이 자기 문장을 검사하면 같은 맹점을 공유하기 때문이다.

결과물: `portfolio/audit/pairs.md`(대조표), `portfolio/audit/report-<YYYYMMDD>.md`(감사 결과)

`<S>`는 이 스킬의 `scripts/`, `<B>`는 build 스킬의 `scripts/` 경로다.

## 0. 사전 확인
- `portfolio/out/index.html`과 `portfolio/facts/`가 있어야 한다. 없으면 `build`를 먼저 하라고 안내한다.
- 모드: **start 흐름에서 불렀으면 묻지 않고 기본 모드**로 한다(start의 멈춤 지점에 모드 질문이 없다). audit를 단독으로 불렀을 때만 묻는다 (`AskUserQuestion`):
  - **기본**: 포트폴리오 ↔ facts
  - **심층**: 기본 + facts ↔ sources 원본. `doc:` 출처가 많거나 제출 직전이면 추천한다. 시간이 더 걸린다.

## 1. 기계 검사

```bash
mkdir -p portfolio/audit
python3 <B>/check_numbers.py portfolio/out/index.html portfolio/facts
python3 <S>/pair_blocks.py portfolio/out/index.html portfolio/facts > portfolio/audit/pairs.md
```

- `check_numbers` 결과(MISSING/UNVERIFIED)는 그대로 최종 보고에 넣는다.
- `pairs.md`의 `BROKEN`은 data-fact가 없는 facts 섹션을 가리킨다는 뜻이다(근거가 쉼표로 여럿이면 없는 것만 표시된다). facts의 제목이 바뀌었거나 build가 잘못 단 것이다. 판정 전에 고친다. 고칠 수 없으면 해당 블록을 `UNSOURCED`로 넘긴다.
- `[헤드라인]` PAIR는 build가 여러 facts를 압축한 문장이다. auditor가 따로 보도록 그대로 둔다.
- `UNATTRIBUTED`는 근거 표시 없이 쓴 문장이다. 장식 문구면 무시하고, 사실 서술이면 auditor가 판정하게 둔다.

## 2. auditor 에이전트 실행

`Agent` 도구로 `auditor` 에이전트(플러그인 등록명 `portfolio-harness:auditor`)를 실행한다.
프롬프트에는 **파일 경로와 모드만** 넣는다. 지금까지의 대화, build할 때의 의도, "이건 괜찮을 것" 같은 사전 판단을 넣지 않는다.

```
모드: 기본 | 심층
pairs.md: <절대경로>/portfolio/audit/pairs.md
facts: <절대경로>/portfolio/facts/
sources: <절대경로>/portfolio/sources/   (심층 모드일 때만)
```

블록이 40개를 넘으면 프로젝트(facts 파일) 단위로 나눠 에이전트를 여러 개 실행해도 된다. 이때 같은 pairs.md를 주고 담당 파일을 지정한다.

## 3. 결과 검토와 보고

1. 에이전트 결과를 그대로 믿지 않는다. 각 지적의 **본문 인용과 근거 인용이 실제 파일에 있는지** 확인한다. 인용이 실제 파일과 다르면 그 지적은 버리고, 몇 건을 버렸는지 보고에 적는다.
2. `report-<YYYYMMDD>.md`에 저장한다. 내용은 check_numbers 결과, 확인된 지적, 버린 지적 수.
3. **선택을 받기 전에 지적 전체를 채팅 본문에 출력한다.** 파일에만 저장하거나 한 줄 요약으로 대신하지 않는다. 사용자는 report 파일을 보지 않는다. 항목마다 아래 형식으로 쓴다.
   ```
   ① [위반·UNSOURCED] DMS 알림 섹션
      지금: "커밋 이후에만 발송되어 롤백된 트랜잭션의 알림은 나가지 않습니다."
      문제: facts에 이 내용이 없음. 블로그 원문(sources/web-velog-msa-to-monolith.md 67행)에는 있음
      제안: 원문을 facts에 추가하고 문장 유지  /  안 고르면: 문장 삭제
   ```
4. 수정 여부는 **항목별로** 사용자가 고른다. `AskUserQuestion`의 multiSelect를 쓴다.
   - 선택지 `label`은 번호만 쓰지 않고 내용이 보이게 쓴다. 예: "① 롤백 문장 — facts에 원문 추가"
   - 선택지 `description`에는 **지금 문장 → 바뀔 문장**을 그대로 넣는다. 질문 화면만 보고도 무엇이 어떻게 바뀌는지 알 수 있어야 한다.
   - 수정 불필요로 판단한 항목도 빼지 말고 "(수정 안 함 추천)"을 붙여 선택지에 남긴다.
   - 제안 수정안이 facts에 없는 내용을 새로 넣는 것이면 고를 수 없게 한다. 대신 그 항목은 "사용자 확인 필요"로 질문한다.
5. `사용자 확인 필요` 항목은 질문을 하고, 답을 받으면 **facts에 먼저 기록**(`[src: interview]`)한 뒤 문장을 고친다.
6. `SRC`(facts 기록 오류) 지적은 HTML이 아니라 **facts를 고친다.** 원본과 대조한 결과를 보여주고 승인받아 수정한 뒤, 그 facts를 쓰는 블록을 다시 검토한다.

## 4. 반영과 재검증

1. 승인된 수정을 `out/index.html`에 반영한다. 블록의 `data-fact`는 유지한다.
2. build의 검증을 다시 돌린다. 문장 길이가 바뀌면 쪽이 넘치거나, 문장을 줄인 쪽에 여백 경고가 생길 수 있다. 여백 경고는 build의 처리 규칙을 따른다.
   ```bash
   python3 <B>/check_numbers.py portfolio/out/index.html portfolio/facts
   python3 <B>/export.py portfolio/out/index.html <design.json의 format> portfolio/out/portfolio.pdf
   ```
3. 통과하면 `out/.build.json`의 `indexSha256`를 새 해시로 갱신하고 `"audit": "<report 파일명>"`을 추가한다. **고친 문장이 없어도 감사를 끝냈으면 `audit`을 적는다** — 턴 끝 전송 훅이 이 표시로 최종본을 알아본다(D-FLOW-8). 그래야 다음 build가 감사로 고친 내용을 사용자의 수동 편집으로 오인하지 않는다.
4. audit를 단독으로 불렀으면 보고 전에 `python3 <B>/upload.py portfolio/out/portfolio.pdf`를 돌리고 출력 한 줄을 보고 끝에 옮긴다(build "PDF 전송", D-FLOW-8). `start` 흐름 안이면 돌리지 않는다 — 감사 뒤 build 검증·리뷰를 다시 돌 수 있어 start가 끝에서 한 번 보낸다. 설정이 없거나 같은 PDF면 알아서 건너뛴다.
5. 감사로 고친 문장의 이유는 **report에 남는다.** 다음 build가 같은 문장을 다시 원래대로 쓰지 않게, 수정 사항 중 facts로 옮길 수 있는 것(예: 인과를 명시하지 않는다는 사실, 측정 조건)은 facts에 반영한다. 이유가 문서에 남지 않으면 며칠 뒤 같은 표현이 되돌아온다.

## 하지 않는 것
- 문체나 표현 취향은 고치지 않는다. 근거와 안 맞는 것만 본다.
- 사용자 승인 없이 HTML이나 facts를 고치지 않는다.
- 지적이 0건이어도 "완벽하다"고 하지 않는다. 결과는 "이 검사 유형 기준으로 불일치를 찾지 못했다"로 보고한다.
