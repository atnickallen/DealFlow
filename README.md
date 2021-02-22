![DealFlow-Mov](https://user-images.githubusercontent.com/39813026/108612644-9c656700-73b8-11eb-9bcb-04ee15b0d948.gif)
Realtime dealflow of new venture rounds entered directly into airtable



## Set your API keys

Use the ```settings.py``` file to set your Crunchbase API key and your Airtable API.


## Choose your round types

I have kept it to just early rounds

```
funding_types = [
    "convertible_note",
    "angel",
    "pre_seed",
    "seed",
    "equity_crowdfunding",
    "grant",
]
```

## All possible round types

    map = {
        "pre_seed": "Pre-Seed",
        "seed": "Seed",
        "angel": "Angel",
        "venture": "Venture",
        "equity_crowdfunding": "Equity Crowdfunding",
        "product_crowdfunding": "Product Crowdfunding",
        "private_equity": "Private Equity",
        "convertible_note": "Convertible Note",
        "debt_financing": "Debt Financing",
        "secondary_market": "Secondary Market",
        "grant": "Grant",
        "post_ipo_equity": "Post-IPO Equity",
        "post_ipo_debt": "Post-IPO Debt",
        "non_equity_assistance": "Non-Equity Assistance",
        "undisclosed": "Undisclosed",
        "corporate_round": "Corporate Round",
        "initial_coin_offering": "Initial Coin Offering",
        "post_ipo_secondary": "Post-IPO Secondary",
        "series_a": "Series A",
        "series_b": "Series B",
        "series_c": "Series C",
        "series_d": "Series D",
        "series_e": "Series E",
        "series_f": "Series F",
        "series_g": "Series G",
        "series_h": "Series H",
        "series_i": "Series I",
        "series_j": "Series J",
        "series_unknown": "Venture - Series Unknown",
    }
    ```
    
   ## Get round properties
    
    return {
        "ID": crunchbase_funding_round["uuid"],
        "Round Type": humanize_funding_type(properties["funding_type"]),
        "Round Size": properties["target_money_raised_usd"],
        "Raised So Far": properties["money_raised_usd"],
        "Pre-Money Valuation or Note Cap": properties["pre_money_valuation_usd"],
        "Close Date": properties.get("close_date"),
        "Announcement Date": properties["announced_on"],
        "Company": [crunchbase_funding_round["company_airtable_id"]],
        "Investors": list(set(crunchbase_funding_round["fund_airtable_ids"])),
        "Lead Investor": [crunchbase_funding_round["lead_fund_airtable_id"]]
        if crunchbase_funding_round["lead_fund_airtable_id"] is not None
        else None,
        "Last Updated": datetime.fromtimestamp(properties["updated_at"]).isoformat(),
    }

    
    
