"""Воспроизводимая сборка статического NOVARY. Только стандартная библиотека."""
import argparse
from collections import Counter
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import sys
import subprocess
from urllib.robotparser import RobotFileParser
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PAGES = ("index.html", "services.html", "projects.html", "about.html", "contact.html",
         "projects/barber-cult.html", "projects/forma-architects.html")
ASSET_TYPES = {".css", ".js", ".svg", ".ico", ".png", ".webp", ".jpg", ".jpeg", ".avif", ".woff", ".woff2"}
FONT_LICENSES = {
    "assets/fonts/inter-variable.woff": "assets/fonts/OFL-inter.txt",
    "assets/fonts/space-grotesk-variable.woff": "assets/fonts/OFL-space-grotesk.txt",
    "assets/fonts/portfolio-oswald.woff": "assets/fonts/Portfolio-OFL-Oswald.txt",
    "assets/fonts/portfolio-manrope.woff": "assets/fonts/Portfolio-OFL-Manrope.txt",
}
FORBIDDEN = {".git", ".venv", "tests", "scripts", "docs", "previews", "node_modules", "__pycache__", "tmp", "dist"}
# Проверяем только публичные кандидаты. Совпадения никогда не печатаются в лог.
SECRET_PATTERNS = {
    "private key": rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "Telegram token": rb"\b[0-9]{7,12}:[A-Za-z0-9_-]{30,}\b",
    "AWS access key": rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "GitHub token": rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b",
    "API secret": rb"\bsk-(?:proj-|ant-api\d+-)?[A-Za-z0-9_-]{24,}\b",
    "credential assignment": rb"(?i)(?:api[_-]?key|client[_-]?secret|bot[_-]?token|password)\s*[:=]\s*[\"'][A-Za-z0-9_./+:-]{16,}[\"']",
}
CSS_URL = re.compile(r"url\(\s*[\"']?([^\)\"']+)[\"']?\s*\)")
JS_IMPORT = re.compile(r"(?:\bfrom\s*|\bimport\s*(?:\(\s*)?)[\"']([^\"']+)[\"']")


class BuildError(Exception):
    pass


class Page(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, text):
        super().__init__()
        self.elements, self.headings, self.title = [], [], ""
        self.in_head = self.in_title = False
        self.stack = []
        self.feed(text)
        if self.stack:
            raise BuildError("Unclosed HTML elements")

    def handle_starttag(self, tag, attrs):
        if len(attrs) != len(dict(attrs)):
            raise BuildError(f"Duplicate HTML attribute at line {self.getpos()[0]}")
        attrs = dict(attrs)
        if tag not in self.VOID:
            if tag == "a" and "a" in self.stack:
                raise BuildError("Nested links in HTML")
            self.stack.append(tag)
        self.elements.append((tag, attrs, self.getpos()[0]))
        if tag == "head":
            self.in_head = True
        if tag == "title" and self.in_head:
            self.in_title = True
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append(int(tag[1]))

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            raise BuildError(f"Unexpected HTML closing tag at line {self.getpos()[0]}")
        if tag == "title":
            self.in_title = False
        if tag == "head":
            self.in_head = False

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.in_title:
            self.title += data

    def references(self):
        for tag, attrs, _ in self.elements:
            if tag == "a" and "href" in attrs:
                yield attrs["href"], False
            if tag == "link" and attrs.get("rel") in ("stylesheet", "icon", "preload"):
                yield attrs.get("href", ""), True
            if tag in ("script", "img", "source") and "src" in attrs:
                yield attrs["src"], True
            for item in attrs.get("srcset", "").split(","):
                if item.strip():
                    yield item.strip().split()[0], True
            if tag == "meta" and attrs.get("property") == "og:image":
                yield attrs.get("content", ""), True


