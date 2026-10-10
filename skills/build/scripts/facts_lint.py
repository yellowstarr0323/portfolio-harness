#!/usr/bin/env python3
"""기록(facts) 사전 검증 — HTML·PDF를 만들기 전에 입력 문제를 잡는다.

사용법: facts_lint.py <portfolio/facts> [--images <portfolio/images>] [--sources <portfolio/sources>] [--cache <파일>] [--json]

책임 구분
- facts_lint.py (사전 검증): **입력**이 올바른가. 기록 형식, 필수 칸, 기간 논리, 이미지 기록.
  인터뷰 직후와 build 시작 전에 돌리고, export.py도 PDF를 만들기 전에 다시 돌린다(같은 입력이면 캐시 재사용).
- export.py (최종 검증): **산출물**이 올바른가. 넘침, 여백, 글자 크기, 첫머리 순서, 측정 화면 배치, 텍스트 일치.

결과 구분
- ERROR[수정]: 사용자 의도를 바꾸지 않고 안전하게 고칠 수 있다 — "고치는 법"대로 기록을 고친다
- ERROR[확인]: 사용자가 정해야 한다 — 추측해서 채우지 않고 "물을 것"을 묻는다
- WARN: 진행은 되지만 결과물이 약해진다
ERROR가 하나라도 있으면 HTML 생성과 PDF export를 진행하지 않는다.

검사 (실제 기록 형식: interview 스킬 "사실 파일 형식" 기준)
- profile.md: 파일 존재, frontmatter `kind: profile`, `## 기본 정보`의 이름,
  `## 수상·자격증`·`## 활동`이 있고 항목마다 날짜(YYYY.MM 이상)가 있음 — 없다고 확인했으면 "- 활동 없음" 한 줄(D-P1-4)
- 프로젝트 파일(profile.md·백업 제외)
  - frontmatter `project`, `slug`
  - 기간: `start`(YYYY.MM), `status`(운영 중/개발 중/종료), 종료면 `end` 필수, 진행 중이면 `end` 비움,
          `end`가 `start`보다 이르면 안 됨, 옛 `period`만 있으면 WARN
  - 사용 기술: `## 사용 기술` 또는 `## 기술 선택`에 하나라도 있어야 함(둘 다 없으면 ERROR, `## 사용 기술`만 없으면 WARN)
  - `## 주요 기능` 비어 있으면 WARN
  - `## 이미지`: 로고·서비스 화면(또는 "없음" 기록), 종류 이름, 파일 존재(--images), 측정 화면 전/후 표시(WARN).
    필수 이미지가 없을 때 `images/<slug>/`에 기록 안 된 파일이 있으면 "확인받은 뒤 기록"을 안내한다(추측 등록 금지)
  - `status: 충돌` 남음
- 근거 원문 대조(D-TXT-6): 기록 본문(frontmatter·`## 이미지` 제외)의 수치가 사용자가 직접 한 말
  (`sources/interview-log.md`, 훅 hooks/log_answers.py가 씀)이나 받은 자료(`sources/`의 글·PDF)에 있어야 한다.
  없으면 ERROR[확인] — 지어냈거나 계산한 값이다. 근거에 이미지 자료(`doc:img-….png`)가 있는 줄은 이미지 속 숫자를
  글자로 대조할 수 없어 WARN으로 모은다. 자료의 버전 3.2.3은 기록의 3.2도 근거로 본다.
  출처 태그대로 찾는다(interview → 사용자 말, doc:X → 그 자료, 태그 없으면 전부). 개선 전 → 후 두 값은 원문 한 곳
  (메시지·답·자료 하나)에 같이 있어야 한다 — 흔한 작은 수가 다른 대화에서 우연히 맞아 통과하지 않게
  근거 원문 기록이 없으면(이 기능 전 기록) 대조를 건너뛰고 WARN. --sources로 폴더를 바꾼다(기본: 기록 폴더 옆 sources/)
종료 코드: ERROR 없음 0, 있음 1, 사용법 오류 2.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

STATUSES = {"운영 중", "개발 중", "종료"}
IMAGE_KINDS = {"로고", "서비스 화면", "화면 캡처", "사진", "측정 화면", "다이어그램", "사용 안 함"}
YM = re.compile(r"^(\d{4})\.(\d{2})(\.\d{2})?$")
YM_LOOSE = re.compile(r"^(\d{4})\s*[-/.년]\s*(\d{1,2})\s*월?(?:[-/.]\s*\d{1,2}\s*일?)?$")
H2 = re.compile(r"^##\s+(.*)$")
PROFILE_DATE = re.compile(r"\b\d{4}\.\d{1,2}(\.\d{1,2})?\b")   # 수상·자격증·활동 날짜(YYYY.MM 이상)
H3 = re.compile(r"^###\s+(.*)$")


class Issues:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, level: str, file: str, field: str, msg: str, action: str = "", how: str = "") -> None:
        self.items.append({"level": level, "file": file, "field": field, "msg": msg, "action": action, "how": how})

    def fix(self, file, field, msg, how):      # 안전하게 고칠 수 있음
        self.add("ERROR", file, field, msg, "수정", how)

    def ask(self, file, field, msg, how):      # 사용자가 정해야 함
        self.add("ERROR", file, field, msg, "확인", how)

    def warn(self, file, field, msg, how=""):
        self.add("WARN", file, field, msg, "", how)

    @property
    def errors(self) -> int:
        return sum(1 for i in self.items if i["level"] == "ERROR")


def frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep:
            out[k.strip()] = v.split("#", 1)[0].strip()
    return out


def sections(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    cur = None
    for line in text.splitlines():
        if m := H2.match(line):
            cur = m.group(1).strip()
            out.setdefault(cur, [])
        elif cur is not None:
            out[cur].append(line)
    return out


def bullets(lines: list[str]) -> list[str]:
    return [l.strip()[2:].strip() for l in lines if l.strip().startswith("- ")]


def ym_value(s: str) -> tuple[int, int] | None:
    m = YM.match(s)
    return (int(m.group(1)), int(m.group(2))) if m else None


def suggest_ym(s: str) -> str | None:
    m = YM_LOOSE.match(s.strip())
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{m.group(1)}.{int(m.group(2)):02d}"
    return None


def check_date(iss: Issues, name: str, field: str, value: str) -> tuple[int, int] | None:
    v = ym_value(value)
    if v:
        if not 1 <= v[1] <= 12:
            iss.ask(name, field, f"월이 1~12가 아니다 — `{value}`", f"`{field}`의 올바른 연·월을 묻는다")
            return None
        return v
    sug = suggest_ym(value) if value else None
    if sug:
        iss.fix(name, field, f"날짜 형식이 `YYYY.MM`이 아니다 — `{value}`", f"`{field}: {sug}`로 바꾼다 (같은 날짜, 표기만 다름)")
    else:
        iss.ask(name, field, f"날짜가 없거나 알아볼 수 없다 — `{value or '(없음)'}`", f"프로젝트 {field == 'start' and '시작' or '종료'} 연·월을 묻는다")
    return None


def lint_profile(path: Path, iss: Issues) -> None:
    text = path.read_text(encoding="utf-8")
    if frontmatter(text).get("kind") != "profile":
        iss.fix(path.name, "kind", "프로필 표시(`kind: profile`)가 없다 — 재료 점검·build가 프로젝트와 구분하지 못할 수 있다",
                "파일 맨 위에 `---` / `kind: profile` / `---` 세 줄을 넣는다")
    secs = sections(text)
    info = " ".join(secs.get("기본 정보", []))
    if not re.search(r"이름\s*[:：]\s*\S", info):
        iss.ask(path.name, "기본 정보.이름", "이름이 없다", "이름을 묻는다")
    # 수상·자격증과 활동은 날짜가 필수다(사용자 결정 D-P1-4). 없다고 확인한 경우만 "~ 없음" 한 줄로 통과
    for sec, none_word, what in (("수상·자격증", "수상·자격증 없음", "수상·자격증"), ("활동", "활동 없음", "활동")):
        if sec not in secs:
            iss.ask(path.name, sec, f"`## {sec}`이 없다 — {what}을 아직 묻지 않았다",
                    f"{what}을 날짜와 함께 묻는다. 없다고 하면 `- {none_word}`으로 기록한다")
            continue
        items = [b for b in bullets(secs[sec]) if not re.match(rf"^{re.escape(none_word)}", re.sub(r"`[^`]*`", "", b).strip())]
        if not items and not bullets(secs[sec]):
            iss.ask(path.name, sec, f"`## {sec}`이 비어 있다",
                    f"{what}을 날짜와 함께 묻는다. 없다고 하면 `- {none_word}`으로 기록한다")
        for b in items:
            plain = re.sub(r"`[^`]*`", "", b).strip()
            if not PROFILE_DATE.search(plain):
                iss.ask(path.name, f"{sec}.{plain.split('|')[0].strip()[:30]}", f"날짜가 없다 — `{plain[:60]}`",
                        "언제였는지 묻는다(날짜 `YYYY.MM.DD` 또는 기간 `YYYY.MM ~ YYYY.MM`). 날을 모르면 연·월까지만 받는다")


def lint_images(name: str, lines: list[str], images_dir: Path | None, iss: Issues, slug: str = "") -> None:
    kinds, measures, listed = [], [], set()
    for it in bullets(lines):
        plain = re.sub(r"`[^`]*`", "", it).strip()
        if re.match(r"^로고\s*없음", plain):
            kinds.append("로고 없음")
            continue
        if re.match(r"^서비스\s*화면\s*없음", plain):
            kinds.append("서비스 화면 없음")
            continue
        cols = [c.strip() for c in plain.split("|")]
        if len(cols) < 2:
            continue
        file, kind = cols[0], cols[1]
        listed.add(Path(file).name)
        caption = cols[2] if len(cols) > 2 else ""
        if kind not in IMAGE_KINDS:
            iss.fix(name, f"이미지.{file}.종류", f"허용되지 않는 이미지 종류 `{kind}`",
                    f"ingest의 이미지 절차로 다시 분류한다 ({' / '.join(sorted(IMAGE_KINDS))})")
        kinds.append(kind)
        if kind == "측정 화면":
            measures.append((file, caption))
        if images_dir and kind != "사용 안 함" and not any(images_dir.rglob(Path(file).name)):
            iss.ask(name, f"이미지.{file}", f"기록된 이미지 파일이 {images_dir}에 없다",
                    "이미지를 채팅으로 다시 달라고 하거나(파일 끌어다 놓기·링크), 쓰지 않을 거면 `사용 안 함`으로 바꿀지 묻는다")
    # 폴더에 있지만 기록에 없는 파일 — 파일이 있다는 것만으로 용도를 정하지 않는다(rules/user-decisions.md R-EVD-7)
    folder = images_dir / slug if images_dir and slug and (images_dir / slug).is_dir() else None
    unlisted = sorted(p.name for p in folder.iterdir() if p.is_file() and p.name not in listed) if folder else []
    hint = (f" 폴더에 기록에 없는 파일({', '.join(unlisted)})이 있지만, 파일 이름만 보고 용도를 정하지 않는다 — "
            "무엇인지 사용자에게 확인받은 뒤(ingest 이미지 절차) 기록하고, 확인 전에는 `[src: interview]`를 달지 않는다") if unlisted else ""
    if "로고" not in kinds and "로고 없음" not in kinds:
        iss.ask(name, "이미지.로고", "프로젝트 로고가 없다(필수)",
                "로고를 채팅으로 달라고 하거나(파일 끌어다 놓기·링크, AI가 images/로 복사), 없다고 하면 `- 로고 없음`으로 기록한다." + hint)
    if "서비스 화면" not in kinds and "서비스 화면 없음" not in kinds:
        iss.ask(name, "이미지.서비스 화면", "서비스 화면이 없다(필수)",
                "대표 화면(캡처·목업)을 채팅으로 달라고 하거나(파일 끌어다 놓기·링크, AI가 images/로 복사), 없다고 하면 `- 서비스 화면 없음`으로 기록한다." + hint)
    if len(measures) >= 2:
        for file, cap in measures:
            if not re.search(r"(개선\s*)?(전|후)\b|before|after", cap, re.I):
                iss.warn(name, f"이미지.{file}.캡션", "측정 화면 캡션에 개선 전/후 표시가 없다",
                         "전·후 짝을 같은 쪽에 두려면 캡션에 개선 전/후를 붙인다")


def lint_project(path: Path, images_dir: Path | None, iss: Issues) -> None:
    text = path.read_text(encoding="utf-8")
    name = path.name
    fm = frontmatter(text)
    if not fm.get("project"):
        iss.ask(name, "project", "프로젝트 이름이 없다", "프로젝트 이름을 묻는다")
    if not fm.get("slug"):
        iss.fix(name, "slug", "slug가 없다", f"`slug: {path.stem}`(파일 이름)으로 넣는다")

    start, end, status, period = fm.get("start", ""), fm.get("end", ""), fm.get("status", ""), fm.get("period", "")
    if not start and period:
        iss.warn(name, "period", f"옛 기간 형식 `period: {period}` — build가 합쳐 쓰지만 `start`/`end`/`status`로 옮기는 게 낫다")
        s = None
    else:
        s = check_date(iss, name, "start", start)
    if status not in STATUSES:
        iss.ask(name, "status", f"상태가 운영 중/개발 중/종료 중 하나가 아니다 — `{status or '(없음)'}`",
                "지금 운영 중인지, 개발 중인지, 끝났는지 묻는다")
    elif status == "종료":
        e = check_date(iss, name, "end", end)
        if s and e and e < s:
            iss.ask(name, "end", f"종료일 `{end}`이 시작일 `{start}`보다 이르다", "시작·종료 연·월을 다시 묻는다")
    elif end:
        iss.ask(name, "end", f"`status: {status}`인데 종료일 `{end}`이 있다",
                "아직 진행 중이면 종료일을 비우고, 끝났으면 상태를 `종료`로 바꿀지 묻는다")

    secs = sections(text)
    tech = bullets(secs.get("사용 기술", []))
    choices = [l for l in secs.get("기술 선택", []) if H3.match(l)]
    if not tech and not choices:
        iss.ask(name, "사용 기술", "사용 기술 정보가 없다(`## 사용 기술`도 `## 기술 선택`도 비었다)",
                "이 프로젝트에서 쓴 언어·프레임워크·DB·인프라를 묻는다")
    elif not tech:
        iss.warn(name, "사용 기술", "`## 사용 기술`이 비었다 — PDF의 사용 기술 줄을 기술 선택에서만 모으게 된다",
                 "인터뷰에서 사용 기술을 한 번 묻는다")
    if not bullets(secs.get("주요 기능", [])):
        iss.warn(name, "주요 기능", "`## 주요 기능`이 비었다 — PDF에서 기능 소개 블록이 빠진다", "주요 기능 3~5개를 한 번 묻는다")

    lint_images(name, secs.get("이미지", []), images_dir, iss, fm.get("slug") or path.stem)
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(r"status:\s*충돌", line):
            iss.ask(f"{name}:{i}", "충돌", f"자료끼리 다른 값이 남아 있다 — {line.strip()[:60]}", "어느 값이 맞는지 묻는다")


# ---------- 근거 원문 대조 (D-TXT-6) ----------

FACT_NUM = re.compile(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?")
CORPUS_NUM = re.compile(r"\d+(?:[.,]\d+)*")
TEXT_EXT = {".md", ".txt", ".html", ".htm", ".svg", ".json", ".csv", ".log", ".yml", ".yaml"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
TAG = re.compile(r"`?\[(src|status):[^\]]*\]`?")
NOISE = re.compile(r"https?://\S+|\b[\w.-]+\.(?:png|jpe?g|gif|webp|svg|md|pdf|html?)\b|doc:\S+|link:\S+", re.I)


def norm(n: str) -> str:
    n = n.replace(",", "")
    if "." in n:
        a, b = n.split(".", 1)
        return f"{a.lstrip('0') or '0'}.{b.rstrip('0')}".rstrip(".")
    return n.lstrip("0") or "0"


def numbers_in(text: str) -> set[str]:
    nums: set[str] = set()
    for m in CORPUS_NUM.finditer(text):
        tok = m.group()
        nums.add(norm(tok))
        parts = [x for x in re.split(r"[.,]", tok) if x]
        nums.update(norm(x) for x in parts)
        if tok.count(".") > 1:                     # 버전 3.2.3 → 기록의 "3.2"도 근거로 본다
            nums.update(norm(".".join(parts[:k])) for k in range(2, len(parts)))
    return nums


def corpus_entries(sources: Path) -> tuple[list[tuple[str, set[str]]], bool]:
    """[(출처 이름, 수치 집합)]. 근거 원문 기록은 메시지·답 하나가 한 항목, 받은 자료는 파일 하나가 한 항목.
    두 번째 값은 근거 원문 기록(interview-log.md)이 있는지."""
    entries: list[tuple[str, set[str]]] = []
    log = sources / "interview-log.md"
    for p in sorted(sources.rglob("*")) if sources.is_dir() else []:
        if not p.is_file() or p.name.startswith("."):
            continue
        if p == log:
            for chunk in re.split(r"^## ", p.read_text(encoding="utf-8", errors="replace"), flags=re.M)[1:]:
                body = chunk.split("\n", 1)[1] if "\n" in chunk else ""
                entries.append(("interview", numbers_in(body)))
        elif p.suffix.lower() in TEXT_EXT:
            entries.append((p.relative_to(sources).as_posix(), numbers_in(p.read_text(encoding="utf-8", errors="replace"))))
        elif p.suffix.lower() == ".pdf":
            import shutil
            import subprocess
            if shutil.which("pdftotext"):
                text = subprocess.run(["pdftotext", str(p), "-"], capture_output=True, text=True).stdout
                entries.append((p.relative_to(sources).as_posix(), numbers_in(text)))
    return entries, log.is_file()


def fact_values(tok: str) -> list[str]:
    """기록의 수치 하나가 원문에서 찾아야 할 값들. 날짜 2026.03(.01)은 연·월(·일)로 나눠 찾는다."""
    if d := re.fullmatch(r"(\d{4})\.(\d{1,2})(?:\.(\d{1,2}))?", tok.replace(",", "")):
        return [norm(x) for x in d.groups() if x]
    return [norm(tok)]


ARROW = re.compile(r"(?<![\w.])(\d[\d,.]*)\s*[A-Za-z%가-힣]{0,6}\s*(?:→|->)\s*[~약]?\s*(\d[\d,.]*)")


def line_tags(line: str) -> list[str]:
    m = re.search(r"\[src:([^\]]*)\]", line)
    return [t.strip() for t in m.group(1).split(",")] if m else []


def lint_provenance(facts: Path, sources: Path, iss: Issues) -> None:
    entries, has_log = corpus_entries(sources)
    if not has_log:
        iss.warn("-", "근거 원문", "사용자가 한 말의 기록(sources/interview-log.md)이 없어 수치 출처 대조를 건너뛴다",
                 "이 기능 전에 만든 기록이다. 플러그인 훅이 켜진 세션에서 인터뷰하면 자동으로 생긴다")
        return
    image_only: list[str] = []
    how = ("지어냈거나 계산한 값이면 기록에서 지운다. 사용자가 말한 값이면 질문 도구(AskUserQuestion) 선택지에 "
           "이 수치를 그대로 넣어 맞는지 확인받는다(고른 답이 근거 원문에 남는다). 근거 원문 파일은 고치지 않는다")
    for path in sorted(facts.glob("*.md")):
        if ".bak" in path.name:
            continue
        text = path.read_text(encoding="utf-8")
        body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S)
        section, block_tags = "", []
        for line in body.splitlines():
            if h := H2.match(line):
                section, block_tags = h.group(1).strip(), []
                continue
            if H3.match(line):
                block_tags = []
                continue
            if section == "이미지":
                continue
            own = line_tags(line)
            tags = own or block_tags
            if own:
                block_tags = own
            docs = [t[4:] for t in tags if t.startswith("doc:")]
            from_image = any(Path(d).suffix.lower() in IMAGE_EXT for d in docs)
            # 출처 태그가 가리키는 원문만 본다: interview → 사용자 말, doc:X → 그 자료. 태그가 없으면 전부
            names = {"interview"} if "interview" in tags else set()
            names |= {d for d in docs if Path(d).suffix.lower() not in IMAGE_EXT}
            pool = [nums for name, nums in entries if not tags or name in names
                    or any(name.endswith("/" + n) for n in names)]
            seen = set().union(*pool) if pool else set()
            clean = NOISE.sub(" ", TAG.sub(" ", line))
            missing = [m.group() for m in FACT_NUM.finditer(clean) if not all(v in seen for v in fact_values(m.group()))]
            # 개선 전 → 후는 두 값이 원문 한 곳(메시지·답·자료 하나)에 같이 있어야 한다 — 흔한 작은 수가 우연히 통과하지 않게
            split = [f"{a} → {b}" for a, b in ((x.rstrip(",."), y.rstrip(",.")) for x, y in ARROW.findall(clean))
                     if a not in missing and b not in missing
                     and not any(norm(a) in nums and norm(b) in nums for nums in pool)]
            if (missing or split) and from_image:  # 이미지에서 읽은 수치는 글자로 대조할 수 없다
                image_only.append(f"{path.name}: {', '.join(missing + split)}")
            elif missing and (elsewhere := sorted({name for name, nums in entries if name not in names
                                                    and all(all(v in nums for v in fact_values(t)) for t in missing)})):
                fix = [("interview" if n == "interview" else f"doc:{n}") for n in elsewhere][:3]
                iss.fix(path.name, section or "-", f"수치 {', '.join(missing)}가 출처 태그({', '.join(tags) or '없음'})가 아니라 "
                        f"{', '.join(fix)}에 있다 — \"{line.strip()[:80]}\"", f"출처 태그에 {', '.join(fix)}를 더한다(사용자 말이 근거가 아니면 interview는 뺀다)")
            elif missing:
                iss.ask(path.name, section or "-", f"사용자가 한 말·받은 자료에 없는 수치 {', '.join(missing)} — \"{line.strip()[:80]}\"", how)
            elif split:
                iss.ask(path.name, section or "-", f"개선 전·후 수치 {', '.join(split)}가 원문 한 곳에 같이 나온 적이 없다 — \"{line.strip()[:80]}\"",
                        "두 값을 사용자가 따로 말했거나 다른 자료에서 왔다. 짝이 맞는지 \"A → B\" 그대로 선택지에 넣어 확인받는다. " + how.split(". ", 1)[0] + ".")
    if image_only:
        iss.warn("-", "근거 원문", f"이미지 자료에서 읽은 수치(글자 자료·사용자 말에 없음) — {' / '.join(image_only)}",
                 "글자로 대조할 수 없다. 이미지에 실제로 있는 값인지 다시 열어 보고, 사용자에게 한 번 확인받는다")


def fingerprint(facts: Path, images_dir: Path | None, sources: Path | None = None) -> str:
    h = hashlib.sha256()
    for p in sorted(facts.glob("*.md")):
        if ".bak" in p.name:
            continue
        h.update(p.name.encode())
        h.update(p.read_bytes())
    if images_dir and images_dir.is_dir():
        for p in sorted(images_dir.rglob("*")):
            if p.is_file():
                h.update(str(p.relative_to(images_dir)).encode())
                h.update(hashlib.sha256(p.read_bytes()).digest())   # 내용 해시 — 크기가 같은 파일로 바꿔도 감지
    if sources and sources.is_dir():               # 근거 원문이 늘면 대조 결과가 바뀐다
        for p in sorted(sources.rglob("*")):
            if p.is_file():
                h.update(str(p.relative_to(sources)).encode())
                h.update(hashlib.sha256(p.read_bytes()).digest())
    h.update(Path(__file__).read_bytes())          # 검사 규칙이 바뀌면 캐시도 무효
    return h.hexdigest()


def lint(facts: Path, images_dir: Path | None, sources: Path | None = None) -> Issues:
    iss = Issues()
    profile = facts / "profile.md"
    if profile.exists():
        lint_profile(profile, iss)
    else:
        iss.ask("profile.md", "-", "프로필 기록이 없다", "인터뷰 1단계(프로필)부터 한다")
    projects = [p for p in sorted(facts.glob("*.md")) if p.name != "profile.md" and ".bak" not in p.name]
    if not projects:
        iss.ask("-", "-", "프로젝트 기록 파일이 없다", "인터뷰 2단계(프로젝트 목록)부터 한다")
    for p in projects:
        lint_project(p, images_dir, iss)
    if sources is not None:
        lint_provenance(facts, sources, iss)
    return iss


def render(items: list[dict], nproj: int) -> str:
    lines = []
    for it in sorted(items, key=lambda i: (i["level"] != "ERROR", i["action"] != "확인")):
        tag = f"{it['level']}[{it['action']}]" if it["action"] else it["level"]
        lines.append(f"{tag:10} {it['file']} › {it['field']}: {it['msg']}")
        if it["how"]:
            lines.append(f"{'':10}   → {'고치는 법' if it['action'] == '수정' else '물을 것' if it['action'] == '확인' else '참고'}: {it['how']}")
    n_err = sum(1 for i in items if i["level"] == "ERROR")
    n_fix = sum(1 for i in items if i["action"] == "수정")
    n_ask = sum(1 for i in items if i["action"] == "확인")
    n_warn = sum(1 for i in items if i["level"] == "WARN")
    lines.append(f"\n기록 검사: ERROR {n_err} (수정 {n_fix} / 확인 {n_ask}) · WARN {n_warn} · 프로젝트 {nproj}개"
                 + ("" if not n_err else " — HTML·PDF를 만들기 전에 ERROR를 해결한다"))
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    facts = Path(argv[0])
    opt = lambda k: argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else None  # noqa: E731
    images_dir = Path(opt("--images")) if opt("--images") else None
    sources = Path(opt("--sources")) if opt("--sources") else Path(argv[0]).parent / "sources"
    cache = Path(opt("--cache")) if opt("--cache") else None
    if not facts.is_dir():
        print(f"기록 폴더가 없다: {facts}")
        return 2

    fp = fingerprint(facts, images_dir, sources)
    if cache and cache.exists():
        try:
            c = json.loads(cache.read_text(encoding="utf-8"))
            if c.get("fingerprint") == fp:
                if "--json" in argv:
                    print(json.dumps(c, ensure_ascii=False, indent=2))
                else:
                    print("(기록이 바뀌지 않아 이전 검사 결과를 재사용한다)")
                    print(render(c["items"], c["projects"]))
                return 1 if c["errors"] else 0
        except (json.JSONDecodeError, KeyError):
            pass

    iss = lint(facts, images_dir, sources)
    nproj = len([p for p in facts.glob("*.md") if p.name != "profile.md" and ".bak" not in p.name])
    result = {"fingerprint": fp, "errors": iss.errors, "projects": nproj, "items": iss.items}
    if cache:
        cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2) if "--json" in argv else render(iss.items, nproj))
    return 1 if iss.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
