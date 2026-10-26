"""Базовые проверки статического сайта. Только стандартная библиотека Python."""

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs), self.getpos()[0]))


def main():
    page = PageParser()
    page.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    failures = []
    ids = Counter(attrs["id"] for _, attrs, _ in page.elements if "id" in attrs)
    for element_id, count in ids.items():
        if count > 1:
            failures.append(f"index.html: duplicate id={element_id}")

    def check_reference(value, source, line):
        parts = urlsplit(value)
        if parts.scheme or parts.netloc or value.startswith("data:"):
            return
        if parts.path:
            target = source.parent / unquote(parts.path)
            if not target.is_file():
                failures.append(f"{source.relative_to(ROOT)}:{line}: missing {value}")
        elif parts.fragment and parts.fragment not in ids:
            failures.append(f"index.html:{line}: missing anchor {value}")

    for tag, attrs, line in page.elements:
        for attribute in ("href", "src"):
            if attribute in attrs:
                check_reference(attrs[attribute], ROOT / "index.html", line)
        if "srcset" in attrs:
            for item in attrs["srcset"].split(","):
                check_reference(item.strip().split()[0], ROOT / "index.html", line)
        for attribute in ("aria-labelledby", "aria-describedby", "aria-controls"):
            for target in attrs.get(attribute, "").split():
                if target not in ids:
                    failures.append(f"index.html:{line}: unresolved {attribute}={target}")
        if tag == "img":
            for attribute in ("alt", "width", "height"):
                if attribute not in attrs:
                    failures.append(f"index.html:{line}: img has no {attribute}")
        if attrs.get("target") == "_blank" and "noopener" not in attrs.get("rel", ""):
            failures.append(f"index.html:{line}: external link has no noopener")

    h1_count = sum(tag == "h1" for tag, _, _ in page.elements)
    if h1_count != 1:
        failures.append(f"index.html: expected one H1, found {h1_count}")
    if not any(tag == "html" and attrs.get("lang") == "ru" for tag, attrs, _ in page.elements):
        failures.append("index.html: missing Russian page language")
    if not any(tag == "title" for tag, _, _ in page.elements):
        failures.append("index.html: missing title")
    for name in ("description", "viewport"):
        if not any(tag == "meta" and attrs.get("name") == name and attrs.get("content")
                   for tag, attrs, _ in page.elements):
            failures.append(f"index.html: missing {name} metadata")
    for tag, attrs, line in page.elements:
        if tag == "meta" and attrs.get("property") == "og:image":
            check_reference(attrs.get("content", ""), ROOT / "index.html", line)

    for css in (ROOT / "assets/css").glob("*.css"):
        content = css.read_text(encoding="utf-8")
        for match in re.finditer(r'url\([\"\']?([^\)\"\']+)', content):
            check_reference(match.group(1), css, content[:match.start()].count("\n") + 1)
        if "transition: all" in content:
            failures.append(f"{css.relative_to(ROOT)}: avoid transition: all")

    if failures:
        print("\n".join(failures))
        return 1
    print("PASS: local assets, anchors, ARIA references, image attributes, SEO and CSS checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
