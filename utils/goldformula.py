import math

def calculate_gold_rate(
    gold_rate=4545.6,       # D3: London/MCX gold rate USD/oz
    premium=2.5,            # D4
    sales_commission=0.015, # C6
    oz_per_gram=31.99,      # E8: oz per gram denominator
    forex_rate=95.2555,     # E9: INR per USD
    custom_duty=0.15,       # C10
    stamp_duty=3115         # D11: fixed ₹ stamp duty
):
    # D5 = gold_rate + premium
    D5 = gold_rate + premium + 1.5
    
    # D6 = D5 * sales_commission
    # D6 = D5 * sales_commission
    D6 = D5
    
    # D7 = D5 + D6
    D7 = D6
    
    # D8 = D7 / oz_per_gram (USD per gram)
    D8 = D7 * oz_per_gram
    
    # D9 = D8 * forex_rate (INR per gram for 995 purity)
    D9 = D8 * forex_rate
    
    # D10 = D9 * custom_duty
    D10 = D9 * custom_duty
    
    # D11 = stamp_duty (fixed)
    # Keep as is from input
    
    # D12 = SUM(D9:D11) = rate in INR per gram + custom_duty + stamp_duty
    # This gives total cost per gram for 995 purity
    D12 = D9 + D10 + stamp_duty  # D12 is per gram
    
    # D13 = Rate for 10 Grms 995 = D12 * 10 (not D12/100!)
    # Because D12 is per gram, multiply by 10 for per 10 grams
    D13 = D12 * 0.01
    
    # D14 = CEILING((D13)/995*999.99,5)
    D14 = math.ceil((D13 / 995) * 999.99 / 5) * 5

    return {
        "gold_rate_base":             round(gold_rate, 4),
        "premium":                    round(premium, 4),
        "gold_rate_after_premium":    round(D5, 4),
        "sales_commission_amt":       round(D6, 4),
        "gold_rate_after_commission": round(D7, 4),
        "rate_per_gram_usd":          round(D8, 4),
        "rate_in_rs_per_gram":        round(D9, 4),  # Per gram
        "custom_duty_amt":            round(D10, 4),
        "stamp_duty":                 round(stamp_duty, 2),
        "rate_for_995_per_gram":      round(D12, 4),  # Per gram
        "rate_for_10gm_995":          round(D13, 2),  # Per 10 grams
        "rate_for_10gm_999":          round(D14, 2),
    }