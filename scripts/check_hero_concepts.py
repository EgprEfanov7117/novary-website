"""Проверить ресурсы и ссылки концептов; опционально — сохранность исходных файлов."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from check_site import PageParser, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, help="JSON: относительные пути и исходные SHA-256")
    args = parser.parse_args()
    failures = []
    parsed = {}

    def read_page(path):
        if path not in parsed:
            document = PageParser()
            document.feed(path.read_text(encoding="utf-8"))
            parsed[path] = document
        return parsed[path]

    original = (ROOT / "index.html").read_text(encoding="utf-8")
    expected_header = re.search(r'<header class="site-header">.*?</header>', original, re.S).group()
    expected_header = re.sub(r'href="#([^"]+)"', r'href="index.html#\1"', expected_header)

    for name in ("hero-a.html", "hero-b.html"):
        path = ROOT / name
        source = path.read_text(encoding="utf-8")
        page = read_page(path)
        ids = Counter(attrs["id"] for _, attrs, _ in page.elements if "id" in attrs)
        if any(count > 1 for count in ids.values()):
            failures.append(f"{name}: duplicate IDs")
        if sum(tag == "h1" for tag, _, _ in page.elements) != 1:
            failures.append(f"{name}: expected one H1")
        header = re.search(r'<header class="site-header">.*?</header>', source, re.S).group()
        if header != expected_header:
            failures.append(f"{name}: header differs from the homepage")
        if 'src="assets/js/main.js"' in source:
            failures.append(f"{name}: must use isolated comparison behavior")

        def reference(value, line):
            parts = urlsplit(value)
            if parts.scheme or parts.netloc:
                return
            target = path.parent / unquote(parts.path) if parts.path else path
            if not target.is_file():
                failures.append(f"{name}:{line}: missing {value}")
            elif parts.fragment and target.suffix == ".html":
                target_ids = {attrs.get("id") for _, attrs, _ in read_page(target).elements}
                if parts.fragment not in target_ids:
                    failures.append(f"{name}:{line}: missing anchor {value}")

        for tag, attrs, line in page.elements:
            for attr in ("src", "href"):
                if attr in attrs:
                    reference(attrs[attr], line)
            for item in attrs.get("srcset", "").split(","):
                if item.strip():
                    reference(item.strip().split()[0], line)
            for attr in ("aria-controls", "aria-labelledby", "aria-describedby"):
                if any(target not in ids for target in attrs.get(attr, "").split()):
                    failures.append(f"{name}:{line}: unresolved {attr}")
            if tag == "img" and any(attr not in attrs for attr in ("alt", "width", "height")):
                failures.append(f"{name}:{line}: image missing accessible or size attributes")
        print(f"Checked {name}: resources, anchors, semantics and shared header")

    # Motion may be defined by the shared component in the main stylesheet.
    css = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("assets/css/styles.css", "assets/css/hero-concepts.css")
    )
    if "transition: all" in css or "prefers-reduced-motion" not in css:
        failures.append("Shared concept stylesheets: motion checks failed")

    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        changed = [name for name, digest in baseline.items()
                   if not (ROOT / name).is_file()
                   or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
        if changed:
            failures.append(f"Existing files changed: {changed}")
        else:
            print(f"Protected existing files unchanged: {len(baseline)} (including index.html)")

    if failures:
        print("\n".join(failures))
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
