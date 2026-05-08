

import json
from pathlib import Path
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================

SCRAPER_BASE = Path("./scraper_output")
HISTORY_DIR = Path("./history")

HISTORY_DIR.mkdir(exist_ok=True)

# =========================================================
# HELPERS
# =========================================================

def latest_run_folder():
    folders = [f for f in SCRAPER_BASE.iterdir() if f.is_dir()]
    folders.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    if not folders:
        raise Exception("No scraper_output folders found.")
    return folders[0]

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def fmt(v):
    if v in [None, "", "-", {}]:
        return "-"
    try:
        return f"{int(round(float(v))):,}"
    except:
        return str(v)

def get_rate(rows, code, field="sell"):
    for row in rows:
        if row.get("commodity") == code:
            return row.get(field)
    return None

def get_spot(kitco_rows, metal):
    for row in kitco_rows:
        if row.get("metal") == metal:
            return row
    return {}

def yesterday_value(key):
    files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)
    if not files:
        return "-"
    try:
        old = load_json(files[0])
        return old.get(key, "-")
    except:
        return "-"

# =========================================================
# LOAD MASTER JSON
# =========================================================

folder = latest_run_folder()
master = load_json(folder / "master.json")

data = master["data"]

kitco = data["kitco"]
rsbl = data["rsbl"]
arihant = data.get("arihantspot", {})
palladium_json = data["goldpriceindia_palladium"]

kitco_rows = kitco["world_spot_prices"]
rsbl_rows = rsbl["commodity_rates"]

usd_inr = rsbl["header_rates"]["usd_inr"]

# =========================================================
# LIVE VALUES
# =========================================================

gold_row = get_spot(kitco_rows, "GOLD")
silver_row = get_spot(kitco_rows, "SILVER")
platinum_row = get_spot(kitco_rows, "PLATINUM")

gold999 = get_rate(rsbl_rows, "GOLD999MUM")
gold995 = get_rate(rsbl_rows, "GOLD995MUM")

silver_kg = get_rate(rsbl_rows, "SILVER999MUM")
silver10 = round(silver_kg / 100) if silver_kg else None

# Platinum from Kitco USD oz converted approx to 10g INR
plat_usd = platinum_row.get("ask_usd_oz", 0)
platinum999 = round((plat_usd / 31.1035) * 10 * usd_inr)
platinum950 = round(platinum999 * 0.95 / 5) * 5

# Palladium direct India source
palladium999 = round(
    palladium_json["spot_prices_inr"]["10_gram"]
)

# Arihant 995
arihant995 = "-"
try:
    if arihant.get("live_rates"):
        arihant995 = arihant["live_rates"][0]["sell"]
except:
    pass

# =========================================================
# YESTERDAY VALUES
# =========================================================

gold999_y = yesterday_value("gold999")
gold995_y = yesterday_value("gold995")
platinum999_y = yesterday_value("platinum999")
platinum950_y = yesterday_value("platinum950")
palladium999_y = yesterday_value("palladium999")
silver10_y = yesterday_value("silver10")

# =========================================================
# SAVE TODAY HISTORY
# =========================================================

today_file = HISTORY_DIR / f'{datetime.now().strftime("%Y-%m-%d")}.json'

today_data = {
    "gold999": gold999,
    "gold995": gold995,
    "platinum999": platinum999,
    "platinum950": platinum950,
    "palladium999": palladium999,
    "silver10": silver10
}

with open(today_file, "w", encoding="utf-8") as f:
    json.dump(today_data, f, indent=2)

# =========================================================
# DATE
# =========================================================

today = datetime.now().strftime("%d-%b-%y")

# =========================================================
# HTML REPORT
# =========================================================

html = f"""
<html>
<head>
<style>
body {{
    font-family: Calibri;
    font-size: 14px;
}}
table {{
    border-collapse: collapse;
}}
th, td {{
    border:1px solid #777;
    padding:8px 12px;
}}
th {{
    text-align:center;
}}
td {{
    text-align:right;
}}
td:first-child {{
    text-align:left;
}}
.header {{
    background:#c95af5;
    font-weight:bold;
    font-size:16px;
}}
.cols {{
    background:#f2d266;
    font-weight:bold;
}}
</style>
</head>

<body>

<p>Dear All,</p>
<p>Please see the below metal rate.</p>

<table>

<tr class="header">
<th colspan="7">Metal Rates for the date: {today}</th>
</tr>

<tr class="cols">
<th>Metal</th>
<th>Grams</th>
<th>Purity</th>
<th>Today Rate</th>
<th>Yesterday</th>
<th>RSBL</th>
<th>Arihant</th>
</tr>

<tr>
<td>Gold</td>
<td>10</td>
<td>999</td>
<td>{fmt(gold999)}</td>
<td>{fmt(gold999_y)}</td>
<td>{fmt(gold999)}</td>
<td>-</td>
</tr>

<tr>
<td>Gold</td>
<td>10</td>
<td>995</td>
<td>{fmt(gold995)}</td>
<td>{fmt(gold995_y)}</td>
<td>{fmt(gold995)}</td>
<td>{fmt(arihant995)}</td>
</tr>

<tr>
<td>Platinum</td>
<td>10</td>
<td>999</td>
<td>{fmt(platinum999)}</td>
<td>{fmt(platinum999_y)}</td>
<td>-</td>
<td>-</td>
</tr>

<tr>
<td>Platinum</td>
<td>10</td>
<td>950</td>
<td>{fmt(platinum950)}</td>
<td>{fmt(platinum950_y)}</td>
<td>-</td>
<td>-</td>
</tr>

<tr>
<td>Palladium</td>
<td>10</td>
<td>999</td>
<td>{fmt(palladium999)}</td>
<td>{fmt(palladium999_y)}</td>
<td>-</td>
<td>-</td>
</tr>

<tr>
<td>Silver</td>
<td>10</td>
<td>-</td>
<td>{fmt(silver10)}</td>
<td>{fmt(silver10_y)}</td>
<td>{fmt(silver10)}</td>
<td>-</td>
</tr>

</table>

<p><b>Note:</b> 999 Gold rate not available in Arihant spot site.</p>

</body>
</html>
"""

# =========================================================
# SAVE HTML
# =========================================================

output = folder / "mail_preview.html"

with open(output, "w", encoding="utf-8") as f:
    f.write(html)

print("✅ Mail Preview Generated:")
print(output)