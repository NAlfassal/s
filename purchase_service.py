import datetime
from Post_processing.business_rules import safe_price, sanitize_float, sanitize_xml_string
from odoo_services.utils import get_odoo_connection, currency

models, db, uid, password = get_odoo_connection()

def get_or_create_pr(sin, order_id, sector_id, region_id):
    # look for existing PR linked to this SO
    pr_ids = models.execute_kw(
        db, uid, password,
        'purchase.requisition', 'search',
        [[['origin', '=', sin]]],
        {'limit': 1}
    )

    if pr_ids:
        pr_id = pr_ids[0]
        print(f"[✔️ PR FOUND] PR ID: {pr_id}")
    else:
              
        pr_id = models.execute_kw(
            db, uid, password,
            'purchase.requisition', 'create',
            [{
                'origin': sin,
                'name': f"PR for {sin}",
                'ordering_date': datetime.date.today().isoformat(),
                'sale_order_id': order_id,
                'sector_id': sector_id,
                'region_id': region_id
            }]
        )
        print(f"[✅ PR CREATED] PR ID: {pr_id}")
        
    return pr_id

def add_pr_lines(pr_id, items, sector_id, region_id, unit_uom_id):

    for item in items:
        product_id = item.get("product_id")
        if not product_id:
            print(f"[⚠️ Skipping] Missing product_id for item: {item}")
            continue

        qty = sanitize_float(item.get("Quantity"))

        product_data = models.execute_kw(
            db, uid, password,
            'product.product', 'read',
            [product_id],
            {'fields': ['name']}
        )
        product_name = sanitize_xml_string(product_data[0]['name'])

        data = {
            'product_id': product_id,
            'requisition_id': pr_id,
            'product_qty': qty,
            'price_unit': 0.0,
            'name': product_name,
            'product_description': product_name,
            'sector_id': sector_id,
            'region_id': region_id,
            'product_uom_id': unit_uom_id
        }

        data = {k: v for k, v in data.items() if v is not None}

        models.execute_kw(
            db, uid, password,
            'purchase.requisition.line', 'create',
            [data]
        )
        print(f"[➕ PR LINE ADDED] Product ID {product_id} qty={qty} to PR {pr_id}")

def create_rfq(pr_id, vendor_id, vendor_name, sector_id, region_id, pr_name, project_mgr_id, currency_code):
    
    currency_id = currency(models, db, uid, password, currency_code)
    
    data = {
            'partner_id': vendor_id,
            'requisition_id': pr_id,
            'sector_id': sector_id,
            'region_id': region_id,
            'origin': pr_name,
            'partner_ref': pr_name,  
            'user_id': project_mgr_id,
            'currency_id': currency_id
        }
    
         # 🚨 Clean: Remove keys with None to avoid marshaling errors
    data = {k: v for k, v in data.items() if v is not None}
   
    po_id = models.execute_kw(
        db, uid, password,
        'purchase.order', 'create',
        [data]
    )
    print(f"[✅ RFQ Created] for {vendor_name} → RFQ ID: {po_id}")
    return po_id


def add_rfq_lines(po_id, product_items, sector_id, region_id, unit_uom_id):

    # Step 1: Get tax ID
    vat_tax_ids = models.execute_kw(
        db, uid, password,
        'account.tax', 'search',
        [[['name', 'ilike', 'VAT goods Purchases-STD - 15% ']]],
        {'limit': 1}
                    )
    
    vat_tax_id = vat_tax_ids[0] if vat_tax_ids else False
    if not vat_tax_id:
        raise Exception("VAT tax not found")

    # Collect all line commands
    commands = []

    for item in product_items:
      
        product_id = item.get("product_id")
        if not product_id:
            print(f"[⚠️ Skipping] Missing product_id for item: {item}")
            continue
        qty = sanitize_float(item.get("Quantity"))
        price_unit = sanitize_float(item.get("Unit Price"))
        price_unit = safe_price(price_unit)

        product_data = models.execute_kw(
            db, uid, password,
            'product.product', 'read',
            [product_id],
            {'fields': ['name']}
        )
        name = sanitize_xml_string(product_data[0]['name'])

        vals = {
            'product_id': product_id,
            'name': name,
            'product_qty': qty,
            'price_unit': price_unit,
            'date_planned': datetime.date.today().isoformat(),
            'product_uom': unit_uom_id,
            'sector_id': sector_id,
            'region_id': region_id,
        }
        if vat_tax_id:
            vals['taxes_id'] = [(6, 0, [vat_tax_id])]

        # remove None
        vals = {k: v for k, v in vals.items() if v is not None}
        commands.append((0, 0, vals))

    if not commands:
        print("[ℹ️] No RFQ lines to add.")
        return

    try:
        models.execute_kw(
            db, uid, password,
            'purchase.order', 'write',
            [[po_id], {'order_line': commands}]
        )
        print(f"[➕ RFQ LINES ADDED] {len(commands)} lines → PO {po_id}")
    except Exception as e:
        print(f"[❌ Failed to add RFQ lines] PO {po_id} → {e}")
        
def apply_standard_note_and_payment_term(po_id, term_name='2 Months'):
    # Define standard note
    note_text = """
    1- Delivery: As Agreed.
    2- Invoicing: Upon Delivery Confirmation.
    3- Payment: 60 Days from invoicing.
    4- No partial invoicing accepted.
    5- No partial delivery accepted.
    6- No Invoice will be accepted without any delivery proof.

    Note: All Invoices & Delivery related information must be shared in the same email thread of PO issuance.
    """.strip()

    # Search for payment term by name
    payment_terms = models.execute_kw(
        db, uid, password,
        'account.payment.term', 'search_read',
        [[['name', '=', term_name]]],
        {'fields': ['id'], 'limit': 1}
    )

    if not payment_terms:
        print(f"[⚠️ Warning] Payment term '{term_name}' not found. Skipping.")
        return

    term_id = payment_terms[0]['id']

    # Update PO
    models.execute_kw(
        db, uid, password,
        'purchase.order', 'write',
        [[po_id], {'notes': note_text, 'payment_term_id': term_id}]
    )
    print(f"[✅ Applied] Standard note and payment term '{term_name}' to PO {po_id}")
