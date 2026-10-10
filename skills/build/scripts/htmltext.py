"""HTML에서 보이는 텍스트만 뽑는다. <title>·script/style과 skip 속성을 가진 요소(및 그 하위)는 제외."""
from html.parser import HTMLParser

# 본문에 렌더되지 않는 태그. <title>은 PDF에 찍히지 않으므로 텍스트 대조·수치 검사에서 빠져야 한다.
NON_RENDERED = {"title", "script", "style", "template", "noscript"}

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class _Extractor(HTMLParser):
    def __init__(self, skip_attrs: tuple[str, ...]) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_attrs = skip_attrs
        self.stack: list[bool] = []  # 각 열린 요소가 '제외 구간'을 시작했는지
        self.skip_depth = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        excluded = tag in NON_RENDERED or any(k in self.skip_attrs for k, _ in attrs)
        self.stack.append(excluded)
        if excluded:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag in VOID or not self.stack:
            return
        if self.stack.pop():
            self.skip_depth -= 1

    def handle_data(self, data):
        if self.skip_depth == 0:
            self.chunks.append(data)


def visible_text(html: str, skip_attrs: tuple[str, ...] = ("data-nocheck",)) -> str:
    p = _Extractor(skip_attrs)
    p.feed(html)
    return "\n".join(c for c in (s.strip() for s in p.chunks) if c)
