#!/usr/bin/env python3
import os
import re
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()   # loads GROQ_API_KEY (and anything else) from .env into os.environ

# ── Selenium ──────────────────────────────────────────────────────────────────
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from utils.build_report import build_rates_table

# ── HTML parsing ──────────────────────────────────────────────────────────────
from bs4 import BeautifulSoup
from utils.send_email import send_metal_rate_report

# ── Groq ──────────────────────────────────────────────────────────────────────
try:
    from groq import Groq
except ImportError:
    raise SystemExit("❌  Run: pip install groq")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

GROQ_MODEL   = "llama-3.3-70b-versatile"
PAGE_TIMEOUT = 30          # seconds to wait for key element
SCROLL_PAUSE = 1.5         # seconds after scrolling

# Per-site config: URL, what element to wait for, and whether to scroll
SITES = [
    {
        "id":            "kitco",
        "name":          "Kitco – World Spot Prices",
        "url":           "https://www.kitco.com/price/precious-metals",
        "wait_by":       By.CSS_SELECTOR,
        "wait_for":      "table",
        "scroll":        True,
        "extra_wait":    2,
    },
    {
        "id":            "goldpriceindia_palladium",
        "name":          "GoldPriceIndia – Palladium",
        "url":           "https://www.goldpriceindia.com/palladium-price-india.php",
        "wait_by":       By.CSS_SELECTOR,
        "wait_for":      "table",
        "scroll":        False,
        "extra_wait":    1,
    },
    {
        "id":            "rsbl",
        "name":          "RSBL – Live Bullion Rates",
        "url":           "https://www.rsbl.in/live-rates/",
        "wait_by":       By.CSS_SELECTOR,
        "wait_for":      "table",
        "scroll":        False,
        "extra_wait":    3,   # rates need a moment to load via AJAX
    },
    {
    "id": "arihantspot",
    "name": "Arihant Spot – Live Rates",
    "url": "https://www.arihantspot.in/",
    "wait_by": By.TAG_NAME,
    "wait_for": "body",
    "scroll": True,
    "extra_wait": 10
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# GROQ EXTRACTION PROMPTS  (one per site, tuned to the exact data visible)
# ─────────────────────────────────────────────────────────────────────────────

GROQ_PROMPTS = {
    "kitco.com": """
You are a financial data extractor. Extract ALL precious metal spot prices from the page text below.
Return ONLY valid JSON — no markdown fences, no explanation.

Required schema:
{
  "source": "kitco.com",
  "scraped_at": "<ISO timestamp from input>",
  "world_spot_prices": [
    {
      "metal":       "GOLD | SILVER | PLATINUM | PALLADIUM | RHODIUM",
      "date":        "Apr 28, 2026",
      "time_est":    "00:29",
      "bid_usd_oz":  4666.50,
      "ask_usd_oz":  4668.50,
      "change_usd":  -14.70,
      "change_pct":  -0.31,
      "low_usd_oz":  4665.80,
      "high_usd_oz": 4702.10
    }
  ],
  "inr_per_usd":    94.47,
  "gold_inr_per_oz": 440902.44
}
All numeric fields must be numbers (not strings). Use null if a value is missing.
""",

    "goldpriceindia.com": """
You are a financial data extractor. Extract palladium prices from the page text below.
Return ONLY valid JSON — no markdown fences, no explanation.

Required schema:
{
  "source": "goldpriceindia.com",
  "scraped_at": "<ISO timestamp from input>",
  "metal": "PALLADIUM",
  "date": "...",
  "price_inr_per_oz":   138577,
  "price_inr_per_gram":   4455.36,
  "spot_prices_inr": {
    "1_gram":  4455.36,
    "2_gram":  8910.72,
    "5_gram":  22276.80,
    "10_gram": 44553.60,
    "1_oz":    138577.19,
    "1_kg":    4455360.03
  },
  "last_10_days": [
    {"date": "...", "inr_per_oz": 0, "inr_per_10g": 0, "change": "..."}
  ]
}
All numeric fields must be numbers. Use null if missing.
""",

    "rsbl.in": """
You are a financial data extractor. Extract live bullion rates from the page text below.
Return ONLY valid JSON — no markdown fences, no explanation.

Required schema:
{
  "source": "rsbl.in",
  "scraped_at": "<ISO timestamp from input>",
  "header_rates": {
    "gold_usd":   4668.08,
    "silver_usd": 74.6,
    "usd_inr":    94.483,
    "goldamfix":  4701.6,
    "goldpmfix":  4692.25,
    "silverfix":  75.915
  },
  "commodity_rates": [
    {
      "commodity":  "GOLD995MUM",
      "sell":       149241,
      "sell_high":  149959,
      "sell_low":   149223,
      "buy":        149941,
      "buy_high":   null,
      "buy_low":    149223,
      "time":       "10:02:44"
    }
  ]
}
All numeric fields must be numbers. Use null if missing.
""",

    "arihantspot.in": """
You are a financial data extractor. Extract live rates from the Arihant Spot page text below.
Return ONLY valid JSON — no markdown fences, no explanation.

Required schema:
{
  "source": "arihantspot.in",
  "scraped_at": "<ISO timestamp from input>",
  "header": {
    "gold_usd":      4668.35,
    "usd_inr":       94.494,
    "gold_cost_inr": 151596
  },
  "live_rates": [
    {
      "product":    "GOLD 995 (1kg) IND-BIS T+0",
      "buy":        149846,
      "buy_low":    149851,
      "sell":       149946,
      "sell_high":  151950
    }
  ]
}
All numeric fields must be numbers. Use null if missing.
""",
}

# ─────────────────────────────────────────────────────────────────────────────
# SELENIUM DRIVER SETUP
# ─────────────────────────────────────────────────────────────────────────────

def replace_nulls(obj):
    if isinstance(obj, dict):
        return {k: replace_nulls(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_nulls(i) for i in obj]
    elif obj is None:
        return ""
    return obj

def create_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Create a Chrome WebDriver that looks like a real user browser.
    Uses webdriver-manager to auto-download the right ChromeDriver.
    """
    options = Options()

    if headless:
        options.add_argument("--headless=new")   # modern headless mode

    # Stealth settings — avoid being detected as a bot
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1400,900")
    options.add_argument("--lang=en-US")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # Hide the "Chrome is being controlled by automated software" bar
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=options)

    # Spoof navigator.webdriver = false
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )

    return driver

# ─────────────────────────────────────────────────────────────────────────────
# FULL-PAGE SCREENSHOT  (Selenium takes viewport shots; we expand to full page)
# ─────────────────────────────────────────────────────────────────────────────

def take_full_page_screenshot(driver: webdriver.Chrome, path: Path):
    """Resize browser to full page height, screenshot, then restore."""
    try:
        total_width  = driver.execute_script("return document.body.scrollWidth")
        total_height = driver.execute_script("return document.body.scrollHeight")
        # Cap height to avoid memory issues on very tall pages
        total_height = min(total_height, 15000)
        driver.set_window_size(max(total_width, 1400), total_height)
        time.sleep(0.3)
        driver.save_screenshot(str(path))
        driver.set_window_size(1400, 900)   # restore
    except Exception as e:
        print(f"    ⚠️  Full-page screenshot failed ({e}), using viewport screenshot")
        driver.save_screenshot(str(path))

# ─────────────────────────────────────────────────────────────────────────────
# PER-SITE SCRAPING
# ─────────────────────────────────────────────────────────────────────────────

# def scrape_site(driver: webdriver.Chrome, site: dict, run_folder: Path) -> dict:
#     """
#     Navigate to site, wait for data, take screenshot, extract HTML/text.
#     Includes Arihant dynamic loading fix.
#     """

#     sid = site["id"]
#     url = site["url"]

#     print(f"\n   Loading: {url}")

#     result = {
#         "id": sid,
#         "name": site["name"],
#         "url": url,
#         "raw_text": "",
#         "raw_html": "",
#         "tables": [],
#         "screenshot_path": ""
#     }

#     try:
#         driver.get(url)
#     except Exception as e:
#         print(f" Navigation error: {e}")
#         result["error"] = str(e)
#         return result

#     # Wait for base page
#     try:
#         WebDriverWait(driver, 30).until(
#             EC.presence_of_element_located((site["wait_by"], site["wait_for"]))
#         )
#     except:
#         pass

#     # General wait
#     time.sleep(site.get("extra_wait", 3))

#     # ─────────────────────────────────────────────
#     # SPECIAL FIX FOR ARIHANT
#     # ─────────────────────────────────────────────
#     if sid == "arihantspot":
#         print(" Applying Arihant dynamic content fix...")

#         try:
#             # Click LIVE RATES if exists
#             elems = driver.find_elements(
#                 By.XPATH,
#                 "//*[contains(text(),'LIVE RATES')]"
#             )
#             if elems:
#                 driver.execute_script("arguments[0].click();", elems[0])
#                 time.sleep(3)
#         except:
#             pass

#         # Scroll multiple times to trigger JS lazy loading
#         driver.execute_script("window.scrollTo(0,500)")
#         time.sleep(2)

#         driver.execute_script("window.scrollTo(0,1000)")
#         time.sleep(2)

#         driver.execute_script("window.scrollTo(0,0)")
#         time.sleep(2)

#         # Wait until numbers appear in source
#         try:
#             WebDriverWait(driver, 20).until(
#                 lambda d: any(
#                     x in d.page_source
#                     for x in ["995", "999", "GOLD", "SILVER", "149", "151"]
#                 )
#             )
#             print("     Rates detected")
#         except:
#             print("     Rates not detected, continuing")

#     # Normal scrolling
#     if site.get("scroll"):
#         driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
#         time.sleep(2)
#         driver.execute_script("window.scrollTo(0, 0)")
#         time.sleep(1)

#     # Screenshot
#     screenshot_path = run_folder / f"{sid}.png"
#     take_full_page_screenshot(driver, screenshot_path)
#     result["screenshot_path"] = str(screenshot_path)

#     # HTML
#     raw_html = driver.page_source
#     result["raw_html"] = raw_html

#     soup = BeautifulSoup(raw_html, "lxml")

#     for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript"]):
#         tag.decompose()

#     result["raw_text"] = soup.get_text(separator="\n", strip=True)

#     # Tables
#     for tbl in soup.find_all("table"):
#         rows = []

#         for tr in tbl.find_all("tr"):
#             cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
#             if any(cells):
#                 rows.append(cells)

#         if len(rows) > 1:
#             result["tables"].append(rows)

#     print(f"     Extracted {len(result['tables'])} tables")

#     return result

# FINAL FIX: Arihant prices are rendered inside JavaScript DOM widgets,
# not normal tables. Your current extractor sends useless HTML to Groq.
# So now we directly read visible text using Selenium before BeautifulSoup.
# Because some websites believe data should be hidden like state secrets.

# ─────────────────────────────────────────────────────────────
# REPLACE ONLY scrape_site() WITH THIS VERSION
# ─────────────────────────────────────────────────────────────

def scrape_site(driver: webdriver.Chrome, site: dict, run_folder: Path) -> dict:
    sid = site["id"]
    url = site["url"]

    print(f"\n🌐 Loading {url}")

    result = {
        "id": sid,
        "name": site["name"],
        "url": url,
        "raw_text": "",
        "raw_html": "",
        "tables": [],
        "screenshot_path": ""
    }

    driver.get(url)
    time.sleep(site.get("extra_wait"))

    # ─────────────────────────────────────────────
    # SPECIAL HANDLING FOR ARIHANT
    # ─────────────────────────────────────────────
    if sid == "arihantspot":

        print("🔄 Using direct visible-text extraction...")

        # wait more
        time.sleep(30)

        # click LIVE RATES if present
        try:
            btn = driver.find_element(
                By.XPATH,
                "//*[contains(translate(text(),'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ'),'LIVE RATES')]"
            )
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(30)
        except:
            pass

        # trigger lazy load
        for y in [400, 800, 1200, 0]:
            driver.execute_script(f"window.scrollTo(0,{y})")
            time.sleep(2)

        # IMPORTANT:
        # grab visible rendered text from browser
        visible_text = driver.find_element(By.TAG_NAME, "body").text

        # save raw html too
        raw_html = driver.page_source

        result["raw_text"] = visible_text
        result["raw_html"] = raw_html

        # Build pseudo table from visible lines
        lines = [x.strip() for x in visible_text.split("\n") if x.strip()]

        rows = []
        for line in lines:
            if any(word in line.upper() for word in ["GOLD", "SILVER", "995", "999"]):
                rows.append([line])

        if rows:
            result["tables"].append(rows)

    else:
        # normal sites
        raw_html = driver.page_source
        result["raw_html"] = raw_html

        soup = BeautifulSoup(raw_html, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "iframe"]):
            tag.decompose()

        result["raw_text"] = soup.get_text(separator="\n", strip=True)

        for tbl in soup.find_all("table"):
            rows = []
            for tr in tbl.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if any(cells):
                    rows.append(cells)
            if len(rows) > 1:
                result["tables"].append(rows)

    # screenshot
    screenshot_path = run_folder / f"{sid}.png"
    take_full_page_screenshot(driver, screenshot_path)
    result["screenshot_path"] = str(screenshot_path)

    print(f"📊 Tables found: {len(result['tables'])}")

    return result

# ─────────────────────────────────────────────────────────────────────────────
# GROQ  —  raw data → structured JSON
# ─────────────────────────────────────────────────────────────────────────────

def build_groq_payload(scraped: dict, scraped_at: str) -> str:
    """Assemble the user message for Groq from scraped data."""
    parts = [
        f"scraped_at: {scraped_at}",
        f"source_url: {scraped['url']}",
        "",
    ]

    # Tables first — most structured, best for accurate number extraction
    if scraped["tables"]:
        parts.append("=== HTML TABLES (structured data) ===")
        for i, tbl in enumerate(scraped["tables"][:6]):
            parts.append(f"\n-- Table {i+1} --")
            for row in tbl[:25]:
                parts.append("  " + "  |  ".join(str(c) for c in row))

    # Then raw text for context (headers, labels, etc.)
    if scraped["raw_text"]:
        parts.append("\n=== PAGE TEXT ===")
        parts.append(scraped["raw_text"][:6000])

    return "\n".join(parts)


def call_groq(client: Groq, site_source: str, scraped: dict, scraped_at: str) -> dict:
    """Send scraped data to Groq LLM and return parsed JSON."""
    system_prompt = GROQ_PROMPTS.get(site_source, "Extract all data as clean JSON.")
    user_content  = build_groq_payload(scraped, scraped_at)

    print(f"    🤖  Groq [{GROQ_MODEL}] extracting {site_source} …")
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content},
            ],
            temperature=0,
            max_tokens=2048,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown fences (```json ... ```) if present
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$",          "", raw)

        result = json.loads(raw)
        
        result = replace_nulls(result)   # ← add this
        print(f"    ✅  JSON extracted  ({len(result)} top-level keys)")
        return result

    except json.JSONDecodeError as e:
        print(f"    ⚠️  JSON parse error: {e}")
        return {"_raw_reply": raw, "_parse_error": str(e)}
    except Exception as e:
        print(f"    ❌  Groq error: {e}")
        return {"_error": str(e)}

# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT FOLDER  —  DD-MM-YYYY_HH-MM-SSam
# ─────────────────────────────────────────────────────────────────────────────

def make_run_folder(base: Path) -> Path:
    label  = datetime.now().strftime("%d-%m-%Y_%I-%M-%S%p")   # 28-04-2026_10-01-30AM
    folder = base / label
    folder.mkdir(parents=True, exist_ok=True)
    return folder

# ─────────────────────────────────────────────────────────────────────────────
# SITE → SOURCE  mapping for GROQ_PROMPTS lookup
# ─────────────────────────────────────────────────────────────────────────────

SITE_SOURCE = {
    "kitco":                    "kitco.com",
    "goldpriceindia_palladium": "goldpriceindia.com",
    "rsbl":                     "rsbl.in",
    "arihantspot":              "arihantspot.in",
}

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Precious Metals Scraper (Selenium)")
    parser.add_argument("--output-dir",   default="./scraper_output",
                        help="Base output directory  (default: ./scraper_output)")
    parser.add_argument("--headless",     default="true", choices=["true", "false"],
                        help="Run Chrome headless  (default: true)")
    parser.add_argument("--groq-api-key", default=os.environ.get("GROQ_API_KEY"),
                        help="Groq API key  (or set GROQ_API_KEY in .env file)")
    args = parser.parse_args()

    # ── Validate API key ──────────────────────────────────────────────────────
    if not args.groq_api_key:
        raise SystemExit(
            "❌  GROQ_API_KEY not found.\n"
            "    Add it to your .env file:\n"
            "        GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx\n"
            "    Or pass it directly:\n"
            "        python scrape_metals.py --groq-api-key gsk_xxxx"
        )

    groq_client = Groq(api_key=args.groq_api_key)
    run_folder  = make_run_folder(Path(args.output_dir))
    scraped_at  = datetime.now().isoformat()
    headless    = args.headless.lower() == "true"

    print(f"\n{'═'*60}")
    print(f"  Precious Metals Scraper  —  Selenium")
    print(f"  Run folder : {run_folder}")
    print(f"  Headless   : {headless}")
    print(f"  Groq model : {GROQ_MODEL}")
    print(f"{'═'*60}")

    all_data = {}
    summary  = []

    # ── Single browser session for all 4 sites ────────────────────────────────
    print("\n🚀  Starting Chrome …")
    driver = create_driver(headless=headless)

    try:
        for site in SITES:
            sid    = site["id"]
            source = SITE_SOURCE[sid]

            print(f"\n{'─'*60}")
            print(f"  [{sid.upper()}]  {site['name']}")
            print(f"{'─'*60}")

            # 1. Scrape page + take screenshot
            scraped = scrape_site(driver, site, run_folder)

            # 2. Send to Groq → structured JSON
            parsed = call_groq(groq_client, source, scraped, scraped_at)

            # 3. Attach metadata to the JSON
            parsed["_meta"] = {
                "source_id":       sid,
                "source":          source,
                "scraped_at":      scraped_at,
                "screenshot_file": Path(scraped["screenshot_path"]).name
                                   if scraped["screenshot_path"] else None,
                "tables_found":    len(scraped["tables"]),
            }

            # 4. Save individual JSON file
            json_path = run_folder / f"{sid}.json"
            json_path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False),
                                 encoding="utf-8")
            print(f"    💾  Saved → {json_path.name}")

            all_data[sid] = parsed
            summary.append({
                "site":            source,
                "json_file":       json_path.name,
                "screenshot_file": Path(scraped["screenshot_path"]).name
                                   if scraped["screenshot_path"] else None,
                "status":          "error" if ("_error" in parsed or "error" in scraped)
                                   else "ok",
            })

    finally:
        driver.quit()
        print("\n🔒  Browser closed")

    # ── Master JSON (all 4 sites combined) ────────────────────────────────────
    master = {
        "run_timestamp": scraped_at,
        "run_folder":    str(run_folder),
        "sites":         summary,
        "data":          all_data,
    }
    master_path = run_folder / "master.json"
    master_path.write_text(json.dumps(master, indent=2, ensure_ascii=False),
                           encoding="utf-8")
    
    # ── Build HTML table ─────────────────────────────
    build_rates_table(master, run_folder)
    RECIPIENTS = ["aman.gupta@jewelexindia.com", "ketan.shah@bitalinfo.com", "aashay.mehta@jewelexindia.com"]  # CHANGE THIS!
    # RECIPIENTS = ["aman.gupta@jewelexindia.com", "aashay.mehta@jewelexindia.com"]
    send_metal_rate_report(run_folder, RECIPIENTS)

    # ── Final summary ─────────────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print(f"  ✅  DONE  —  {len(SITES)} sites scraped")
    print(f"  📂  {run_folder}")
    print(f"{'═'*60}")
    for s in summary:
        icon = "✅" if s["status"] == "ok" else "❌"
        print(f"  {icon}  {s['site']}")
        print(f"         📸  {s['screenshot_file']}")
        print(f"         💾  {s['json_file']}")
    print(f"\n  📄  master.json  (all sites combined)\n")


if __name__ == "__main__":
    main()