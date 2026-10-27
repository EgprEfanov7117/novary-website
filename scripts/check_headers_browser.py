"""Локальный Chromium-тест эквивалентных HTTP-заголовков, не тест Cloudflare CDN.

Dev-инструмент использует уже доступный Playwright. Сервер специально добавляет
заголовки из используемого подмножества _headers: обычный http.server их не читает.
"""
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

from build import ROOT, PAGES, read_header_rules, headers_for_path


def main():
    rules = read_header_rules(ROOT/"dist/_headers")
    results = {"scope": "Local equivalent response headers; not Cloudflare edge/cache verification",
               "checks": [], "console_errors": [], "csp_violations": []}

    class Handler(SimpleHTTPRequestHandler):
        def end_headers(self):
            for name, value in headers_for_path(rules, urlsplit(self.path).path).items():
                self.send_header(name, value)
            super().end_headers()

        def log_message(self, *args):
            pass

    def check(name, passed, details=None):
        results["checks"].append({"name": name, "passed": bool(passed), "details": details})

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ROOT/"dist")))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(bypass_csp=False, reduced_motion="reduce")
            context.add_init_script('''window.__cspViolations=[];document.addEventListener('securitypolicyviolation',e=>window.__cspViolations.push({directive:e.effectiveDirective,blocked:e.blockedURI}));''')
            context.route("https://t.me/**", lambda route: route.fulfill(status=200, content_type="text/html", body="<title>Local Telegram navigation test</title>"))
            context.route("https://egprefanov7117.github.io/**", lambda route: route.fulfill(status=200, content_type="text/html", body="<title>Local external navigation test</title>"))
            page = context.new_page()
            page.on("pageerror", lambda error: results["console_errors"].append(str(error)))
            page.on("console", lambda msg: results["console_errors"].append(msg.text) if msg.type == "error" else None)
            for name in PAGES:
                page.set_viewport_size({"width": 1440, "height": 1000})
                response = page.goto(base+name, wait_until="networkidle")
                check(name+" receives equivalent CSP", response.headers.get("content-security-policy") == headers_for_path(rules, "/"+name)["content-security-policy"])
                check(name+" styles loaded", page.evaluate('getComputedStyle(document.body).backgroundColor==="rgb(11, 13, 12)"'))
                check(name+" module and menu initialization", page.evaluate('document.documentElement.classList.contains("js")'))
                page.locator("img").evaluate_all('items=>items.forEach(i=>i.loading="eager")')
                page.evaluate("Promise.all(Array.from(document.images).map(i=>i.decode()))")
                check(name+" images decoded", page.locator("img").evaluate_all("images=>images.every(i=>i.complete&&i.naturalWidth>0)"))
                page.evaluate("document.fonts.ready")
                check(name+" local fonts ready", page.evaluate("""document.fonts.check('500 16px Inter') && document.fonts.check('500 16px "Space Grotesk"')"""))
                for sample in page.locator(".color-sample").all():
                    check(name+" inline palette color applies", sample.evaluate('e=>{const h=e.style.getPropertyValue("--sample").trim().slice(1);return getComputedStyle(e).backgroundColor===`rgb(${parseInt(h.slice(0,2),16)}, ${parseInt(h.slice(2,4),16)}, ${parseInt(h.slice(4,6),16)})`}'))
                for link in page.locator("[data-telegram-link]").all():
                    with page.expect_popup() as event:
                        link.click()
                    popup = event.value
                    popup.wait_for_load_state()
                    check(name+" Telegram navigation allowed", popup.url == "https://t.me/novary_studio_bot")
                    popup.close()
                for link in page.locator('a[target="_blank"][href^="https://egprefanov7117.github.io/"]').all():
                    with page.expect_popup() as event:
                        link.click()
                    popup = event.value
                    popup.wait_for_load_state()
                    check(name+" external project navigation allowed", popup.url.startswith("https://egprefanov7117.github.io/"))
                    popup.close()
                for detail in page.locator("details").all():
                    original = detail.evaluate("e=>e.open")
                    detail.locator("summary").click()
                    check(name+" FAQ click", detail.evaluate("e=>e.open") != original)
                    detail.locator("summary").focus()
                    page.keyboard.press("Enter")
                    check(name+" FAQ keyboard", detail.evaluate("e=>e.open") == original)
                permissions = page.evaluate('''() => document.featurePolicy ? ["camera","microphone","geolocation"].map(name=>({name,allowed:document.featurePolicy.allowsFeature(name)})) : null''')
                check(name+" unused permissions denied", permissions is not None and all(not item["allowed"] for item in permissions), permissions)
                page.set_viewport_size({"width": 390, "height": 844})
                page.locator(".menu-trigger").click()
                check(name+" mobile dialog opens", page.locator("#mobile-menu").evaluate("e=>e.open"))
                page.keyboard.press("Escape")
                check(name+" mobile menu restores focus", not page.locator("#mobile-menu").evaluate("e=>e.open") and page.locator(".menu-trigger").evaluate("e=>e===document.activeElement"))
                violations = page.evaluate("window.__cspViolations")
                results["csp_violations"].extend({"page": name, **item} for item in violations)
                check(name+" no CSP violations", not violations)
            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    results["summary"] = {"passed": sum(c["passed"] for c in results["checks"]),
                          "failed": sum(not c["passed"] for c in results["checks"]),
                          "console_errors": len(results["console_errors"]), "csp_violations": len(results["csp_violations"])}
    (ROOT/"docs/cloudflare-headers-browser.json").write_text(json.dumps(results, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(results["summary"]))
    for item in results["checks"]:
        if not item["passed"]:
            print(json.dumps(item, ensure_ascii=False))
    for error in results["console_errors"]:
        print(error)
    return int(bool(results["summary"]["failed"] or results["console_errors"] or results["csp_violations"]))


if __name__ == "__main__":
    raise SystemExit(main())
