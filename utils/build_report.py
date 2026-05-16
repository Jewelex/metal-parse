from pathlib import Path
import json
from datetime import date
from utils.goldformula import calculate_gold_rate
from utils.platinumformula import calculate_platinum_rate
from utils.palladiumformula import calculate_palladium_rate
# from goldformula import calculate_gold_rate
# from platinumformula import calculate_platinum_rate



def build_rates_table(master_data: dict, output_folder: Path, debug=True):

    def log(msg):
        if debug:
            print(msg)

    log("\n" + "="*70)
    log("🚀 STARTING METAL RATE ENGINE")
    log("="*70)

    data = master_data["data"]

    kitco           = data.get("kitco", {})
    rsbl            = data.get("rsbl", {})
    arihant         = data.get("arihantspot", {})
    palladium_india = data.get("goldpriceindia_palladium", {})

    # ── KITCO ASK ──────────────────────────────────────────────────────────
    kitco_prices = {}
    for item in kitco.get("world_spot_prices", []):
        ask = item.get("ask_usd_oz")
        if ask:
            kitco_prices[item["metal"]] = ask

    # ── FOREX ──────────────────────────────────────────────────────────────
    forex = rsbl.get("header_rates", {}).get("usd_inr", 95)

    # ── GOLD ───────────────────────────────────────────────────────────────
    gold_calc = calculate_gold_rate(gold_rate=kitco_prices.get("GOLD"), forex_rate=forex)
    gold_999  = gold_calc["rate_for_10gm_999"]
    gold_995  = gold_calc["rate_for_10gm_995"]

    # ── PLATINUM ───────────────────────────────────────────────────────────
    # plat_calc_999 = calculate_platinum_rate(kitco_rate=kitco_prices.get("PLATINUM"), forex_rate=forex, purity=999)
    # plat_calc_950 = calculate_platinum_rate(kitco_rate=kitco_prices.get("PLATINUM"), forex_rate=forex, purity=950)
    # platinum_999  = plat_calc_999["rate_for_10gm_999"]
    # platinum_950  = plat_calc_950["rate_for_10gm_999"]

        # ── PLATINUM ───────────────────────────────────────────────────────────
    plat_calc    = calculate_platinum_rate(kitco_rate=kitco_prices.get("PLATINUM"), forex_rate=forex)
    platinum_999 = plat_calc["rate_for_10gm_999"]
    platinum_950 = plat_calc["rate_for_10gm_950"]


    # ── PALLADIUM ──────────────────────────────────────────────────────────
    # palladium_999 = palladium_india.get("spot_prices_inr", {}).get("10_gram")
    # ── PALLADIUM ──────────────────────────────────────────────────────────
    raw_palladium = palladium_india.get("spot_prices_inr", {}).get("10_gram")

    # If the scraped source is already 10gm, do NOT feed it as per-gram.
    # Either use the raw value directly, or first convert your source to per-gram.

    palladium_calc = calculate_palladium_rate(cif_per_gram=4605.25)
    palladium_999 = palladium_calc["rate_for_10gm_999"]

    
    # ── SILVER ─────────────────────────────────────────────────────────────
    silver_rate     = None
    rsbl_silver_raw = None
    for item in rsbl.get("commodity_rates", []):
        if "SILVER" in item["commodity"]:
            rsbl_silver_raw = item.get("sell")
            silver_rate     = rsbl_silver_raw / 100
            break

    # ── ARIHANT ────────────────────────────────────────────────────────────
    arihant_995 = arihant_999 = None
    for item in arihant.get("live_rates", []):
        name  = item["product"].upper()
        price = item.get("sell")
        if "995" in name and "1KG" in name:
            arihant_995 = price
        if "999" in name:
            arihant_999 = price

    # ── RSBL ───────────────────────────────────────────────────────────────
    rsbl_gold_999 = rsbl_gold_995 = None
    for item in rsbl.get("commodity_rates", []):
        if item["commodity"] == "GOLD999MUM":
            rsbl_gold_999 = item.get("sell")
        if item["commodity"] == "GOLD995MUM":
            rsbl_gold_995 = item.get("sell")

    # ── FORMAT HELPER ──────────────────────────────────────────────────────
    def fmt(val):
        if val is None or val == "-":
            return "-"
        try:
            return f"{round(float(val)):,}"
        except Exception:
            return str(val)

    today_str = date.today().strftime("%d-%b-%y")

    # ═══════════════════════════════════════════════════════════════════
    # EXACT COLOR CODES
    # ═══════════════════════════════════════════════════════════════════
    #  Top stripe (salmon/coral)     #F4A7A3
    #  Date header bg (purple)       #A45DB5   text #FFFFFF
    #  Column header bg (dark red)   #C0392B   text #FFD700
    #  Metal col – Gold rows         #FFD700
    #            – Platinum rows     #FF69B4
    #            – Palladium row     #BEBEBE
    #            – Silver row        #FFD700
    #  Grams col                     #BABABA
    #  Purity col                    #FF69B4   text #000000
    #  Today Rate col                #F6BEF8
    #  RSBL col                      #D8D8D8
    #  Arihant col                   #F4B183
    #  Note row                      #BFEFFF
    # ═══════════════════════════════════════════════════════════════════

    METAL_BG = {
        "Gold":      "#FFD700",
        "Platinum":  "#FFD700",
        "Palladium": "#FFD700",
        "Silver":    "#FFD700",
    }

    BORDER = "#0C0B0B"

    def td(content, bg, text="#000000", bold=False, align="center"):
        fw = "bold" if bold else "normal"
        return (
            f'<td style="background-color:{bg};color:{text};font-weight:{fw};'
            f'font-size:13px;font-family:Arial,sans-serif;padding:6px 10px;'
            f'text-align:{align};border:1px solid {BORDER};">{content}</td>'
        )

    def th(content, bg, text="#000000"):
        return (
            f'<th style="background-color:{bg};color:{text};font-weight:bold;'
            f'font-size:13px;font-family:Arial,sans-serif;padding:7px 10px;'
            f'text-align:center;border:1px solid {BORDER};">{content}</th>'
        )

    # ── TABLE ROWS ─────────────────────────────────────────────────────────
    data_rows = [
        ("Gold",      10, "999", gold_999,      rsbl_gold_999,                                       arihant_999),
        ("Gold",      10, "995", gold_995,      rsbl_gold_995,                                       arihant_995),
        ("Platinum",  10, "999", platinum_999,  "-",                                                 "-"),
        ("Platinum",  10, "950", platinum_950,  "-",                                                 "-"),
        ("Palladium", 10, "999", palladium_999, "-",                                                 "-"),
        ("Silver",    10, "-",   silver_rate,   rsbl_silver_raw / 100 if rsbl_silver_raw else "-",   "-"),
    ]

    rows_html = ""
    for metal, grams, purity, today, rsbl_v, arihant_v in data_rows:
        rows_html += "<tr>"
        rows_html += td(metal,          bg=METAL_BG[metal], text="#000000", bold=True)
        rows_html += td(grams,          bg="#BABABA",        text="#000000", align="right")
        rows_html += td(purity,         bg="#FF69B4",        text="#000000", bold=True)
        rows_html += td(fmt(today),     bg="#F6BEF8",        text="#000000", align="right")
        rows_html += td(fmt(rsbl_v),    bg="#D8D8D8",        text="#000000", align="right")
        rows_html += td(fmt(arihant_v), bg="#F4B183",        text="#000000", align="right")
        rows_html += "</tr>\n"

    # ── HTML OUTPUT ────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Metal Rate Report</title></head>
