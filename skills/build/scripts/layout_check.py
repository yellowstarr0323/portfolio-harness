#!/usr/bin/env python3
"""세부 설명 섹션의 이야기 모양(레이아웃) 검사 — 사용자 결정 D-DES-13.

사용법: layout_check.py <portfolio/out/index.html>

브라우저 없이 HTML만 읽는다. export.py가 PDF를 만들기 전에 이 검사를 먼저 돌린다.

검사 (모두 실패):
  1. 세부 설명 섹션(<section data-role="project-detail">)마다 data-layout이 있고, design.base.json의 layouts 키다
  2. 키마다 그 이야기 모양의 부품(components.css)이 섹션 안에 있다 — 키만 바꾸고 모양은 그대로인 경우를 잡는다
       problem-solving → data-role="steps"      timeline → data-role="timeline"
       flow-compare → data-role="flow-compare"  process-flow → data-role="process-flow"
       metric-compare → .ba-lead                decision → data-role="decision-card"
       architecture → img[data-kind=diagram] 또는 <svg>   code → <pre>   image-feature → <img>
  3. 라벨 단계 목록(data-role="steps")은 problem-solving 섹션에서만 쓴다 — 모든 작업이 같은 라벨 행으로 그려지던 원인
  4. 한 프로젝트 안에서 이미 쓴 키를 다시 쓰려면 그 섹션에 data-layout-repeat="이유"를 단다
     (콘텐츠에 맞으면 반복해도 된다 — 이유는 의식적으로 골랐다는 표시)
  5. 범용 형식(problem-solving·text)은 세부 설명이 3개 이상인 프로젝트에서 각각 절반을 넘지 못한다.
     어떤 작업에도 쓸 수 있는 형식이라, 많아지면 모든 작업이 같은 형식으로 보인다(2026-10-10)
  6. metric-compare는 대표 수치(.ba-lead)가 단계 카드·측정 화면보다 먼저 나온다 — 가장 먼저 보여야 할 것이 수치다
  7. problem-solving의 라벨(<dt>)이 모두 일반 라벨(상황·배경·문제·원인·해결·결과·성과·개선)이면 실패 — 기록의 실제 분석 단계
     ("가설", "EXPLAIN 확인", "발견")를 하나 이상 쓴다. 문서 규칙만 있던 것을 옮김(E-9, 10-10)
  8. 세부 설명이 2개 이하인 프로젝트에서 둘 다 problem-solving이면 실패(반복 이유가 있어도) — 절반 상한(5)은 3개 이상에서만 걸린다
프로젝트는 문서 순서에서 가장 최근의 <header data-project="…">로 나눈다.
종료 코드: 통과 0, 실패 1, 실행 불가 2.
"""
import json
import sys
from html.parser import HTMLParser
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "design" / "theme" / "design.base.json"

