"""Проверки контактов, внутренних маршрутов и сохранности существующих файлов."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit, unquote

from check_site import PageParser, ROOT
from check_projects import StructureParser

EXISTING = ("index.html", "services.html", "projects.html", "about.html", "hero-a.html", "hero-b.html",
            "projects/barber-cult.html", "projects/forma-architects.html")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, help="Снимок SHA-256 перед созданием контактов")
    parser.add_argument("--allow-changed", action="append", default=[], help="Разрешённое обновление документации")
    args = parser.parse_args()
    failures, cache = [], {}

    def parse(path):
        path = path.resolve()
        if path not in cache:
            result = PageParser()
            result.feed(path.read_text(encoding="utf-8"))
            cache[path] = result
        return cache[path]

    for name in (*EXISTING, "contact.html"):
        path = ROOT/name
        page = parse(path)
        ids = Counter(attrs["id"] for _, attrs, _ in page.elements if "id" in attrs)
        if any(count > 1 for count in ids.values()):
            failures.append(f"{name}: duplicate IDs")

        def reference(value, line):
            parts = urlsplit(value)
            if parts.scheme or parts.netloc:
                return
            target = (path.parent/unquote(parts.path)).resolve() if parts.path else path
            if not target.is_file():
                failures.append(f"{name}:{line}: missing {value}")
            elif parts.fragment and target.suffix == ".html":
                if not any(attrs.get("id") == parts.fragment for _, attrs, _ in parse(target).elements):
                    failures.append(f"{name}:{line}: missing anchor {value}")

        for tag, attrs, line in page.elements:
            for attribute in ("href", "src"):
                if attribute in attrs:
                    reference(attrs[attribute], line)
            for item in attrs.get("srcset", "").split(","):
                if item.strip():
                    reference(item.strip().split()[0], line)
            for attribute in ("aria-controls", "aria-labelledby", "aria-describedby"):
                if any(value not in ids for value in attrs.get(attribute, "").split()):
                    failures.append(f"{name}:{line}: unresolved {attribute}")
            if attrs.get("target") == "_blank" and "noopener" not in attrs.get("rel", ""):
                failures.append(f"{name}:{line}: unsafe new-tab link")

    contact = parse(ROOT/"contact.html")
    structure = StructureParser()
    structure.feed((ROOT/"contact.html").read_text())
    failures.extend(structure.errors)
    if structure.stack:
        failures.append(f"contact.html: unclosed elements {structure.stack}")
    if sum(tag == "h1" for tag, _, _ in contact.elements) != 1:
        failures.append("contact.html: expected one H1")
    for key in ("description", "viewport"):
        if not any(tag == "meta" and attrs.get("name") == key and attrs.get("content")
                   for tag, attrs, _ in contact.elements):
            failures.append(f"contact.html: missing {key}")
    if any(tag == "form" for tag, _, _ in contact.elements):
        failures.append("contact.html: a contact form is outside scope")

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
            if name in EXISTING:
                prefix = "../" if name.startswith("projects/") else ""
                old = "#contact" if name == "index.html" else prefix+"index.html#contact"
                content = content.decode().replace(f'href="{prefix}contact.html">Контакты', f'href="{old}">Контакты').encode()
            if hashlib.sha256(content).hexdigest() != digest:
                failures.append(f"Unexpected existing-file change: {name}")
        if not failures:
            print("Existing pages and Telegram links preserved; only Contacts navigation changed")

    if failures:
        print("\n".join(failures))
        return 1
    print("PASS: Contact HTML structure, site navigation, nested resources/anchors, ARIA, SEO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
