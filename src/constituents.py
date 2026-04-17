"""
NIFTY 50 constituents as of December 2025.

Tickers use the .NS suffix for yfinance / NSE queries.

Notes on data quality:
- TMPV.NS (Tata Motors Passenger Vehicles): Only ~120 rows of history available,
  starting 2025-10-15. This is the successor entity after Tata Motors' October 2025
  demerger, which renamed TATAMOTORS → TMPV. The pre-demerger TATAMOTORS ticker
  was delisted, and Yahoo Finance does not carry the legacy history under TMPV.
- ETERNAL.NS (formerly Zomato): Partial history starting ~July 2021 (IPO date).
"""
NIFTY_50_CONSTITUENTS = [
    # Financial Services
    {"ticker": "HDFCBANK.NS",   "company_name": "HDFC Bank Ltd",                       "sector": "Financial Services", "industry": "Private Bank"},
    {"ticker": "ICICIBANK.NS",  "company_name": "ICICI Bank Ltd",                      "sector": "Financial Services", "industry": "Private Bank"},
    {"ticker": "SBIN.NS",       "company_name": "State Bank of India",                 "sector": "Financial Services", "industry": "Public Bank"},
    {"ticker": "KOTAKBANK.NS",  "company_name": "Kotak Mahindra Bank Ltd",             "sector": "Financial Services", "industry": "Private Bank"},
    {"ticker": "AXISBANK.NS",   "company_name": "Axis Bank Ltd",                       "sector": "Financial Services", "industry": "Private Bank"},
    {"ticker": "BAJFINANCE.NS", "company_name": "Bajaj Finance Ltd",                   "sector": "Financial Services", "industry": "NBFC"},
    {"ticker": "BAJAJFINSV.NS", "company_name": "Bajaj Finserv Ltd",                   "sector": "Financial Services", "industry": "Financial Holding"},
    {"ticker": "HDFCLIFE.NS",   "company_name": "HDFC Life Insurance Co Ltd",          "sector": "Financial Services", "industry": "Insurance"},
    {"ticker": "SBILIFE.NS",    "company_name": "SBI Life Insurance Co Ltd",           "sector": "Financial Services", "industry": "Insurance"},
    {"ticker": "SHRIRAMFIN.NS", "company_name": "Shriram Finance Ltd",                 "sector": "Financial Services", "industry": "NBFC"},

    # Information Technology
    {"ticker": "TCS.NS",        "company_name": "Tata Consultancy Services Ltd",       "sector": "Information Technology", "industry": "IT Services"},
    {"ticker": "INFY.NS",       "company_name": "Infosys Ltd",                         "sector": "Information Technology", "industry": "IT Services"},
    {"ticker": "HCLTECH.NS",    "company_name": "HCL Technologies Ltd",                "sector": "Information Technology", "industry": "IT Services"},
    {"ticker": "WIPRO.NS",      "company_name": "Wipro Ltd",                           "sector": "Information Technology", "industry": "IT Services"},
    {"ticker": "TECHM.NS",      "company_name": "Tech Mahindra Ltd",                   "sector": "Information Technology", "industry": "IT Services"},

    # Energy / Oil & Gas
    {"ticker": "RELIANCE.NS",   "company_name": "Reliance Industries Ltd",             "sector": "Energy", "industry": "Oil & Gas / Conglomerate"},
    {"ticker": "ONGC.NS",       "company_name": "Oil & Natural Gas Corporation Ltd",   "sector": "Energy", "industry": "Oil & Gas Exploration"},
    {"ticker": "COALINDIA.NS",  "company_name": "Coal India Ltd",                      "sector": "Energy", "industry": "Coal Mining"},
    {"ticker": "BPCL.NS",       "company_name": "Bharat Petroleum Corporation Ltd",    "sector": "Energy", "industry": "Oil Refining & Marketing"},

    # Consumer Goods (FMCG)
    {"ticker": "HINDUNILVR.NS", "company_name": "Hindustan Unilever Ltd",              "sector": "FMCG", "industry": "Personal & Household Products"},
    {"ticker": "ITC.NS",        "company_name": "ITC Ltd",                             "sector": "FMCG", "industry": "Cigarettes & Diversified"},
    {"ticker": "NESTLEIND.NS",  "company_name": "Nestle India Ltd",                    "sector": "FMCG", "industry": "Packaged Foods"},
    {"ticker": "BRITANNIA.NS",  "company_name": "Britannia Industries Ltd",            "sector": "FMCG", "industry": "Packaged Foods"},
    {"ticker": "TATACONSUM.NS", "company_name": "Tata Consumer Products Ltd",          "sector": "FMCG", "industry": "Packaged Foods & Beverages"},

    # Automobiles
    {"ticker": "MARUTI.NS",     "company_name": "Maruti Suzuki India Ltd",             "sector": "Automobiles", "industry": "Passenger Vehicles"},
    {"ticker": "M&M.NS",        "company_name": "Mahindra & Mahindra Ltd",             "sector": "Automobiles", "industry": "Passenger & Commercial Vehicles"},
    {"ticker": "TMPV.NS",       "company_name": "Tata Motors Passenger Vehicles Ltd",  "sector": "Automobiles", "industry": "Passenger Vehicles & JLR"},
    {"ticker": "BAJAJ-AUTO.NS", "company_name": "Bajaj Auto Ltd",                      "sector": "Automobiles", "industry": "Two-Wheelers"},
    {"ticker": "EICHERMOT.NS",  "company_name": "Eicher Motors Ltd",                   "sector": "Automobiles", "industry": "Two-Wheelers & Commercial Vehicles"},
    {"ticker": "HEROMOTOCO.NS", "company_name": "Hero MotoCorp Ltd",                   "sector": "Automobiles", "industry": "Two-Wheelers"},

    # Pharmaceuticals & Healthcare
    {"ticker": "SUNPHARMA.NS",  "company_name": "Sun Pharmaceutical Industries Ltd",   "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"ticker": "DRREDDY.NS",    "company_name": "Dr. Reddy's Laboratories Ltd",        "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"ticker": "CIPLA.NS",      "company_name": "Cipla Ltd",                           "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"ticker": "APOLLOHOSP.NS", "company_name": "Apollo Hospitals Enterprise Ltd",     "sector": "Healthcare", "industry": "Hospitals"},

    # Metals & Mining
    {"ticker": "TATASTEEL.NS",  "company_name": "Tata Steel Ltd",                      "sector": "Metals & Mining", "industry": "Steel"},
    {"ticker": "JSWSTEEL.NS",   "company_name": "JSW Steel Ltd",                       "sector": "Metals & Mining", "industry": "Steel"},
    {"ticker": "HINDALCO.NS",   "company_name": "Hindalco Industries Ltd",             "sector": "Metals & Mining", "industry": "Aluminium"},

    # Cement & Construction Materials
    {"ticker": "ULTRACEMCO.NS", "company_name": "UltraTech Cement Ltd",                "sector": "Construction Materials", "industry": "Cement"},
    {"ticker": "GRASIM.NS",     "company_name": "Grasim Industries Ltd",               "sector": "Construction Materials", "industry": "Cement & Diversified"},

    # Infrastructure / Capital Goods
    {"ticker": "LT.NS",         "company_name": "Larsen & Toubro Ltd",                 "sector": "Industrials", "industry": "Construction & Engineering"},
    {"ticker": "ADANIPORTS.NS", "company_name": "Adani Ports & SEZ Ltd",               "sector": "Industrials", "industry": "Ports & Logistics"},
    {"ticker": "ADANIENT.NS",   "company_name": "Adani Enterprises Ltd",               "sector": "Industrials", "industry": "Conglomerate"},
    {"ticker": "BEL.NS",        "company_name": "Bharat Electronics Ltd",              "sector": "Industrials", "industry": "Defence Electronics"},

    # Power & Utilities
    {"ticker": "NTPC.NS",       "company_name": "NTPC Ltd",                            "sector": "Utilities", "industry": "Power Generation"},
    {"ticker": "POWERGRID.NS",  "company_name": "Power Grid Corporation of India Ltd", "sector": "Utilities", "industry": "Power Transmission"},

    # Telecom
    {"ticker": "BHARTIARTL.NS", "company_name": "Bharti Airtel Ltd",                   "sector": "Telecom", "industry": "Telecom Services"},

    # Consumer Discretionary
    {"ticker": "TITAN.NS",      "company_name": "Titan Company Ltd",                   "sector": "Consumer Discretionary", "industry": "Jewellery & Watches"},
    {"ticker": "ASIANPAINT.NS", "company_name": "Asian Paints Ltd",                    "sector": "Consumer Discretionary", "industry": "Paints"},
    {"ticker": "TRENT.NS",      "company_name": "Trent Ltd",                           "sector": "Consumer Discretionary", "industry": "Retail"},
    {"ticker": "ETERNAL.NS",    "company_name": "Eternal Ltd (formerly Zomato)",       "sector": "Consumer Discretionary", "industry": "Online Food Delivery"},
]


def get_tickers():
    """Return a flat list of NSE tickers (with .NS suffix)."""
    return [c["ticker"] for c in NIFTY_50_CONSTITUENTS]


if __name__ == "__main__":
    print(f"Total constituents: {len(NIFTY_50_CONSTITUENTS)}")
    sectors = {}
    for c in NIFTY_50_CONSTITUENTS:
        sectors[c["sector"]] = sectors.get(c["sector"], 0) + 1
    print("\nSector breakdown:")
    for sector, count in sorted(sectors.items(), key=lambda x: -x[1]):
        print(f"  {sector:30s} {count}")