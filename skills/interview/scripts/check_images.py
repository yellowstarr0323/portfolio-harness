#!/usr/bin/env python3
"""프로젝트마다 필수 이미지(로고 1장 + 프로젝트 화면 1장 이상)가 있는지 확인한다.

사용법: check_images.py <portfolio 폴더>

- 프로젝트 목록: portfolio/projects/*.md 의 파일 이름(슬러그)
- 이미지 위치: portfolio/images/<슬러그>/logo.<확장자> (정확히 1개), screen-<번호>.<확장자> (1개 이상)
- 확장자: png, jpg, jpeg, gif, webp, svg. 0바이트 파일은 없는 것으로 본다
종료 코드: 모두 있음 0, 빠진 것 있음 1, 사용법 오류 2.
"""
import sys
from pathlib import Path

EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def images(folder: Path, stem_prefix: str) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir()
                  if p.is_file() and p.suffix.lower() in EXT and p.stat().st_size > 0
                  and (p.stem == "logo" if stem_prefix == "logo" else p.stem.startswith(stem_prefix)))


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not Path(argv[0]).is_dir():
        print(__doc__.strip().splitlines()[2])
        return 2
    pf = Path(argv[0])
    slugs = sorted(p.stem for p in (pf / "projects").glob("*.md"))
    if not slugs:
        print("프로젝트 기록이 없다: portfolio/projects/*.md")
        return 1
    missing = 0
    for slug in slugs:
        folder = pf / "images" / slug
        logos, screens = images(folder, "logo"), images(folder, "screen-")
        problems = []
        if not logos:
            problems.append("로고 없음")
        elif len(logos) > 1:
            problems.append(f"로고가 {len(logos)}개 — 하나만 남긴다")
        if not screens:
            problems.append("프로젝트 화면 없음")
        if problems:
            missing += 1
            print(f"빠짐: {slug} — {', '.join(problems)} ({folder}/)")
        else:
            print(f"있음: {slug} — 로고 1, 화면 {len(screens)}")
    print(f"프로젝트 이미지: {'모두 있음' if not missing else f'{missing}개 프로젝트에 빠짐'}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
