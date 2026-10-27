"""Изолированные проверки production-сборки. Никакие реальные секреты не читаются."""
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from build import (ROOT, PAGES, FONT_LICENSES, BuildError, build, collect_files,
                   normalize_site_url, validate_site, parse_header_rules, headers_for_path)


class ProductionBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="novary-build-test-")
        self.root = Path(self.temporary.name).resolve()
        for name in PAGES:
            target = self.root/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, target)
        shutil.copytree(ROOT/"assets", self.root/"assets")
        shutil.copyfile(ROOT/"robots.txt", self.root/"robots.txt")
        shutil.copyfile(ROOT/"_headers", self.root/"_headers")

    def tearDown(self):
        self.temporary.cleanup()

    def test_allowlist_clean_and_deterministic(self):
        # Эти синтетические внутренние файлы не должны попасть в dist.
        for name in (".env", "docs/private.md", "scripts/private.py", "tests/private.py", "previews/image.png", "node_modules/private.js", "hero-a.html", "hero-b.html"):
            path = self.root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("test fixture, not public")
        (self.root/"dist").mkdir()
        (self.root/"dist/stale.txt").write_text("stale build")
        result = build(self.root)
        self.assertEqual(result["pages"], 7)
        self.assertFalse((self.root/"dist/sitemap.xml").exists())
        self.assertFalse((self.root/"dist/stale.txt").exists())
        self.assertFalse((self.root/"dist/.env").exists())
        self.assertFalse((self.root/"dist/docs").exists())
        self.assertFalse((self.root/"dist/assets/css/hero-concepts.css").exists())
        for license_name in FONT_LICENSES.values():
            self.assertTrue((self.root/"dist"/license_name).is_file())
        def digests():
            return {p.relative_to(self.root/"dist").as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (self.root/"dist").rglob("*") if p.is_file()}
        first = digests()
        build(self.root)
        self.assertEqual(first, digests())
        for name in PAGES:
            self.assertEqual((self.root/name).read_bytes(), (self.root/"dist"/name).read_bytes())

    def test_domain_metadata_and_subpath_use_test_fixture_only(self):
        # Зарезервированный тестовый адрес существует только в удаляемой temp-папке.
        url = "https://site.test/studio/"
        build(self.root, url)
        page = (self.root/"dist/projects/barber-cult.html").read_text()
        self.assertIn('rel="canonical" href="https://site.test/studio/projects/barber-cult.html"', page)
        self.assertIn('content="https://site.test/studio/assets/images/social-preview.png"', page)
        self.assertIn("Sitemap: https://site.test/studio/sitemap.xml", (self.root/"dist/robots.txt").read_text())
        self.assertEqual((self.root/"dist/sitemap.xml").read_text().count("<loc>"), 7)
        build(self.root)
        self.assertNotIn("site.test", (self.root/"dist/index.html").read_text())
        self.assertFalse((self.root/"dist/sitemap.xml").exists())

    def test_missing_module_fails(self):
        (self.root/"assets/js/config.js").unlink()
        with self.assertRaises(BuildError):
            build(self.root)

    def test_broken_anchor_fails_and_removes_partial_build(self):
        path = self.root/"index.html"
        path.write_text(path.read_text().replace('href="#projects"', 'href="#missing-anchor"'))
        with self.assertRaises(BuildError):
            build(self.root)
        self.assertFalse((self.root/"dist").exists())

    def test_internal_dependency_cannot_be_published(self):
        path = self.root/"index.html"
        path.write_text(path.read_text().replace('href="#projects"', 'href=".env"'))
        (self.root/".env").write_text("private fixture")
        with self.assertRaises(BuildError):
            build(self.root)

    def test_symlink_input_and_output_rejected(self):
        source = self.root/"assets/js/config.js"
        fixture = self.root/"private.txt"
        fixture.write_text("private fixture")
        source.unlink()
        source.symlink_to(fixture)
        with self.assertRaises(BuildError):
            build(self.root)
        source.unlink()
        shutil.copyfile(ROOT/"assets/js/config.js", source)
        (self.root/"dist").symlink_to(self.root/"assets", target_is_directory=True)
        with self.assertRaises(BuildError):
            build(self.root)
        self.assertTrue(source.exists())

    def test_secret_detection_redacts_value(self):
        token = "123456789:" + "x" * 35
        with (self.root/"assets/js/config.js").open("a") as stream:
            stream.write("\n// " + token)
        with self.assertRaises(BuildError) as error:
            build(self.root)
        self.assertNotIn(token, str(error.exception))

    def test_unexpected_file_rejected_by_final_validation(self):
        build(self.root)
        (self.root/"dist/private.txt").write_text("private fixture")
        with self.assertRaises(BuildError):
            validate_site(self.root/"dist", expected=collect_files(self.root) | {"robots.txt", "_headers"})

    def test_duplicate_title_fails(self):
        path = self.root/"about.html"
        import re
        title = re.search(r"<title>(.*?)</title>", (self.root/"index.html").read_text()).group(1)
        path.write_text(re.sub(r"<title>.*?</title>", "<title>"+title+"</title>", path.read_text()))
        with self.assertRaises(BuildError):
            build(self.root)

    def test_domain_validation_does_not_echo_credentials(self):
        for value in ("http://site.test", "https://user:password@site.test", "https://site.test/?x=1", "https://site.test/#hash", "https://localhost/", "https://site.test/../private"):
            with self.assertRaises(BuildError) as error:
                normalize_site_url(value)
            self.assertNotIn("password", str(error.exception))

    def test_blocked_indexing_is_a_build_failure(self):
        (self.root/"robots.txt").write_text("User-agent: *\nDisallow: /\n")
        with self.assertRaises(BuildError):
            build(self.root)

    def test_invalid_javascript_is_a_build_failure_when_node_available(self):
        if not shutil.which("node"):
            self.skipTest("Node syntax checker unavailable")
        (self.root/"assets/js/config.js").write_text("export const = ;")
        with self.assertRaises(BuildError):
            build(self.root)

    def test_active_link_scheme_is_rejected(self):
        path = self.root/"index.html"
        path.write_text(path.read_text().replace('href="#projects"', 'href="javascript:alert(1)"'))
        with self.assertRaises(BuildError):
            build(self.root)

    def test_missing_css_asset_is_a_build_failure(self):
        path = self.root/"assets/css/styles.css"
        path.write_text(path.read_text().replace('inter-variable.woff', 'missing-font.woff'))
        with self.assertRaises(BuildError):
            build(self.root)

    def test_headers_are_copied_exactly_and_reproducibly(self):
        build(self.root)
        expected = (self.root/"_headers").read_bytes()
        self.assertEqual((self.root/"dist/_headers").read_bytes(), expected)
        build(self.root)
        self.assertEqual((self.root/"dist/_headers").read_bytes(), expected)
        build(self.root, "https://site.test/")
        self.assertEqual((self.root/"dist/_headers").read_bytes(), expected)

    def test_headers_syntax_limits_and_malformed_input(self):
        rules = parse_header_rules((self.root/"_headers").read_text())
        self.assertLessEqual(len(rules), 100)
        for text in ("  X-Test: orphan", "/\n  Missing-Colon", "/\n  X-Test:\n",
                     "/**\n  X-Test: value", "/\n  X-Test: first\n  x-test: second",
                     "/\n  X-Test: " + "x" * 2000,
                     "\n".join(f"/path{i}\n  X-Test: value" for i in range(101))):
            with self.subTest(text=text[:50]), self.assertRaises(BuildError):
                parse_header_rules(text)

    def test_document_and_asset_cache_paths_do_not_merge_conflicting_values(self):
        rules = parse_header_rules((self.root/"_headers").read_text())
        documents = ["/", "/index"] + ["/"+name for name in PAGES] + ["/"+name.removesuffix(".html") for name in PAGES if name != "index.html"]
        paths = {path: 0 for path in documents + ["/robots.txt", "/sitemap.xml", "/assets/css/styles.css", "/assets/js/main.js", "/assets/js/config.js"]}
        paths.update({"/assets/images/social-preview.png": 3600, "/assets/images/projects/barber-cult-about-640.webp": 3600,
                      "/assets/fonts/inter-variable.woff": 86400, "/assets/favicon.svg": 3600})
        for path, age in paths.items():
            with self.subTest(path=path):
                headers = headers_for_path(rules, path)
                self.assertEqual(headers["cache-control"], f"public, max-age={age}, must-revalidate")
                self.assertNotIn("immutable", headers["cache-control"])
                self.assertEqual(headers["x-content-type-options"], "nosniff")
                self.assertEqual(headers["referrer-policy"], "strict-origin-when-cross-origin")
        self.assertNotIn("cache-control", headers_for_path(rules, "/assets/css-file.css"))
        self.assertNotIn("cache-control", headers_for_path(rules, "/services-extra"))

    def test_csp_matches_real_resources_and_does_not_allow_eval(self):
        rules = parse_header_rules((self.root/"_headers").read_text())
        for path in ("/", "/services", "/projects/barber-cult", "/assets/js/main.js"):
            headers = headers_for_path(rules, path)
            csp = dict((parts[0], parts[1:]) for piece in headers["content-security-policy"].split(";") if (parts := piece.split()))
            self.assertEqual(csp["script-src"], ["'self'"])
            self.assertEqual(csp["script-src-attr"], ["'none'"])
            self.assertEqual(csp["style-src-elem"], ["'self'"])
            self.assertEqual(csp["style-src-attr"], ["'unsafe-inline'"])
            self.assertEqual(csp["img-src"], ["'self'"])
            self.assertEqual(csp["font-src"], ["'self'"])
            self.assertEqual(csp["connect-src"], ["'none'"])
            self.assertNotIn("unsafe-eval", headers["content-security-policy"])
            self.assertNotIn("https:", headers["content-security-policy"])
            self.assertEqual(headers["permissions-policy"], "camera=(), microphone=(), geolocation=()")

    def test_headers_missing_symlink_and_secret_are_rejected(self):
        path = self.root/"_headers"
        path.unlink()
        with self.assertRaises(BuildError):
            build(self.root)
        path.symlink_to(ROOT/"_headers")
        with self.assertRaises(BuildError):
            build(self.root)
        path.unlink()
        token = "123456789:" + "x" * 35
        path.write_text("/*\n  X-Test: " + token)
        with self.assertRaises(BuildError) as error:
            build(self.root)
        self.assertNotIn(token, str(error.exception))

    def test_multiple_matching_headers_follow_documented_comma_join(self):
        rules = parse_header_rules("/*\n  X-Test: a\n/assets/*\n  X-Test: b\n")
        self.assertEqual(headers_for_path(rules, "/assets/main.js")["x-test"], "a, b")


if __name__ == "__main__":
    unittest.main()
