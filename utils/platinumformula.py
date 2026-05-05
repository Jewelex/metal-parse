import math

def calculate_platinum_rate(
    kitco_rate=1906,          # F6: Kitco platinum USD/oz
    premium=0.02,             # E7
    oz_per_gram=31.1035,      # E9
    airfreight=0.5,           # F10
    forex_rate=95.2555,       # E13: INR per USD
    custom_duty=0.05,         # E14
    aidc=0.014,               # E15
    jewellery_pct=0.952,      # E18
    spl_alloy_charges=120,    # F19
    gst_pct=0,                # GST rate
    octroi=0,                 # E24
    making_rate=0,            # E30
    purity=950                # G32
):
    # F7 = kitco_rate * premium
    F7 = kitco_rate * premium
    
    # F8 = kitco_rate + F7
    F8 = kitco_rate + F7
    
    # F9 = F8 / oz_per_gram
    F9 = F8 / oz_per_gram
    
    # F11 = F9 + airfreight
    F11 = F9 + airfreight
    
    # F12 = F11 * 0.01 (Landing charges @1%)
    F12 = F11 * 0.01
    
    # F13 = F11 + F12 (Conversion charges/CIF value)
    F13 = F11 + F12
    
    # Custom duty on 101% of CIF
    F14 = (custom_duty * 1.01) * F13
    
    # AIDC
    F15 = F13 * aidc
    
    # Note: There's F16 in Excel screenshot but value not shown
    F16 = 0
    
    # Total USD before forex (F13 + F14 + F16 + F15)
    total_usd = F13 + F14 + F15 + F16
    
    # Platinum rate per gram for 99.99% in INR
    F17 = total_usd * forex_rate
    
    # Platinum jewellery rate
    F18 = F17 * jewellery_pct
    
    # Add special alloy charges
    F20 = F18 + spl_alloy_charges
    
    # GST calculation
    F21 = F20 * gst_pct
    
    # Subtotal after GST
    F23 = F20 + F21
    
    # Octroi/Stamp Duty (assuming 0.021 = 2.1%)
    # octroi_amount = F23 * octroi if octroi < 1 else octroi
    octroi_amount = 0 
    F25 = F23 + octroi_amount
    
    # Making charges
    F30 = F25 * making_rate
    
    # Final rate per gram for 999 purity
    F31 = F25 + F30
    
    # Convert to target purity for system rate purpose
    # Formula from screenshot: =+F31/G32*999
    # BUT this appears to be converting FROM target purity TO 999
    # Let me re-analyze the screenshot...
    
    # The screenshot shows: "conversion for the 999 purity (system rate purpose) =+F31/G32*999"
    # and "1950 purity considered" - this means G32 = 950
    # So: F31/950*999 = Converting 950 rate to equivalent 999 rate?
    # That would make 950 appear HIGHER than 999 rate (which matches your output!)
    
    # I think the formula is actually:
    # If F31 is for 950 purity, then equivalent 999 purity rate = F31/950*999
    # This explains why 950 shows higher number!
    
    # So your output is actually showing:
    # - Platinum 999: ₹65,416/10g (actual 999 rate)
    # - Platinum 950: ₹68,790/10g (equivalent 999 rate if converted from 950)
    
    # If you want actual 950 rate for comparison:
    actual_950_rate = F31  # This is already the rate for 950 purity
    equivalent_999_rate = (F31 / purity) * 999
    
    return {
        "kitco_rate":                    round(kitco_rate, 4),
        "premium_amt":                   round(F7, 4),
        "rate_with_premium":             round(F8, 4),
        "rate_per_gram_usd":             round(F9, 4),
        "airfreight":                    round(airfreight, 4),
        "rate_with_airfreight":          round(F11, 4),
        "landing_charges_1pct":          round(F12, 4),
        "conversion_charges":            round(F13, 4),
        "custom_duty_amt":               round(F14, 4),
        "aidc_amt":                      round(F15, 4),
        "platinum_rate_per_gram_9999":   round(F17, 4),
        "platinum_jewellery_rate":       round(F18, 4),
        "spl_alloy_charges":             round(spl_alloy_charges, 4),
        "total_before_gst":              round(F20, 4),
        "gst_amt":                       round(F21, 4),
        "sub_total":                     round(F23, 4),
        "octroi":                        round(octroi_amount, 4),
        "total_per_gram":                round(F25, 4),
        "making_amt":                    round(F30, 4),
        "final_platinum_rate_per_gram":  round(F31, 4),
        "rate_for_999_purity":           round(equivalent_999_rate, 4),
        "rate_for_10gm_999":             round(equivalent_999_rate * 10, 2),
    }