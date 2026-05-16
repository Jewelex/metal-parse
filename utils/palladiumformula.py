import math

def calculate_palladium_rate(
    cif_per_gram=4605.25,   # use PER GRAM base here
    av=0,
    bd_pct=0.075,
    cvd_pct=0.08,
    edu_cess_pct=0.03,
    c_edu_cess_pct=0.03,
    spl_cvd_pct=0.04
):
    c1517 = cif_per_gram
    c1518 = av
    c1519 = c1517 + c1518
    c1520 = c1519 * bd_pct
    c1521 = c1519 + c1520
    c1522 = c1521 * cvd_pct
    c1523 = c1522 * edu_cess_pct
    c1524 = (c1520 + c1522 + c1523) * c_edu_cess_pct
    c1525 = (c1519 + c1520 + c1522 + c1523 + c1524) * spl_cvd_pct

    final_per_gram = c1519 + c1520 + c1522 + c1523 + c1524 + c1525
    final_10gm = math.ceil(final_per_gram * 10 / 5) * 5

    return {
        "rate_per_gram": round(final_per_gram, 2),
        "rate_for_10gm_999": round(final_10gm, 2),
    }