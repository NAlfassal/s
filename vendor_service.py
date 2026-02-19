from Post_processing.business_rules import get_country_id, get_state_id, map_sector
from odoo_services.utils import get_odoo_connection

models, db, uid, password = get_odoo_connection()

def get_or_create_vendor(vendor_dict):
    vendor_name = vendor_dict.get("name")
    vat = vendor_dict.get("vat")
    email = vendor_dict.get("email")
    phone = vendor_dict.get("phone")
    city = vendor_dict.get("city")
    zip_code = vendor_dict.get("zip")
    country_code = vendor_dict.get("country")
    website = vendor_dict.get("website")
    mobile = vendor_dict.get("mobile")
    name_ar = vendor_dict.get("name_ar")
    short_name = vendor_dict.get("short_name")
    street = vendor_dict.get("address")
    state_name = vendor_dict.get("state")
    country_code = vendor_dict.get("country")


    # Check if vendor exists
    partner_ids = models.execute_kw(
        db, uid, password,
        'res.partner', 'search',
        [[['name', '=', vendor_name], ['company_type', '=', 'company']]],
        {'limit': 1}
    )

    if partner_ids:
        print(f"[✅ Vendor found] {partner_ids[0]}")
        return partner_ids[0]
    
    # Lookup sector
    sector_raw = vendor_dict.get("sector")
    sector = map_sector(sector_raw)
    

    # Lookup country_id and state_id
    country_id = get_country_id(models, db, uid, password, country_code)
    state_id = get_state_id(models, db, uid, password, state_name, country_id)

                
    # Lookup or create tags
    # tag_names = vendor_dict.get("tags", [])
    # tag_ids = []
    # for tag_name in tag_names:
    #     tag_id = models.execute_kw(
    #         db, uid, password,
    #         'res.partner.category', 'search',
    #         [[['name', '=', tag_name]]],
    #         {'limit': 1}
    #     )
    #     if not tag_id:
    #         tag_id = [models.execute_kw(
    #             db, uid, password,
    #             'res.partner.category', 'create',
    #             [{'name': tag_name}]
    #         )]
    #     tag_ids.append(tag_id[0])


    vendor_vals = {
        'name': vendor_name,
        'x_name_arabic': name_ar,
        'short_name': short_name,
        'company_type': 'company',
        'supplier_rank': 1,
        'vat': vat,
        'email': email,
        'phone': phone,
        'mobile': mobile,
        'city': city,
        'street': street,
        'zip': zip_code,
        'state_id': state_id,
        'country_id': country_id,
        'website': website,
        'company_sector': sector,
        # 'category_id': [(6, 0, tag_ids)],

    }

    # Remove None values
    vendor_vals = {k: v for k, v in vendor_vals.items() if v is not None}

    # Create vendor
    partner_id = models.execute_kw(
        db, uid, password,
        'res.partner', 'create',
        [vendor_vals]
    )
    print(f"[✅ Vendor Created] {vendor_name} → ID: {partner_id}")
    return partner_id


