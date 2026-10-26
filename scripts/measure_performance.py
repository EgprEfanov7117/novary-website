"""Локальные замеры Chromium; не Lighthouse и не полевые Core Web Vitals."""
import argparse
import json
from pathlib import Path
from statistics import median
from playwright.sync_api import sync_playwright

from build import PAGES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8002/")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    result = {"conditions": {"engine": "Chromium", "viewport": "390x844", "device_scale_factor": 1,
              "latency_ms": 150, "download_bytes_per_second": 200000, "upload_bytes_per_second": 93750,
              "cpu_slowdown": 4, "cache": "disabled", "runs": args.runs,
              "scope": "localhost, cold initial viewport; not field data or Lighthouse scores"}, "pages": []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        result["conditions"]["browser_version"] = browser.version
        for name in PAGES:
            runs = []
            for _ in range(args.runs):
                context = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1)
                context.add_init_script('''window.__measure={lcp:0,cls:0};let windowStart=0,lastShift=0,windowScore=0;
                  new PerformanceObserver(list=>{for(const e of list.getEntries())window.__measure.lcp=e.startTime}).observe({type:'largest-contentful-paint',buffered:true});
                  new PerformanceObserver(list=>{for(const e of list.getEntries()){if(e.hadRecentInput)continue;
                    if(e.startTime-lastShift<1000&&e.startTime-windowStart<5000)windowScore+=e.value;
                    else{windowStart=e.startTime;windowScore=e.value}lastShift=e.startTime;
                    window.__measure.cls=Math.max(window.__measure.cls,windowScore);
                  }}).observe({type:'layout-shift',buffered:true});''')
                page = context.new_page()
                cdp = context.new_cdp_session(page)
                cdp.send("Network.enable")
                cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
                cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 150,
                         "downloadThroughput": 200000, "uploadThroughput": 93750})
                cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
                page.goto(args.base_url.rstrip("/")+"/"+name, wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(1000)
                data = page.evaluate('''() => {const n=performance.getEntriesByType('navigation')[0],r=performance.getEntriesByType('resource');return {
                  lcp_ms:window.__measure.lcp,cls:window.__measure.cls,dom_content_loaded_ms:n.domContentLoadedEventEnd,
                  load_ms:n.loadEventEnd,initial_resource_requests:r.length,
                  transferred_bytes:n.transferSize+r.reduce((s,e)=>s+e.transferSize,0),
                  decoded_body_bytes:n.decodedBodySize+r.reduce((s,e)=>s+e.decodedBodySize,0)}}''')
                runs.append(data)
                context.close()
            result["pages"].append({"page": name, "runs": runs,
                "median_lcp_ms": round(median(r["lcp_ms"] for r in runs), 1),
                "max_initial_cls": round(max(r["cls"] for r in runs), 6),
                "median_transferred_bytes": round(median(r["transferred_bytes"] for r in runs))})
            print(name, "measured", flush=True)
        browser.close()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps([{k: v for k, v in row.items() if k != "runs"} for row in result["pages"]], ensure_ascii=False))


if __name__ == "__main__":
    main()