def normalize_site_url(value):
    if value is None:
        return None
    try:
        parts = urlsplit(value)
        if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
                or parts.query or parts.fragment or parts.port not in (None, 443)
                or any(c.isspace() or ord(c) < 32 for c in value)
                or "\\" in value or any(p in (".", "..") for p in unquote(parts.path).split("/"))):
            raise ValueError
        if parts.hostname in ("localhost", "127.0.0.1", "::1"):
            raise ValueError
        return urlunsplit(("https", parts.netloc, parts.path.rstrip("/") + "/", "", ""))
    except ValueError as error:
        raise BuildError("--site-url must be the real HTTPS site URL, without credentials, query or fragment") from error


def local_reference(root, source, value, site_url=None):
    parts = urlsplit(value)
    if parts.scheme or parts.netloc:
        if parts.username or parts.password:
            raise BuildError(f"Credential-bearing URL in {source.relative_to(root)}")
        if parts.scheme not in ("https", "http") or not parts.netloc:
            raise BuildError(f"Unsupported URL scheme in {source.relative_to(root)}")
        if not site_url or not value.startswith(site_url):
            return None
        value = value[len(site_url):]
        parts = urlsplit(value)
        target = root / unquote(parts.path or "index.html")
    elif not parts.path:
        target = source
    else:
        if "\\" in parts.path or parts.path.startswith("/"):
            raise BuildError(f"Root-relative or invalid path in {source.relative_to(root)}")
        target = source.parent / unquote(parts.path)
    # Не разрешаем даже внутрипроектные symlink: сборка не должна читать секрет по ссылке.
    if target.is_symlink() or any(p.is_symlink() for p in target.parents if p != root.parent):
        raise BuildError(f"Symlink resource in {source.relative_to(root)}")
    target = target.resolve()
    if not target.is_relative_to(root.resolve()):
        raise BuildError(f"Resource escapes project in {source.relative_to(root)}")
    return target, parts.fragment


def scan_public_file(path):
    data = path.read_bytes()
    for label, pattern in SECRET_PATTERNS.items():
        if re.search(pattern, data):
            raise BuildError(f"Possible {label} in public file {path.name}; value redacted")
    for marker in (b"/Users/", b"/home/", b"file://", b"localhost:", b"127.0.0.1:"):
        if marker in data:
            raise BuildError(f"Private/local path in public file {path.name}; value redacted")


def collect_files(root):
    pending, included = list(PAGES), set()
    while pending:
        name = pending.pop()
        if name in included:
            continue
        path = root / name
        if (name not in PAGES and (not name.startswith("assets/") or path.suffix not in ASSET_TYPES)
                or any(part in FORBIDDEN or part.startswith(".") for part in Path(name).parts)):
            raise BuildError(f"Non-public dependency: {name}")
        if not path.is_file() or path.is_symlink():
            raise BuildError(f"Missing or symlink input: {name}")
        scan_public_file(path)
        included.add(name)
        refs = []
        if path.suffix == ".html":
            refs = list(Page(path.read_text()).references())
        elif path.suffix == ".css":
            refs = [(value.strip(), True) for value in CSS_URL.findall(path.read_text())]
        elif path.suffix == ".js":
            refs = [(value, True) for value in JS_IMPORT.findall(path.read_text())]
        for value, resource in refs:
            if value.startswith("data:"):
                continue
            reference = local_reference(root, path, value)
            if reference is None:
                if resource:
                    raise BuildError(f"External runtime dependency in {name}")
                continue
            target, _ = reference
            pending.append(target.relative_to(root).as_posix())
    for font, license_name in FONT_LICENSES.items():
        if font in included:
            license_path = root/license_name
            if not license_path.is_file() or license_path.is_symlink():
                raise BuildError(f"Missing font license: {license_name}")
            scan_public_file(license_path)
            included.add(license_name)
    return included