# 키 → (설명, 섹션 안에 있어야 하는 표시 중 하나). 표시: "role:X" = data-role="X", "class:X", "tag:X", "diagram"
MARKERS = {
    "problem-solving": ("라벨 단계 목록 <dl class=\"steps\" data-role=\"steps\">", ("role:steps",)),
    "timeline": ("<ol class=\"timeline\" data-role=\"timeline\">", ("role:timeline",)),
    "flow-compare": ("<div class=\"flow-compare\" data-role=\"flow-compare\">", ("role:flow-compare",)),
    "process-flow": ("<ol class=\"process-flow\" data-role=\"process-flow\">", ("role:process-flow",)),
    "metric-compare": ("핵심 수치 <p class=\"ba ba-lead\">", ("class:ba-lead",)),
    "decision": ("<div class=\"decision-card\" data-role=\"decision-card\">", ("role:decision-card",)),
    "architecture": ("구조도 <img data-kind=\"diagram\"> 또는 인라인 <svg>", ("diagram", "tag:svg")),
    "code": ("코드 발췌 <pre>", ("tag:pre",)),
    "image-feature": ("큰 이미지 <img>", ("tag:img",)),
}
GENERIC_LABELS = {"상황", "배경", "문제", "원인", "해결", "결과", "성과", "개선"}   # 어떤 작업에도 붙는 라벨
GENERIC = {"problem-solving", "text"}   # 어떤 작업에도 쓸 수 있는 범용 형식 — 절반 상한
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Sections(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.project = ""
        self.cur: dict | None = None
        self.depth = 0                      # cur 섹션이 열린 스택 깊이
        self.found: list[dict] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "header" and a.get("data-project"):
            self.project = a["data-project"]
        if tag == "section" and a.get("data-role") == "project-detail" and self.cur is None:
            title = a.get("data-fact", "").split(",")[0].split("#")[-1].strip()
            self.cur = {"project": self.project, "layout": a.get("data-layout"), "repeat": a.get("data-layout-repeat"),
                        "title": title, "marks": set(), "order": [], "labels": [], "line": self.getpos()[0]}
            self.depth = len(self.stack) + 1
        elif self.cur is not None:
            m = self.cur["marks"]
            if a.get("data-role"):
                m.add("role:" + a["data-role"])
            for c in (a.get("class") or "").split():
                m.add("class:" + c)
            m.add("tag:" + tag)
            for c in (a.get("class") or "").split():
                if c in ("ba-lead", "stage-cards", "measure-pair") and c not in self.cur["order"]:
                    self.cur["order"].append(c)
            if tag == "img" and a.get("data-kind") == "diagram":
                m.add("diagram")
            if tag == "dt":
                self.cur["labels"].append("")
        if tag not in VOID:
            self.stack.append(tag)

    def handle_data(self, data):
        if self.cur is not None and self.stack and "dt" in self.stack and self.cur["labels"]:
            self.cur["labels"][-1] += data

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag in VOID or not self.stack:
            return
        # 닫는 태그와 짝이 맞는 가장 가까운 여는 태그까지 닫는다(잘못 닫힌 HTML에 관대하게)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i] == tag:
                del self.stack[i:]
                break
        if self.cur is not None and len(self.stack) < self.depth:
            self.found.append(self.cur)
            self.cur = None


def check(html: str, keys: set[str]) -> tuple[list[str], list[str]]:
    p = Sections()
    p.feed(html)
    if p.cur is not None:
        p.found.append(p.cur)
    fails, notes = [], []
    by_project: dict[str, list[dict]] = {}
    for s in p.found:
        by_project.setdefault(s["project"], []).append(s)
    for proj, secs in by_project.items():
        seen: dict[str, str] = {}
        for s in secs:
            name = f"[{proj or '?'}] " + (s["title"] or f"{s['line']}번째 줄 섹션")
            key = s["layout"]
            if not key:
                fails.append(f"{name}: data-layout이 없다 — 이야기 모양에 맞는 키를 단다 (design \"이야기 모양\" 표)")
                continue
            if key not in keys:
                fails.append(f"{name}: 없는 레이아웃 키 '{key}' (허용: {', '.join(sorted(keys))})")
                continue
            if key in MARKERS:
                desc, need = MARKERS[key]
                if not any(n in s["marks"] for n in need):
                    fails.append(f"{name}: '{key}'인데 그 모양의 부품이 없다 — {desc}")
            if key == "metric-compare" and "ba-lead" in s["order"] and s["order"][0] != "ba-lead":
                fails.append(f"{name}: metric-compare인데 대표 수치(.ba-lead)보다 {s['order'][0]}가 먼저 나온다 — 수치를 맨 위에 둔다")
            labels = [l.strip() for l in s["labels"] if l.strip()]
            if key == "problem-solving" and labels and all(l in GENERIC_LABELS for l in labels):
                fails.append(f"{name}: 라벨이 일반 라벨({'·'.join(labels)})뿐이다 — 기록의 실제 분석 단계(\"가설\", \"EXPLAIN 확인\", "
                             f"\"발견\")를 하나 이상 라벨로 쓴다")
            if key != "problem-solving" and "role:steps" in s["marks"]:
                fails.append(f"{name}: 라벨 단계 목록(data-role=\"steps\")은 problem-solving 섹션에서만 쓴다 ('{key}' 섹션)")
            if key in seen:
                if s["repeat"]:
                    notes.append(f"{name}: '{key}' 다시 씀 — 이유: {s['repeat']}")
                else:
                    fails.append(f"{name}: '{key}'를 이미 '{seen[key]}'에서 썼다 — 이야기 모양이 다른 키를 고르거나, "
                                 f"정말 같은 모양이면 data-layout-repeat=\"이유\"를 단다")
            else:
                seen[key] = s["title"] or key
        counted = [s["layout"] for s in secs if s["layout"] in keys]
        if 2 <= len(counted) <= 2 and counted.count("problem-solving") == 2:
            fails.append(f"[{proj or '?'}] 세부 설명 2개가 모두 problem-solving(라벨 행)이다 — 한 프로젝트에 한 번이 기본. "
                         f"하나는 이야기 모양에 맞는 다른 키로 그린다")
        if len(counted) >= 3:
            for key in set(counted) & GENERIC:
                n = counted.count(key)
                if n * 2 > len(counted):
                    fails.append(f"[{proj or '?'}] 범용 형식 '{key}'가 세부 설명 {len(counted)}개 중 {n}개 — 절반을 넘으면 "
                                 f"모든 작업이 같은 형식으로 보인다. 작업마다 이야기 모양(design 표)을 다시 고른다")
        layouts = " → ".join(s["layout"] or "?" for s in secs)
        notes.insert(0, f"[{proj or '?'}] 세부 설명 {len(secs)}개: {layouts}")
    if not p.found:
        notes.append("세부 설명 섹션(data-role=\"project-detail\")이 없다 — 검사할 것 없음")
    return fails, notes


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[2])
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"파일이 없다: {path}")
        return 2
    keys = set(json.loads(BASE.read_text(encoding="utf-8"))["layouts"])
    fails, notes = check(path.read_text(encoding="utf-8"), keys)
    for n in notes:
        print(n)
    for f in fails:
        print(f"실패: {f}")
    print(f"레이아웃 검사: {'통과' if not fails else f'실패 {len(fails)}건'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
