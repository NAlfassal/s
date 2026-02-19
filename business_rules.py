
from typing import Optional
import re
import unicodedata
# address, sector mapping
def sanitize_item(item):
    return {
        k: sanitize_xml_string(v) if isinstance(v, str) else v
        for k, v in item.items()
    } 

def safe_price(value):
    try:
        return round(float(value), 12)
    except:
        return 0.0


def sanitize_xml_string(s):
    if not isinstance(s, str):
        return ""
    
    # Normalize unicode and remove control chars (0x00–0x1F except tab, newline, carriage return)
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]", "", s)
    
    # Replace problematic unicode characters
    s = s.replace("\u2028", " ")  # line separator
    s = s.replace("\u00ad", "")   # soft hyphen
    s = s.replace("\xa0", " ")    # non-breaking space

    # Escape XML characters
    s = (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&apos;")
    )
    
    return s.strip()


def sanitize_float(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        value = str(value).replace(',', '').strip()
        return float(value)
    except ValueError:
        print(f"[❌ Invalid float] Could not convert '{value}'")
        return 0.0

   
def get_country_id(models, db, uid, password, country_code: str) -> Optional[int]:
    if not country_code:
        return None
    country_ids = models.execute_kw(
        db, uid, password,
        'res.country', 'search',
        [[['code', '=', country_code]]],
        {'limit': 1}
    )
    return country_ids[0] if country_ids else None


def get_state_id(models, db, uid, password, state_name: str, country_id: int) -> Optional[int]:
    if not state_name or not country_id:
        return None

    state_ids = models.execute_kw(
        db, uid, password,
        'res.country.state', 'search',
        [[
            ['name', 'ilike', state_name],
            ['country_id', '=', country_id]
        ]],
        {'limit': 1}
    )
    return state_ids[0] if state_ids else None


def validate_category(category: str) -> Optional[str]:
    if not category:
        return "All"
    
    category = category.strip()

    ALLOWED_CATEGORIES = [
        "EX - Training", "EX - Support", "EX - Products (HW Only)", "EX - PS",
        "EX - Outsourcing", "EX - MSS", "EX - MDS", "EX - License", "EX - Consulting", "All" 
    ]
    # If exact match, return
    if category in ALLOWED_CATEGORIES:
        return category

    # Fallback mapping logic 
    fallback_keywords = {
        "training": "EX - Training",
        "support": "EX - Support",
        "hardware": "EX - Products (HW Only)",
        "product": "EX - Products (HW Only)",
        "ps": "EX - PS",
        "setup": "EX - PS",
        "license": "EX - License",
        "consult": "EX - Consulting",
        "mss": "EX - MSS",
        "mds": "EX - MDS",
        "outsourcing": "EX - Outsourcing"
    }

    for keyword, mapped_category in fallback_keywords.items():
        if keyword.lower() in category.lower():
            return mapped_category

    return "All"   # default fallback

def map_sector(sector_name: str) -> Optional[str]:
    if not sector_name:
        return None
    sector_map = {
        "government": "government",
        "corporate": "coroporate",  # odoo typo
        "non profit": "non_profit"
    }
    return sector_map.get(sector_name.strip().lower())

def map_product_type(product_type: str, default: str = "consu") -> str:
    if not product_type:
        return "consu"
    
    type_mapping = {
        "Storable Product": "product",
        "Consumable": "consu",
        "Service": "service"
    }
    return type_mapping.get(product_type, default)

def normalize_currency(value):
    
    ALLOWED_CURRENCIES = {"SAR", "USD", "EUR", "GBP", "AED"}
    CURRENCY_ALIASES = {"SR": "SAR", "€": "EUR", "$": "USD", "£": "GBP", "AED": "AED"}

    if not value:  # covers None, "", 0
        return "SAR"

    value = value.strip().upper()
    return CURRENCY_ALIASES.get(value, value) if value in CURRENCY_ALIASES else (value if value in ALLOWED_CURRENCIES else "")