def render_seo(text, name, site_url):
    if not site_url:
        return text
    canonical = site_url if name == "index.html" else urljoin(site_url, name)
    image = urljoin(site_url, "assets/images/social-preview.png")
    text = re.sub(r'(<meta property="og:image" content=")[^"]+', lambda m: m[1]+escape(image, quote=True), text)
    extra = (f'  <link rel="canonical" href="{escape(canonical, quote=True)}">\n'
             f'  <meta property="og:url" content="{escape(canonical, quote=True)}">\n'
             f'  <meta name="twitter:image" content="{escape(image, quote=True)}">\n')
    return text.replace("</head>", extra+"</head>")


def validate_site(root, site_url=None, expected=None):
    failures, pages, titles, descriptions = [], {}, [], []
    for name in PAGES:
        path = root/name
        if not path.is_file():
            raise BuildError(f"Missing public page: {name}")
        pages[name] = Page(path.read_text())
    for name, page in pages.items():
        path = root/name
        ids = Counter(attrs["id"] for _, attrs, _ in page.elements if "id" in attrs)
        if any(count > 1 for count in ids.values()):
            failures.append(f"{name}: duplicate IDs")
        if page.headings.count(1) != 1 or any(b > a+1 for a, b in zip(page.headings, page.headings[1:])):
            failures.append(f"{name}: invalid heading hierarchy")
        titles.append(page.title.strip())
        description = [attrs.get("content", "") for tag, attrs, _ in page.elements if tag == "meta" and attrs.get("name") == "description"]
        descriptions.extend(description)
        if len(description) != 1 or not description[0]:
            failures.append(f"{name}: missing unique description")
        for tag, attrs, line in page.elements:
            if any(key.lower().startswith("on") for key in attrs):
                failures.append(f"{name}:{line}: inline script handler")
            if tag == "script" and not attrs.get("src"):
                failures.append(f"{name}:{line}: unexpected inline script")
            if tag == "meta" and attrs.get("name") == "robots" and "noindex" in attrs.get("content", "").lower():
                failures.append(f"{name}: noindex on public page")
            if tag == "img" and any(k not in attrs for k in ("alt", "width", "height")):
                failures.append(f"{name}:{line}: image lacks alt or dimensions")
            if attrs.get("target") == "_blank" and not {"noopener", "noreferrer"}.issubset(attrs.get("rel", "").split()):
                failures.append(f"{name}:{line}: unsafe external link")
            for key in ("aria-controls", "aria-labelledby", "aria-describedby"):
                if any(value not in ids for value in attrs.get(key, "").split()):
                    failures.append(f"{name}:{line}: unresolved {key}")
        if site_url:
            canonical = site_url if name == "index.html" else urljoin(site_url, name)
            actual_canonical = [attrs.get("href") for tag, attrs, _ in page.elements if tag == "link" and attrs.get("rel") == "canonical"]
            actual_og_url = [attrs.get("content") for tag, attrs, _ in page.elements if tag == "meta" and attrs.get("property") == "og:url"]
            if actual_canonical != [canonical] or actual_og_url != [canonical]:
                failures.append(f"{name}: incorrect canonical or og:url")
        for value, _ in page.references():
            ref = local_reference(root, path, value, site_url)
            if ref is None:
                continue
            target, fragment = ref
            if not target.is_file():
                failures.append(f"{name}: missing local reference")
            elif fragment and target.suffix == ".html":
                target_page = pages.get(target.relative_to(root).as_posix())
                if not target_page or fragment not in {a.get("id") for _, a, _ in target_page.elements}:
                    failures.append(f"{name}: missing local anchor")
    if len(set(titles)) != len(PAGES) or not all(titles):
        failures.append("Titles must be nonempty and unique")
    if len(set(descriptions)) != len(PAGES):
        failures.append("Descriptions must be unique")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if expected is not None and actual != set(expected):
        raise BuildError("Public build contains missing or unexpected files")
    for name in actual:
        path = root/name
        if path.is_symlink() or any(part in FORBIDDEN or part.startswith(".") for part in Path(name).parts):
            failures.append(f"Forbidden public file: {name}")
            continue
        scan_public_file(path)
        refs = CSS_URL.findall(path.read_text()) if path.suffix == ".css" else JS_IMPORT.findall(path.read_text()) if path.suffix == ".js" else []
        for value in refs:
            ref = local_reference(root, path, value.strip(), site_url)
            if ref is None or not ref[0].is_file():
                failures.append(f"{name}: missing CSS/JS dependency")
    if not site_url and ((root/"sitemap.xml").exists() or any('rel="canonical"' in (root/name).read_text() or 'property="og:url"' in (root/name).read_text() for name in PAGES)):
        failures.append("Domain-specific metadata present without --site-url")
    if site_url:
        sitemap = root/"sitemap.xml"
        locs = [e.text for e in ET.parse(sitemap).getroot().iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        if set(locs) != {site_url if n == "index.html" else urljoin(site_url, n) for n in PAGES}:
            failures.append("Sitemap does not match public routes")
    robots = RobotFileParser()
    robots.parse((root/"robots.txt").read_text().splitlines())
    if any(not robots.can_fetch("*", (site_url or "https://validation.test/")+name) for name in PAGES):
        failures.append("robots.txt blocks public pages")
    node = shutil.which("node")
    if node:
        for name in actual:
            if name.endswith(".js"):
                # Явный ESM-режим не зависит от package.json и autodetect версии Node.
                syntax = subprocess.run([node, "--input-type=module", "--check"], input=(root/name).read_bytes(), capture_output=True)
                if syntax.returncode:
                    failures.append(f"{name}: JavaScript syntax error (run node --check locally)")
    if failures:
        raise BuildError("\n".join(failures))
    return {"pages": len(pages), "files": len(actual), "bytes": sum((root/n).stat().st_size for n in actual)}


def build(root=ROOT, site_url=None):
    root = root.resolve()
    site_url = normalize_site_url(site_url)
    dist = root/"dist"
    if dist.is_symlink() or (dist.exists() and not dist.is_dir()):
        raise BuildError("Refusing to clean a symlink or non-directory dist")
    files = collect_files(root)
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir()
    try:
        for name in sorted(files):
            target = dist/name
            target.parent.mkdir(parents=True, exist_ok=True)
            if name in PAGES:
                target.write_text(render_seo((root/name).read_text(), name, site_url), encoding="utf-8")
            else:
                shutil.copyfile(root/name, target)
        robots = (root/"robots.txt").read_text()
        if site_url:
            robots += f"\nSitemap: {urljoin(site_url, 'sitemap.xml')}\n"
            ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
            sitemap = ET.Element("{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")
            for name in PAGES:
                node = ET.SubElement(sitemap, "{http://www.sitemaps.org/schemas/sitemap/0.9}url")
                ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text = site_url if name == "index.html" else urljoin(site_url, name)
            ET.indent(sitemap)
            ET.ElementTree(sitemap).write(dist/"sitemap.xml", encoding="utf-8", xml_declaration=True)
        (dist/"robots.txt").write_text(robots, encoding="utf-8")
        expected = files | {"robots.txt"} | ({"sitemap.xml"} if site_url else set())
        return validate_site(dist, site_url, expected)
    except Exception:
        shutil.rmtree(dist)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", help="Настоящий публичный HTTPS URL; можно с базовым путём")
    parser.add_argument("--check", action="store_true", help="Проверить существующую dist без перезаписи")
    args = parser.parse_args()
    try:
        site_url = normalize_site_url(args.site_url)
        expected = collect_files(ROOT) | {"robots.txt"} | ({"sitemap.xml"} if site_url else set())
        result = validate_site(ROOT/"dist", site_url, expected) if args.check else build(ROOT, site_url)
        print(f"PASS: {result['pages']} pages, {result['files']} public files, {result['bytes']} bytes")
        if not site_url:
            print("Public domain unspecified: sitemap/canonical/og:url omitted; set --site-url before launch.")
        return 0
    except (BuildError, OSError, ET.ParseError) as error:
        print(f"BUILD FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
