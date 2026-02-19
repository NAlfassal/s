from Post_processing.business_rules import sanitize_float, sanitize_item, sanitize_xml_string
from odoo_services.sales_order_service import get_sales_order, find_sector_region, patch_so_lines
from odoo_services.product_service import get_or_create_product
from odoo_services.vendor_service import get_or_create_vendor
from odoo_services.purchase_service import apply_standard_note_and_payment_term, get_or_create_pr, add_pr_lines, create_rfq, add_rfq_lines
from odoo_services.utils import get_UoM, get_currency_code
from odoo_services.utils import get_odoo_connection

models, db, uid, password = get_odoo_connection()

# Main pipeline
def process_quotation_data(data):
    print("[⚙️ Processing]", data["SIN"])
    sin = data["SIN"]

    order_id = get_sales_order(sin)
    if not order_id:
        print(f"[⚠️ WARNING] Sales Order {sin} not found — skipping.")
        return  # stop this SIN, but system keeps running
    
    so_data = models.execute_kw(
        db, uid, password,
        'sale.order', 'read',
        [order_id],
        {'fields': ['sector_id', 'region_id',  'opportunity_id', 'project_mgr']}
)
    project_mgr = so_data[0].get('project_mgr')
    project_mgr_id = project_mgr[0] if project_mgr else False
    
    unit_uom_id = get_UoM(models, db, uid, password)


    sector_id, region_id =  find_sector_region(so_data)

    product_tuples = []
    
    for quotation in data["quotations"]:
        for item in quotation["Items"]:
            part_number = item.get("Part Number")
            sanitized = sanitize_item(item)
            item.update(sanitized)  # ✅ Now item inside quotations is updated

            description = sanitize_xml_string(item.get("Full Description"))

            if not part_number:
                internal_reference= description
            else:
                internal_reference=item.get("Part Number")

            product_id = get_or_create_product(
                internal_reference,
                description,
                item.get("Type"),
                item.get("Category"),
                item.get("Technology"),
            )

            qty = sanitize_float(item.get("Quantity"))
            product_tuples.append( (product_id, qty) )
            item["product_id"] = product_id  
            print(f"[🟢 PRODUCT] Created or found: {internal_reference} → Product ID: {product_id}")
    
    pr_id = get_or_create_pr(sin, order_id, sector_id, region_id)
    product_items = []
    for quotation in data["quotations"]:
        product_items.extend(quotation["Items"])


    add_pr_lines(pr_id, product_items, sector_id, region_id, unit_uom_id)


    # now get the PR name
    pr_data = models.execute_kw(
        db, uid, password,
        'purchase.requisition', 'read',
        [pr_id],
        {'fields': ['name']}
    )
    pr_name = pr_data[0]['name']

    # 5️⃣ for each vendor → create RFQ → add their items
    for quotation in data.get("quotations", []):
        vendor_info = quotation.get("Vendor", {})
        vendor_id = get_or_create_vendor(vendor_info)
        # currency_code = quotation.get("Items", [{}])[0].get("Currency") or "SAR"
        currency_code = get_currency_code(quotation)
        po_id = create_rfq(pr_id, vendor_id, vendor_info, sector_id, region_id, pr_name, project_mgr_id, currency_code)
        apply_standard_note_and_payment_term(po_id)
        add_rfq_lines(po_id, quotation["Items"], sector_id, region_id, unit_uom_id)
        
    patch_so_lines(order_id, sector_id, region_id)
    


