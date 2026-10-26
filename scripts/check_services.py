"""Проверки страницы услуг и связей между статическими страницами."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from check_site import PageParser, ROOT


def main():
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--baseline", type=Path, help="Необязательный снимок SHA-256 до изменения")
    arguments.add_argument("--allow-changed", action="append", default=[], help="Допустимое изменение при сравнении со снимком")
    args = arguments.parse_args()
    failures = []
    cache = {}

    def parse(path):
        if path not in cache:
            document = PageParser()
            document.feed(path.read_text(encoding="utf-8"))
            cache[path] = document
        return cache[path]

    path = ROOT / "services.html"
    document = parse(path)
    ids = Counter(attrs["id"] for _, attrs, _ in document.elements if "id" in attrs)
    if any(count > 1 for count in ids.values()):
        failures.append("services.html: duplicate IDs")
    if sum(tag == "h1" for tag, _, _ in document.elements) != 1:
        failures.append("services.html: expected one H1")
    for name in ("description", "viewport"):
        if not any(tag == "meta" and attrs.get("name") == name and attrs.get("content")
                   for tag, attrs, _ in document.elements):
            failures.append(f"services.html: missing {name}")

    for tag, attrs, line in document.elements:
        for attribute in ("href", "src"):
            if attribute not in attrs:
                continue
            parts = urlsplit(attrs[attribute])
            if parts.scheme or parts.netloc:
                continue
            target = ROOT / unquote(parts.path) if parts.path else path
            if not target.is_file():
                failures.append(f"services.html:{line}: missing {attrs[attribute]}")
            elif parts.fragment and target.suffix == ".html":
                target_ids = {attrs.get("id") for _, attrs, _ in parse(target).elements}
                if parts.fragment not in target_ids:
                    failures.append(f"services.html:{line}: missing anchor {attrs[attribute]}")
        for attribute in ("aria-controls", "aria-labelledby", "aria-describedby"):
            if any(name not in ids for name in attrs.get(attribute, "").split()):
                failures.append(f"services.html:{line}: unresolved {attribute}")
        if tag == "img" and any(name not in attrs for name in ("alt", "width", "height")):
            failures.append(f"services.html:{line}: missing image attributes")

    css = (ROOT / "assets/css/services.css").read_text(encoding="utf-8")
    if "transition: all" in css or "prefers-reduced-motion" not in css:
        failures.append("services.css: motion checks failed")

    if args.baseline:
        manifest = json.loads(args.baseline.read_text(encoding="utf-8"))
        routes = {"index.html": "#services", "hero-a.html": "index.html#services", "hero-b.html": "index.html#services"}
        for name, digest in manifest.items():
            if name in args.allow_changed:
                continue
            current = (ROOT / name).read_bytes()
            if name in routes:
                current = current.decode("utf-8").replace(
                    'href="services.html">Услуги', f'href="{routes[name]}">Услуги'
                ).encode("utf-8")
            if hashlib.sha256(current).hexdigest() != digest:
                failures.append(f"Unexpected existing-file change: {name}")
        if not failures:
            print("Other existing files preserved; HTML changes limited to Services navigation")

    if failures:
        print("\n".join(failures))
        return 1
    print("PASS: services resources, cross-page anchors, IDs, ARIA and metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
