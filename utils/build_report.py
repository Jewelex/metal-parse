from pathlib import Path
# from goldformula import calculate_gold_rate
# from platinumformula import calculate_platinum_rate

import json

from pathlib import Path
from utils.goldformula import calculate_gold_rate
from utils.platinumformula import calculate_platinum_rate


def build_rates_table(master_data: dict, output_folder: Path, debug=True):

    def log(msg):
        if debug:
            print(msg)

    log("\n" + "="*70)
    log("🚀 STARTING METAL RATE ENGINE")
    log("="*70)

    data = master_data["data"]

    kitco = data.get("kitco", {})
    rsbl = data.get("rsbl", {})
    arihant = data.get("arihantspot", {})
    palladium_india = data.get("goldpriceindia_palladium", {})

    # ─────────────────────────────────────────────
    # KITCO ASK EXTRACTION
    # ─────────────────────────────────────────────
    kitco_prices = {}
    for item in kitco.get("world_spot_prices", []):
        metal = item["metal"]
        ask = item.get("ask_usd_oz")
        if ask:
            kitco_prices[metal] = ask

    log("\n📊 KITCO ASK PRICES:")
    for k, v in kitco_prices.items():
        log(f"   {k}: {v}")

    # ─────────────────────────────────────────────
    # FOREX
    # ─────────────────────────────────────────────
    forex = rsbl.get("header_rates", {}).get("usd_inr", 95)
    log(f"\n💱 USD/INR: {forex}")

    # ─────────────────────────────────────────────
    # GOLD CALCULATION
    # ─────────────────────────────────────────────
    gold_calc = calculate_gold_rate(
        gold_rate=kitco_prices.get("GOLD"),
        forex_rate=forex
    )

    gold_999 = gold_calc["rate_for_10gm_999"]
    gold_995 = gold_calc["rate_for_10gm_995"]

    log("\n🟡 GOLD CALCULATION:")
    log(gold_calc)

    # ─────────────────────────────────────────────
    # PLATINUM
    # ─────────────────────────────────────────────
    plat_calc_999 = calculate_platinum_rate(
        kitco_rate=kitco_prices.get("PLATINUM"),
        forex_rate=forex,
        purity=999
    )

    plat_calc_950 = calculate_platinum_rate(
        kitco_rate=kitco_prices.get("PLATINUM"),
        forex_rate=forex,
        purity=950
    )

    platinum_999 = plat_calc_999["rate_for_10gm_999"]
    platinum_950 = plat_calc_950["rate_for_10gm_999"]

    log("\n⚪ PLATINUM 999:")
    log(plat_calc_999)

    log("\n⚪ PLATINUM 950:")
    log(plat_calc_950)

    # ─────────────────────────────────────────────
    # PALLADIUM
    # ─────────────────────────────────────────────
    palladium_999 = palladium_india.get("spot_prices_inr", {}).get("10_gram")

    kitco_palladium_999 = None
    if kitco_prices.get("PALLADIUM"):
        kitco_palladium_999 = (
            kitco_prices["PALLADIUM"] / 31.1035 * forex * 10
        )

    log(f"\n🟣 PALLADIUM (India): {palladium_999}")
    log(f"🟣 PALLADIUM (Kitco conv): {kitco_palladium_999}")

    # ─────────────────────────────────────────────
    # SILVER
    # ─────────────────────────────────────────────
    silver_rate = None
    rsbl_silver_raw = None

    for item in rsbl.get("commodity_rates", []):
        if "SILVER" in item["commodity"]:
            rsbl_silver_raw = item.get("sell")
            silver_rate = rsbl_silver_raw / 100
            break

    kitco_silver = None
    if kitco_prices.get("SILVER"):
        kitco_silver = (
            kitco_prices["SILVER"] / 31.1035 * forex * 10
        )

    log(f"\n🔵 SILVER RSBL raw: {rsbl_silver_raw}")
    log(f"🔵 SILVER (₹/10g): {silver_rate}")
    log(f"🔵 SILVER (Kitco conv): {kitco_silver}")

    # ─────────────────────────────────────────────
    # ARIHANT FILTER (FIXED)
    # ─────────────────────────────────────────────
    arihant_995 = None
    arihant_999 = None

    log("\n🏢 ARIHANT PRODUCTS:")

    for item in arihant.get("live_rates", []):
        name = item["product"].upper()
        price = item.get("sell")

        log(f"   {name} → {price}")

        if "995" in name and "1KG" in name:
            arihant_995 = price

        if "999" in name:
            arihant_999 = price

    log(f"\nArihant 995: {arihant_995}")
    log(f"Arihant 999: {arihant_999}")

    # ─────────────────────────────────────────────
    # RSBL DATA
    # ─────────────────────────────────────────────
    rsbl_gold_999 = None
    rsbl_gold_995 = None

    for item in rsbl.get("commodity_rates", []):
        if item["commodity"] == "GOLD999MUM":
            rsbl_gold_999 = item.get("sell")
        if item["commodity"] == "GOLD995MUM":
            rsbl_gold_995 = item.get("sell")

    log(f"\n🏦 RSBL GOLD999: {rsbl_gold_999}")
    log(f"🏦 RSBL GOLD995: {rsbl_gold_995}")

    # ─────────────────────────────────────────────
    # FINAL TABLE DATA
    # ─────────────────────────────────────────────
    rows = [
        ["Gold", "10", "999", gold_999, rsbl_gold_999, arihant_999],
        ["Gold", "10", "995", gold_995, rsbl_gold_995, arihant_995],
        ["Platinum", "10", "999", platinum_999, "-", "-"],
        ["Platinum", "10", "950", platinum_950, "-", "-"],
        ["Palladium", "10", "999", palladium_999, "-", "-"],
        ["Silver", "10", "-", silver_rate, rsbl_silver_raw / 100 if rsbl_silver_raw else "-", "-"],
    ]

    headers = ["Metal", "Grams", "Purity", "Today Rate", "RSBL", "Arihant"]

    # ─────────────────────────────────────────────
    # HTML REPORT
    # ─────────────────────────────────────────────
    html = """
    <html>
    <head>
    <style>
        body { font-family: Arial; background: #020617; color: white; }
        table { border-collapse: collapse; width: 95%; margin: 40px auto; }
        th, td { padding: 12px; text-align: center; }
        th { background: #1e293b; }
        tr:nth-child(even) { background: #0f172a; }
        tr:nth-child(odd) { background: #1e293b; }
        td { font-weight: bold; }
        .gold { color: #facc15; }
        .platinum { color: #e5e7eb; }
        .palladium { color: #c084fc; }
        .silver { color: #93c5fd; }
    </style>
    </head>
    <body>

    <h2 style="text-align:center;">Metal Rate Report (₹/10g)</h2>
    <table border="1">
    <tr>
    """

    for h in headers:
        html += f"<th>{h}</th>"
    html += "</tr>"

    for row in rows:
        cls = row[0].lower()
        html += f"<tr class='{cls}'>"
        for cell in row:
            html += f"<td>{round(cell,2) if isinstance(cell,(int,float)) else cell}</td>"
        html += "</tr>"

    html += "</table></body></html>"

    out_path = output_folder / "rates_table.html"
    out_path.write_text(html, encoding="utf-8")

    log("\n📊 HTML REPORT GENERATED")
    log(f"📂 Saved at: {out_path}")

    log("\n" + "="*70)
    log("✅ ENGINE COMPLETE")
    log("="*70)

# ##Test
# RUN_FOLDER = Path(r"C:\Users\Aman.gupta\Downloads\metal-rate-bot\scraper_output\04-05-2026_02-48-20PM")

# master_path = RUN_FOLDER / "master.json"

# print(f"\n📂 Loading: {master_path}")

# with open(master_path, "r", encoding="utf-8") as f:
#     master_data = json.load(f)

# # Run your function
# build_rates_table(master_data, RUN_FOLDER, debug=True)