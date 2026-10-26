"""Проверки портфолио, вложенных маршрутов и сохранности существующих страниц."""
import argparse
from collections import Counter
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from check_site import PageParser, ROOT

PAGES = ("projects.html", "projects/barber-cult.html", "projects/forma-architects.html")


class StructureParser(HTMLParser):
    """Ловит незакрытые элементы и случайно вложенные ссылки в новых шаблонах."""
    void = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag == "a" and "a" in self.stack:
            self.errors.append("nested links")
        if tag not in self.void:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append(f"unexpected closing tag {tag} at line {self.getpos()[0]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, help="Снимок SHA-256 до работы над разделом")
    parser.add_argument("--allow-changed", action="append", default=[], help="Разрешённый файл документации")
    args = parser.parse_args()
    failures = []
    cache = {}

    def parse(path):
        path = path.resolve()
        if path not in cache:
            result = PageParser()
            result.feed(path.read_text(encoding="utf-8"))
            cache[path] = result
        return cache[path]

    for name in PAGES:
        path = ROOT / name
        document = parse(path)
        structure = StructureParser()
        structure.feed(path.read_text(encoding="utf-8"))
        failures.extend(f"{name}: {error}" for error in structure.errors)
        if structure.stack:
            failures.append(f"{name}: unclosed tags {structure.stack}")
        ids = Counter(attrs["id"] for _, attrs, _ in document.elements if "id" in attrs)
        if any(count > 1 for count in ids.values()):
            failures.append(f"{name}: duplicate IDs")
        if sum(tag == "h1" for tag, _, _ in document.elements) != 1:
            failures.append(f"{name}: expected one H1")
        for required in ("title", "main", "header", "footer"):
            if not any(tag == required for tag, _, _ in document.elements):
                failures.append(f"{name}: missing {required}")
        for required in ("viewport", "description"):
            if not any(tag == "meta" and attrs.get("name") == required and attrs.get("content")
                       for tag, attrs, _ in document.elements):
                failures.append(f"{name}: missing {required}")

        def reference(value, line):
            parts = urlsplit(value)
            if parts.scheme or parts.netloc:
                return
            target = (path.parent / unquote(parts.path)).resolve() if parts.path else path
            if not target.is_file():
                failures.append(f"{name}:{line}: missing {value}")
            elif parts.fragment and target.suffix == ".html":
                if not any(attrs.get("id") == parts.fragment for _, attrs, _ in parse(target).elements):
                    failures.append(f"{name}:{line}: missing anchor {value}")

        for tag, attrs, line in document.elements:
            for attribute in ("href", "src"):
                if attribute in attrs:
                    reference(attrs[attribute], line)
            if "srcset" in attrs:
                for item in attrs["srcset"].split(","):
                    reference(item.strip().split()[0], line)
            for attribute in ("aria-controls", "aria-labelledby", "aria-describedby"):
                if any(value not in ids for value in attrs.get(attribute, "").split()):
                    failures.append(f"{name}:{line}: unresolved {attribute}")
            if tag == "img" and any(value not in attrs for value in ("alt", "width", "height")):
                failures.append(f"{name}:{line}: missing image attributes")
            if attrs.get("target") == "_blank" and not {"noopener", "noreferrer"}.issubset(attrs.get("rel", "").split()):
                failures.append(f"{name}:{line}: unsafe new-tab link")
        if "contact-status" not in ids:
            failures.append(f"{name}: missing shared Telegram status")

    if args.baseline:
        manifest = json.loads(args.baseline.read_text())
        for name, digest in manifest.items():
            if name in args.allow_changed:
                continue
            path = ROOT/name
            if not path.is_file():
                failures.append(f"Deleted existing file: {name}")
                continue
            content = path.read_bytes()
            if name in ("index.html", "services.html", "hero-a.html", "hero-b.html"):
                old_route = "#projects" if name == "index.html" else "index.html#projects"
                content = content.decode().replace('href="projects.html">Проекты', f'href="{old_route}">Проекты').encode()
            if hashlib.sha256(content).hexdigest() != digest:
                failures.append(f"Unexpected existing-file change: {name}")
        if not failures:
            print("Existing pages preserved; only canonical Projects navigation changed")

    if failures:
        print("\n".join(failures))
        return 1
    print("PASS: portfolio and cases, nested assets/anchors, srcset, ARIA, metadata, external links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
