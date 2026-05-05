# 🪙 Precious Metals Price Scraper — Selenium

Automates 4 precious-metals websites using **Selenium + Chrome**, takes
full-page screenshots, and uses **Groq LLM** to extract clean JSON data.

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Python      | 3.9 or higher |
| Google Chrome | Any recent version — **must be installed** |
| ChromeDriver | Auto-downloaded by `webdriver-manager` — no manual install |
| Groq API key | Free at [console.groq.com](https://console.groq.com) |

---

## Setup

```bash
# 1. Install Python packages
pip install -r requirements.txt

# 2. Set your Groq API key
# Windows CMD:
set GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
# Windows PowerShell:
$env:GROQ_API_KEY="gsk_xxxxxxxxxxxxxxxxxxxx"
# Linux / Mac:
export GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

---

## Run

```bash
# Default — headless Chrome, output in ./scraper_output
python scrape_metals.py

# Show the Chrome browser window (good for debugging)
python scrape_metals.py --headless false

# Custom output folder
python scrape_metals.py --output-dir D:\metals_data

# Pass API key inline
python scrape_metals.py --groq-api-key gsk_xxxx
```

---

## Output structure

Every run creates a timestamped folder:

```
scraper_output/
└── 28-04-2026_10-01-30AM/        ← DD-MM-YYYY_HH-MM-SSam
    ├── kitco.png                  ← Full-page screenshot
    ├── kitco.json                 ← Groq-extracted structured data
    ├── goldpriceindia_palladium.png
    ├── goldpriceindia_palladium.json
    ├── rsbl.png
    ├── rsbl.json
    ├── arihantspot.png
    ├── arihantspot.json
    └── master.json                ← All 4 sites combined
```

---

## Sample JSON output

### kitco.json
```json
{
  "source": "kitco.com",
  "scraped_at": "2026-04-28T10:01:30",
  "world_spot_prices": [
    {
      "metal": "GOLD",
      "date": "Apr 28, 2026",
      "time_est": "00:29",
      "bid_usd_oz": 4666.50,
      "ask_usd_oz": 4668.50,
      "change_usd": -14.70,
      "change_pct": -0.31,
      "low_usd_oz": 4665.80,
      "high_usd_oz": 4702.10
    },
    { "metal": "SILVER",    "bid_usd_oz": 74.45, "ask_usd_oz": 74.70, ... },
    { "metal": "PLATINUM",  "bid_usd_oz": 1975.00, ... },
    { "metal": "PALLADIUM", "bid_usd_oz": 1444.00, ... },
    { "metal": "RHODIUM",   "bid_usd_oz": 9650.00, ... }
  ],
  "inr_per_usd": 94.47,
  "gold_inr_per_oz": 440902.44
}
```

### rsbl.json
```json
{
  "source": "rsbl.in",
  "scraped_at": "2026-04-28T10:02:44",
  "header_rates": {
    "gold_usd": 4668.08,
    "silver_usd": 74.6,
    "usd_inr": 94.483,
    "goldamfix": 4701.6,
    "goldpmfix": 4692.25,
    "silverfix": 75.915
  },
  "commodity_rates": [
    {
      "commodity": "GOLD995MUM",
      "sell": 149241, "sell_high": 149959, "sell_low": 149223,
      "buy": 149941,  "buy_high": null,    "buy_low": 149223,
      "time": "10:02:44"
    }
  ]
}
```

---

## Schedule (run automatically)

### Windows Task Scheduler
1. Open **Task Scheduler** → Create Basic Task
2. Trigger: Daily, repeat every **1 hour**
3. Action: Start a program
   - Program: `python`
   - Arguments: `C:\path\to\scrape_metals.py`
   - Start in: `C:\path\to\scraper_selenium\`
4. Add environment variable: `GROQ_API_KEY=gsk_xxxx`

### Linux / Mac cron
```bash
crontab -e
# Run every hour:
0 * * * * cd /path/to/scraper_selenium && GROQ_API_KEY=gsk_xxxx python scrape_metals.py >> scraper.log 2>&1
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Chrome not found` | Install Google Chrome from [google.com/chrome](https://google.com/chrome) |
| `ChromeDriver version mismatch` | `pip install --upgrade webdriver-manager` |
| `GROQ_API_KEY not set` | Set the env var or use `--groq-api-key` flag |
| Page loads but prices are 0 | Try `--headless false` to see what the browser shows |
| `selenium.common.exceptions.WebDriverException` | Restart — Chrome may have crashed |
| Site shows CAPTCHA | Run with `--headless false`, solve once, then switch back |
