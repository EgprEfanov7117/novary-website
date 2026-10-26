"""Регрессия семи публичных страниц в Chromium (нужен dev-пакет Playwright)."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PAGES = ("index.html", "services.html", "projects.html", "about.html", "contact.html",
         "projects/barber-cult.html", "projects/forma-architects.html")
WIDTHS = (320, 375, 390, 768, 1024, 1440, 1920)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--captures", type=Path, required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/") + "/"
    args.captures.mkdir(parents=True, exist_ok=True)
    result = {"base_url": base, "checks": [], "errors": [], "captures": [], "text_contrast": [], "targets": []}

    def check(name, ok, details=None):
        result["checks"].append({"name": name, "passed": bool(ok), "details": details})

    def reflow(page, label):
        data = page.evaluate('''() => ({viewport:document.documentElement.clientWidth,
          width:Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)})''')
        check(label, data["width"] <= data["viewport"], data)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(reduced_motion="reduce")
        context.route("https://t.me/**", lambda route: route.fulfill(status=200, content_type="text/html", body="<title>Local CTA check</title>"))
        context.route("https://egprefanov7117.github.io/**", lambda route: route.fulfill(status=200, content_type="text/html", body="<title>Local external-link check</title>"))
        page = context.new_page()
        page.on("pageerror", lambda error: result["errors"].append(str(error)))
        page.on("console", lambda message: result["errors"].append(message.text) if message.type == "error" else None)
        page.on("response", lambda response: result["errors"].append(f"{response.status} {response.url}") if response.status >= 400 else None)
        for name in PAGES:
            for width in WIDTHS:
                page.set_viewport_size({"width": width, "height": 900})
                page.goto(base + name, wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                reflow(page, f"{name} {width}px reflow")
                check(f"{name} {width}px menu", page.locator(".menu-trigger").is_visible() == (width < 1200))
            for width in (320, 390, 768, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                page.goto(base + name, wait_until="networkidle")
                page.evaluate('document.documentElement.style.fontSize="200%"')
                reflow(page, f"{name} {width}px 200% text")
                text_overflow = page.evaluate('''() => Array.from(document.querySelectorAll('h1,h2,h3,p,dd,.color-value')).filter(e=>{
                  if(!e.getClientRects().length) return false;
                  const r=document.createRange();r.selectNodeContents(e);const t=r.getBoundingClientRect(), b=e.getBoundingClientRect();
                  return t.right>b.right+3 || t.left<b.left-3;
                }).map(e=>({tag:e.tagName,class:e.className,text:e.textContent.slice(0,65)}))''')
                check(f"{name} {width}px 200% text stays in container", not text_overflow, text_overflow)
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(base + name, wait_until="networkidle")
            check(name + " skip hidden initially", page.locator(".skip-link").evaluate("e=>e.getBoundingClientRect().bottom<=0"))
            keyboard = context.new_page()
            keyboard.goto(base + name, wait_until="networkidle")
            keyboard.keyboard.press("Tab")
            check(name + " first Tab shows skip", keyboard.locator(".skip-link").evaluate("e=>e===document.activeElement && e.getBoundingClientRect().top>=0"))
            keyboard.keyboard.press("Enter")
            check(name + " skip focuses main", keyboard.evaluate('document.activeElement.id==="main"'))
            keyboard.close()
            page.locator(".menu-trigger").click()
            check(name + " menu opens and focuses close", page.locator("#mobile-menu").evaluate("e=>e.open") and page.locator(".menu-close").evaluate("e=>e===document.activeElement"))
            page.keyboard.press("Shift+Tab")
            check(name + " menu focus containment", page.evaluate('document.activeElement.closest("#mobile-menu")!==null'))
            page.keyboard.press("Escape")
            check(name + " Escape restores focus", not page.locator("#mobile-menu").evaluate("e=>e.open") and page.locator(".menu-trigger").evaluate("e=>e===document.activeElement"))
            page.locator(".menu-trigger").click()
            page.locator("#mobile-menu a.button").click()
            check(name + " menu CTA closes and focuses section", not page.locator("#mobile-menu").evaluate("e=>e.open") and page.evaluate('document.activeElement.id==="contact"'))
            check(name + " shared Telegram URL", page.locator("[data-telegram-link]").evaluate_all('links=>links.length>0&&links.every(a=>a.href==="https://t.me/novary_studio_bot"&&a.target==="_blank"&&a.rel.includes("noopener")&&a.rel.includes("noreferrer"))'))
            for link in page.locator("[data-telegram-link]").all():
                with page.expect_popup() as popup:
                    link.click()
                popup.value.wait_for_load_state()
                check(name + " Telegram CTA popup", popup.value.url == "https://t.me/novary_studio_bot")
                popup.value.close()
            for detail in page.locator("details").all():
                original = detail.evaluate("e=>e.open")
                detail.locator("summary").click()
                check(name + " FAQ pointer toggles", detail.evaluate("e=>e.open") != original)
                detail.locator("summary").focus()
                page.keyboard.press("Space")
                check(name + " FAQ Space toggles", detail.evaluate("e=>e.open") == original)
            page.locator("details").evaluate_all("items=>items.forEach(e=>e.open=true)")
            reflow(page, name + " all FAQ expanded")
            # Реальные вычисленные цвета, включая светлый образец шрифта FORMA.
            contrast = page.evaluate(r'''() => {
              const rgb=s=>(s.match(/[\d.]+/g)||[]).map(Number), lum=c=>{const a=c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4});return .2126*a[0]+.7152*a[1]+.0722*a[2]};
              const out=[], walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
              while(walker.nextNode()){const n=walker.currentNode,e=n.parentElement;if(!n.textContent.trim()||!e||e.closest('svg,script,style,dialog:not([open])')||!e.getClientRects().length)continue;
                const s=getComputedStyle(e);if(s.visibility==='hidden'||s.display==='none')continue;
                let a=e,bg;while(a){bg=rgb(getComputedStyle(a).backgroundColor);if(bg.length<4||bg[3]===1)break;a=a.parentElement}
                if(!a)bg=[11,13,12];const fg=rgb(s.color), l1=lum(fg),l2=lum(bg),ratio=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);
                const large=parseFloat(s.fontSize)>=24||(parseFloat(s.fontSize)>=18.67&&parseInt(s.fontWeight)>=700),min=large?3:4.5;
                if(ratio<min-.01)out.push({text:n.textContent.trim().slice(0,65),ratio,minimum:min,color:s.color,background:bg});
              }return out;
            }''')
            check(name + " computed text contrast", not contrast, contrast)
            result["text_contrast"].append({"page": name, "failures": contrast})
            targets = page.locator("a,button,summary").evaluate_all('''items=>items.filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.height&&!e.closest('dialog:not([open])')&&getComputedStyle(e).visibility!=='hidden'&&(r.width<44||r.height<44)}).map(e=>({tag:e.tagName,text:e.textContent.trim().slice(0,65),width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}))''')
            result["targets"].append({"page": name, "under_44px": targets})
            for label, target in (("Услуги", "services.html"), ("Проекты", "projects.html"), ("О студии", "about.html"), ("Контакты", "contact.html")):
                page.goto(base + name, wait_until="networkidle")
                page.locator(".menu-trigger").click()
                page.locator("#mobile-menu nav a").filter(has_text=label).click()
                check(name + " mobile nav " + label, page.url == base + target)
            for width, height, label in ((1440, 1000, "desktop"), (390, 844, "mobile")):
                page.set_viewport_size({"width": width, "height": height})
                page.goto(base + name, wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                page.locator("img").evaluate_all('items=>items.forEach(e=>e.loading="eager")')
                page.evaluate("Promise.all(Array.from(document.images).map(e=>e.decode()))")
                for img in page.locator("img").all():
                    img.scroll_into_view_if_needed()
                    page.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
                page.mouse.move(0, 0)
                page.evaluate("window.scrollTo(0,0)")
                path = args.captures / (name.replace("/", "-").replace(".html", "") + "-" + label + ".png")
                page.screenshot(path=str(path), full_page=True, animations="disabled")
                result["captures"].append(str(path))
            check(name + " reduced motion", page.evaluate("Array.from(document.getAnimations()).every(a=>a.playState!=='running')"))
        context.close()
        no_js = browser.new_context(java_script_enabled=False, viewport={"width": 320, "height": 844})
        page = no_js.new_page()
        for name in PAGES:
            page.goto(base + name)
            check(name + " no-JS navigation", page.locator(".desktop-nav").is_visible())
            reflow(page, name + " no-JS reflow")
        no_js.close()
        # Синтезированное touch-взаимодействие, а не только эмуляция ширины.
        touch = browser.new_context(has_touch=True, is_mobile=True, viewport={"width": 390, "height": 844}, reduced_motion="reduce")
        page = touch.new_page()
        for name in PAGES:
            page.goto(base + name, wait_until="networkidle")
            page.locator(".menu-trigger").tap()
            check(name + " touch opens menu", page.locator("#mobile-menu").evaluate("e=>e.open"))
            page.locator(".menu-close").tap()
            check(name + " touch closes menu", not page.locator("#mobile-menu").evaluate("e=>e.open"))
        touch.close()
        browser.close()
    result["summary"] = {"passed": sum(c["passed"] for c in result["checks"]), "failed": sum(not c["passed"] for c in result["checks"]), "errors": len(result["errors"])}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result["summary"]))
    for item in result["checks"]:
        if not item["passed"]:
            print(json.dumps(item, ensure_ascii=False))
    for error in result["errors"]:
        print(error)
    return int(result["summary"]["failed"] > 0 or bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