<body style="margin:0;padding:20px;font-family:Arial,sans-serif;background-color:#FFFFFF;color:#222222;">

<p style="margin:0 0 5px 0;font-size:14px;font-family:Arial,sans-serif;">Dear All,</p>
<p style="margin:0 0 16px 0;font-size:14px;font-family:Arial,sans-serif;">Please see the below metal rate.</p>

<table cellpadding="0" cellspacing="0" border="0"
  style="border-collapse:collapse;width:100%;max-width:680px;font-family:Arial,sans-serif;">

  <!-- ① Top coral/salmon stripe -->
  <tr>
    <td colspan="6"
      style="background-color:#F4A7A3;height:12px;font-size:1px;line-height:1px;
             border:1px solid {BORDER};">&nbsp;</td>
  </tr>

  <!-- ② Date header — purple -->
  <tr>
    <td colspan="3"
      style="background-color:#A45DB5;color:#FFFFFF;font-size:13px;font-family:Arial,sans-serif;
             font-weight:bold;padding:6px 10px;border:1px solid {BORDER};">
      <u>Metal Rates for the date:</u>
    </td>
    <td colspan="3"
      style="background-color:#A45DB5;color:#FFFFFF;font-size:13px;font-family:Arial,sans-serif;
             font-weight:bold;padding:6px 10px;border:1px solid {BORDER};">
      <u>{today_str}</u>
    </td>
  </tr>

  <!-- ③ Column headers -->
  <tr>
    {th("Metal",      "#FFD700")}
    {th("Grams",      "#BABABA")}
    {th("Purity",     "#FF69B4")}
    {th("Today Rate", "#F6BEF8")}
    {th("RSBL",       "#D8D8D8")}
    {th("Arihant",    "#F4B183")}
  </tr>

  <!-- ④ Data rows -->
  {rows_html}

  <!-- ⑤ Note row -->
  <tr>
    <td colspan="6"
      style="background-color:#BFEFFF;color:#000000;font-size:12px;font-family:Arial,sans-serif;
             padding:6px 10px;text-align:left;border:1px solid {BORDER};">
      
    </td>
  </tr>

</table>

<p style="margin:16px 0 0 0;font-size:13px;font-family:Arial,sans-serif;">
  <b>NOTE : 999 Gold rate not available in Arihant spot site.</b>
</p>

</body>
</html>"""

    out_path = output_folder / "rates_table.html"
    out_path.write_text(html, encoding="utf-8")

    log(f"\n📊 HTML REPORT SAVED: {out_path}")
    log("✅ ENGINE COMPLETE")


