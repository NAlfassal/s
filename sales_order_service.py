from odoo_services.utils import get_odoo_connection

models, db, uid, password = get_odoo_connection()


def get_sales_order(sin):
    order_ids = models.execute_kw(
        db, uid, password,
        'sale.order', 'search',
        [[['name', '=', sin]]]
    )
    if not order_ids:
        return None
    return order_ids[0]

def find_sector_region(so_data):
    sector_id = so_data[0].get('sector_id') 
    region_id = so_data[0].get('region_id')
    opportunity_id = so_data[0].get('opportunity_id') and so_data[0]['opportunity_id'][0]

    # unpack many2one tuples
    sector_id = sector_id[0] if sector_id else False
    region_id = region_id[0] if region_id else False

    print(f"[📄 SECTOR_ID on SO] {sector_id}, [📄 REGION_ID on SO] {region_id}")
    
    # if we have no opportunity, cannot fallback at all
    if not opportunity_id:
        return sector_id, region_id
    
    opp_data = models.execute_kw(
            db, uid, password,
            'crm.lead', 'read',
            [opportunity_id],
            {'fields': ['sector_id', 'region_id']}
        )
    
    # if missing, fallback to opportunity
    if (not sector_id) and opportunity_id:

        opp_sector = opp_data[0].get('sector_id')
        
        if not sector_id and opp_sector:
            sector_id = opp_sector[0]
        
        print(f"[📄 FALLBACK SECTOR_ID from Opportunity] {sector_id}")

    if (not region_id) and opportunity_id:
        opp_region = opp_data[0].get('region_id')

       
        if not region_id and opp_region:
            region_id = opp_region[0]

        print(f"[📄 FALLBACK REGION_ID from Opportunity] {region_id}")

    return sector_id, region_id

def patch_so_lines(order_id, sector_id, region_id): 
    
    so_line_ids = models.execute_kw(
        db, uid, password,
        'sale.order.line', 'search',
        [[['order_id', '=', order_id]]]
    )

    for so_line_id in so_line_ids:
        models.execute_kw(
            db, uid, password,
            'sale.order.line', 'write',
            [[so_line_id], {
                'sector_id': sector_id,
                'region_id': region_id
            }]
        )
        print(f"[🛠️ PATCHED] SO Line {so_line_id} with sector={sector_id}, region={region_id}")
