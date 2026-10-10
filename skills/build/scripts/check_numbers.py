#!/usr/bin/env python3
"""포트폴리오 HTML에 나온 모든 수치가 facts에 근거가 있는지, 내부 기록용 말이 본문에 새지 않았는지 검사한다.

사용법: check_numbers.py <portfolio/out/index.html> <portfolio/facts>

- facts 어디에도 없는 수치          → MISSING (지어냈거나 계산한 값)
  단위가 붙은 수치는 같은 단위로 기록된 것만 근거로 본다. 기록에 "포트 80"만 있으면 본문의 "80% 개선"은 MISSING.
  기록에서 단위 없이 쓴 수치는 같은 줄에 그 단위가 있으면 인정한다("1,225 → 241ms"의 1,225ms).
  단위 표기 차이는 맞춘다(퍼센트=%, 밀리초=ms, 초=s, x·×=배, 달=개월). "2026년"은 연도로 보고 단위 없이 대조, "1개·1회"는 통과
  기록에 나열된 것을 세어 쓴 개수("DB 2개")도 기록에 그 숫자가 없으면 MISSING이다(R-EVD-1: 새로 계산한 값)
- 한글 수량어("절반", "두 배", "수십 배" …)가 기록에 같은 말로 없음 → MISSING
- 근거없음/모름/충돌 줄에만 있는 수치 → UNVERIFIED (근거 없는 값을 본문에 씀)
- 출처 메모·하네스 용어("원문", "블로그 기준", "facts", "근거없음" …) → INTERNAL
  facts에 붙은 출처 표기가 문장에 그대로 옮겨진 것이다. 독자에게는 의미가 없다. 측정 조건은 쓰되 출처는 쓰지 않는다
data-nocheck 요소(쪽 번호, 빈 이미지 슬롯 등)는 검사하지 않는다.
종료 코드: 문제가 없으면 0, 있으면 1.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from htmltext import visible_text  # noqa: E402

NUM = re.compile(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?")
# 수치 바로 뒤(공백 하나 허용)의 단위. 긴 것부터 맞춘다. '배포'·'배치'의 '배'는 단위가 아니다
UNIT = re.compile(r"\s?(%p|%|퍼센트|ms|밀리초|초|분|시간|개월|달|주|일|년|배(?![포치열경])|x(?![a-z])|×|명|개|건|회|번|줄|쪽|"
                  r"MB|GB|KB|TB|원|req/s|rps|RPS|TPS|QPS|tokens|토큰|s(?![a-z]))", re.I)
COUNT_UNITS = {"개", "회", "번", "건", "명"}
UNIT_ALIAS = {"퍼센트": "%", "밀리초": "ms", "초": "s", "x": "배", "×": "배", "달": "개월", "rps": "req/s"}
# 한글 수량어: 숫자 없이 크기를 말하는 표현. 기록에 같은 말이 있어야 쓸 수 있다
WORD_QTY = re.compile(r"절반|반으로|(?:두|세|네|다섯|여섯|일곱|여덟|아홉|열|수십|수백|수천|몇)\s?배|"
                      r"(?:수십|수백|수천|수만)\s?(?:명|개|건|ms|초|회)")
UNVERIFIED_TAG = re.compile(r"status:\s*(근거없음|모름|충돌)")
INTERNAL = re.compile(
    r"(?i)\bfacts?\b|\[src:|status:|data-fact|근거\s?없음|역할 미확인|원문|"
    r"블로그\s?기준|블로그에서|당시 블로그|위키|인터뷰에서|인터뷰 기준|사용자 확인|DB에서 얻은|원본\s?(시트|자료|데이터)|대조함|대조했")


def unit_at(text: str, end: int) -> str | None:
    u = UNIT.match(text, end)
    if not u:
        return None
    key = u.group(1)
    key = UNIT_ALIAS.get(key, UNIT_ALIAS.get(key.lower(), key))
    return key.lower() if key.isascii() else key


def quantities(text: str) -> set[tuple[str, str | None]]:
    """줄의 (수치, 단위) 쌍. 단위 없이 쓴 수치는 같은 줄에 나온 단위들과도 짝짓는다("1,225 → 241ms")."""
    found = [(m.group().replace(",", ""), unit_at(text, m.end())) for m in NUM.finditer(text)]
    units = {u for _, u in found if u}
    out = set(found)
    for n, _ in found:                         # 날짜 2026.03(.01)은 연도·월로도 쓴다("2026년 3월")
        if d := re.fullmatch(r"((?:19|20)\d\d)\.(\d\d)", n):
            out.update({(d.group(1), None), (str(int(d.group(2))), None)})
    for n, u in found:
        if u is None:
            out.update((n, x) for x in units)
    return out


def squash(t: str) -> str:
    return re.sub(r"\s+", "", t)


def main(html_path: str, facts_dir: str) -> int:
    verified: set[tuple[str, str | None]] = set()
    unverified: set[tuple[str, str | None]] = set()
    facts_text = ""
    for f in sorted(Path(facts_dir).glob("*.md")):
        for line in f.read_text(encoding="utf-8").splitlines():
            (unverified if UNVERIFIED_TAG.search(line) else verified).update(quantities(line))
            if not UNVERIFIED_TAG.search(line):
                facts_text += squash(line) + "\n"
    bare = {n for n, _ in verified}
    bare_unverified = {n for n, _ in unverified}

    text = visible_text(Path(html_path).read_text(encoding="utf-8"))
    problems = []
    for line in text.splitlines():
        for m in NUM.finditer(line):
            n, u = m.group().replace(",", ""), unit_at(line, m.end())
            if u in COUNT_UNITS and n == "1":
                continue                       # "1개·1회"는 하나라는 말
            if u == "년" and re.fullmatch(r"(19|20)\d\d", n):
                u = None                       # "2026년"은 기록의 2026.03과 같은 연도
            if (n, u) in verified if u else n in bare:
                continue
            kind = "UNVERIFIED" if ((n, u) in unverified if u else n in bare_unverified) else "MISSING"
            ctx = line[max(0, m.start() - 30): m.end() + 30]
            shown = m.group() + (UNIT.match(line, m.end()).group().strip() if u else "")
            problems.append(f"{kind:10} {shown:>10}  …{ctx}…")

        for m in WORD_QTY.finditer(line):
            if squash(m.group()) in facts_text:
                continue
            ctx = line[max(0, m.start() - 30): m.end() + 30]
            problems.append(f"{'MISSING':10} {m.group():>10}  …{ctx}…  (숫자 없이 쓴 수량 — 기록에 같은 말이 없다)")

        for m in INTERNAL.finditer(line):
            ctx = line[max(0, m.start() - 30): m.end() + 30]
            problems.append(f"{'INTERNAL':10} {m.group():>10}  …{ctx}…")

    for p in problems:
        print(p)
    print(f"\n수치·내부 용어 검사: 문제 {len(problems)}건")
    return 1 if problems else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
