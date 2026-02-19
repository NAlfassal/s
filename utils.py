import xmlrpc.client
from config import ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD

def get_odoo_connection():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})

    if not uid:
        raise Exception("Failed to authenticate with Odoo. Check credentials.")

    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return models, ODOO_DB, uid, ODOO_PASSWORD


def currency(models, db, uid, password, currency_code):

    currency_ids = models.execute_kw(
        db, uid, password,
        'res.currency', 'search',
        [[['name', '=', currency_code]]],  
        {'limit': 1}
    )
    if not currency_ids:
        raise Exception(f"Currency {currency_code} not found.")
    return currency_ids[0]

def get_currency_code(quotation, default="SAR"):
    for item in quotation.get("Items", []):
        if item.get("Currency"):
            return item["Currency"]
    return default  # fallback if none of the items have a currency

def get_UoM(models, db, uid, password):
    
      # get UoM ID for "Units"
            unit_uom_ids = models.execute_kw(
                db, uid, password,
                'uom.uom', 'search',
                [[['name', '=', 'Units']]],
                {'limit': 1}
            )
            unit_uom_id = unit_uom_ids[0] if unit_uom_ids else None
            
            return unit_uom_id
            