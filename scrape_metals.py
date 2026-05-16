#!/usr/bin/env python3
# scrape_metals.py  –  MinIO edition (no local file storage)

import os
import re
import io
import json
import time
import tempfile
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# ── Selenium ──────────────────────────────────────────────────────────────────
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# ── HTML parsing ──────────────────────────────────────────────────────────────
from bs4 import BeautifulSoup

# ── Project utilities ─────────────────────────────────────────────────────────
from utils.build_report import build_rates_table
from utils.send_email import send_metal_rate_report
from utils.s3_storage import (                                    # ← NEW
    get_s3_client,
    ensure_bucket,
    upload_bytes,
    upload_json,
    upload_file,
    build_run_prefix,
    get_object_url,
)

# ── Groq ──────────────────────────────────────────────────────────────────────
try:
    from groq import Groq
except ImportError:
    raise SystemExit("Run: pip install groq")


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

GROQ_MODEL   = "llama-3.3-70b-versatile"
PAGE_TIMEOUT = 30
SCROLL_PAUSE = 1.5

MINIO_BUCKET = "metal-rates"                                      # ← NEW

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
        "extra_wait":    3,
    },
    {
        "id":            "arihantspot",
        "name":          "Arihant Spot – Live Rates",
        "url":           "https://www.arihantspot.in/",
        "wait_by":       By.TAG_NAME,
        "wait_for":      "body",
        "scroll":        True,
        "extra_wait":    10,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# GROQ PROMPTS  (unchanged)
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

SITE_SOURCE = {
    "kitco":                    "kitco.com",
    "goldpriceindia_palladium": "goldpriceindia.com",
    "rsbl":                     "rsbl.in",
    "arihantspot":              "arihantspot.in",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS  (unchanged)
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
    options = Options()
    if headless:
        options.add_argument("--headless=new")
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
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


# ─────────────────────────────────────────────────────────────────────────────
# SCREENSHOT → bytes (no local file needed)                         ← CHANGED
# ─────────────────────────────────────────────────────────────────────────────

def take_full_page_screenshot_bytes(driver: webdriver.Chrome) -> bytes | None:
    """Return a PNG screenshot as bytes (full-page where possible)."""
    try:
        total_width = driver.execute_script("return document.body.scrollWidth")
        total_height = driver.execute_script("return document.body.scrollHeight")
        total_height = min(total_height, 5000)
        driver.set_window_size(max(total_width, 1400), total_height)
        time.sleep(0.3)
        png = driver.get_screenshot_as_png()
        driver.set_window_size(1400, 900)
        return png
    except Exception as e:
        print(f"    ⚠️  Full-page screenshot failed ({e}), using viewport")
        try:
            driver.set_window_size(1400, 900)
            return driver.get_screenshot_as_png()
        except Exception:
            print(f"    ⚠️  Viewport screenshot also failed")
            return None


# ─────────────────────────────────────────────────────────────────────────────
# PER-SITE SCRAPING  (returns screenshot bytes instead of path)      ← CHANGED
# ─────────────────────────────────────────────────────────────────────────────

def scrape_site(driver: webdriver.Chrome, site: dict) -> dict:
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
        "screenshot_png": None,                                   # ← bytes now
    }

    driver.get(url)
    time.sleep(site.get("extra_wait"))

    # ── ARIHANT special handling ──────────────────────────────────────────
    if sid == "arihantspot":
        print("🔄 Using direct visible-text extraction...")
        time.sleep(15)
        try:
            btn = driver.find_element(
                By.XPATH,
                "//*[contains(translate(text(),'abcdefghijklmnopqrstuvwxyz',"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'),'LIVE RATES')]",
            )
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(10)
        except Exception:
            pass
        for y in [400, 800, 1200, 0]:
            driver.execute_script(f"window.scrollTo(0,{y})")
            time.sleep(2)

        visible_text = driver.find_element(By.TAG_NAME, "body").text
        raw_html = driver.page_source
        result["raw_text"] = visible_text
        result["raw_html"] = raw_html

        lines = [x.strip() for x in visible_text.split("\n") if x.strip()]
        rows = []
        for line in lines:
            if any(word in line.upper() for word in ["GOLD", "SILVER", "995", "999"]):
                rows.append([line])
        if rows:
            result["tables"].append(rows)
    else:
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

    # Screenshot → bytes                                          ← CHANGED
    result["screenshot_png"] = take_full_page_screenshot_bytes(driver)

    print(f"📊 Tables found: {len(result['tables'])}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# GROQ  (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

def build_groq_payload(scraped: dict, scraped_at: str) -> str:
    parts = [
        f"scraped_at: {scraped_at}",
        f"source_url: {scraped['url']}",
        "",
    ]
    if scraped["tables"]:
        parts.append("=== HTML TABLES (structured data) ===")
        for i, tbl in enumerate(scraped["tables"][:6]):
            parts.append(f"\n-- Table {i+1} --")
            for row in tbl[:25]:
                parts.append("  " + "  |  ".join(str(c) for c in row))
    if scraped["raw_text"]:
        parts.append("\n=== PAGE TEXT ===")
        parts.append(scraped["raw_text"][:6000])
    return "\n".join(parts)


def call_groq(client: Groq, site_source: str, scraped: dict, scraped_at: str) -> dict:
    system_prompt = GROQ_PROMPTS.get(site_source, "Extract all data as clean JSON.")
    user_content = build_groq_payload(scraped, scraped_at)

    print(f"    🤖  Groq [{GROQ_MODEL}] extracting {site_source} …")
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
            max_tokens=2048,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        result = json.loads(raw)
        result = replace_nulls(result)
        print(f"    ✅  JSON extracted  ({len(result)} top-level keys)")
        return result
    except json.JSONDecodeError as e:
        print(f"    ⚠️  JSON parse error: {e}")
        return {"_raw_reply": raw, "_parse_error": str(e)}
    except Exception as e:
        print(f"    ❌  Groq error: {e}")
        return {"_error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN                                                               ← CHANGED
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Precious Metals Scraper (Selenium + MinIO)")
    parser.add_argument("--headless", default="true", choices=["true", "false"],
                        help="Run Chrome headless  (default: true)")
    parser.add_argument("--groq-api-key", default=os.environ.get("GROQ_API_KEY"),
                        help="Groq API key  (or set GROQ_API_KEY in .env)")
    parser.add_argument("--minio-endpoint", default=os.environ.get("MINIO_ENDPOINT", "http://192.168.100.149:9000"),
                        help="MinIO endpoint URL")
    parser.add_argument("--minio-bucket", default=os.environ.get("MINIO_BUCKET", MINIO_BUCKET),
                        help="MinIO bucket name")
    args = parser.parse_args()

    if not args.groq_api_key:
        raise SystemExit(
            "❌  GROQ_API_KEY not found.\n"
            "    Add it to your .env file or pass --groq-api-key"
        )

    groq_client = Groq(api_key=args.groq_api_key)
    scraped_at = datetime.now().isoformat()
    headless = args.headless.lower() == "true"

    # ── MinIO setup ───────────────────────────────────────────────── ← NEW
    s3 = get_s3_client(endpoint_url=args.minio_endpoint)
    bucket = args.minio_bucket
    ensure_bucket(s3, bucket)
    run_prefix = build_run_prefix()  # e.g. "runs/28-04-2026_10-01-30AM"

    print(f"\n{'═'*60}")
    print(f"  Precious Metals Scraper  —  Selenium + MinIO")
    print(f"  S3 bucket  : {bucket}")
    print(f"  Run prefix : {run_prefix}/")
    print(f"  Headless   : {headless}")
    print(f"  Groq model : {GROQ_MODEL}")
    print(f"{'═'*60}")

    all_data = {}
    summary = []

    print("\n🚀  Starting Chrome …")
    driver = create_driver(headless=headless)

    try:
        for site in SITES:
            sid = site["id"]
            source = SITE_SOURCE[sid]

            print(f"\n{'─'*60}")
            print(f"  [{sid.upper()}]  {site['name']}")
            print(f"{'─'*60}")

            # 1. Scrape
            scraped = scrape_site(driver, site)

            # 2. Upload screenshot to MinIO                       ← NEW
            screenshot_key = None
            if scraped["screenshot_png"]:
                screenshot_key = f"{run_prefix}/{sid}.png"
                upload_bytes(s3, bucket, screenshot_key, scraped["screenshot_png"], "image/png")
                print(f"    📸  Uploaded → s3://{bucket}/{screenshot_key}")

            # 3. Groq extraction
            parsed = call_groq(groq_client, source, scraped, scraped_at)

            # 4. Attach metadata (S3 key instead of local path)  ← CHANGED
            parsed["_meta"] = {
                "source_id": sid,
                "source": source,
                "scraped_at": scraped_at,
                "screenshot_s3_key": screenshot_key,
                "tables_found": len(scraped["tables"]),
            }

            # 5. NO individual JSON files saved                   ← CHANGED
            all_data[sid] = parsed
            summary.append({
                "site": source,
                "screenshot_s3_key": screenshot_key,
                "status": "error" if ("_error" in parsed or "error" in scraped) else "ok",
            })

    finally:
        driver.quit()
        print("\n🔒  Browser closed")

    # ── Master JSON → MinIO ───────────────────────────────────── ← CHANGED
    master = {
        "run_timestamp": scraped_at,
        "s3_bucket": bucket,
        "s3_run_prefix": run_prefix,
        "sites": summary,
        "data": all_data,
    }
    master_key = f"{run_prefix}/master.json"
    upload_json(s3, bucket, master_key, master)
    print(f"\n💾  master.json → s3://{bucket}/{master_key}")

    # ── Build HTML table → MinIO ──────────────────────────────── ← CHANGED
    #    build_rates_table writes to a local folder, so we use a tempdir
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        build_rates_table(master, tmp_path)

        html_file = tmp_path / "rates_table.html"
        if html_file.exists():
            html_key = f"{run_prefix}/rates_table.html"
            upload_file(s3, bucket, html_key, html_file, "text/html")
            print(f"📊  rates_table.html → s3://{bucket}/{html_key}")

        # ── Email (still reads from local tmpdir) ─────────────────
        RECIPIENTS = os.getenv("RECIPIENTS", "").split(",")
        RECIPIENTS = [email.strip() for email in RECIPIENTS if email.strip()]

        if not RECIPIENTS:
            print("⚠️  No RECIPIENTS found in .env file! Skipping email.")
        else:
            send_metal_rate_report(tmp_path, RECIPIENTS)

    # ── Final summary ─────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print(f"  ✅  DONE  —  {len(SITES)} sites scraped")
    print(f"  🪣  s3://{bucket}/{run_prefix}/")
    print(f"{'═'*60}")
    for s in summary:
        icon = "✅" if s["status"] == "ok" else "❌"
        print(f"  {icon}  {s['site']}")
        if s["screenshot_s3_key"]:
            print(f"         📸  {s['screenshot_s3_key']}")
    print(f"\n  📄  {master_key}")
    print(f"  📊  {run_prefix}/rates_table.html\n")


if __name__ == "__main__":
    main()
