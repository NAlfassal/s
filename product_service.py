from Post_processing.business_rules import map_product_type, validate_category
from odoo_services.utils import get_odoo_connection

models, db, uid, password = get_odoo_connection()

def get_or_create_technology(name):
    tech_ids = models.execute_kw(
        db, uid, password,
        'x_technology', 'search',
        [[['x_name', '=', name]]],  
        {'limit': 1}
    )
    
    if tech_ids:
        print(f"[✔️ Found] Technology '{name}' with ID: {tech_ids[0]}")
        return tech_ids[0]
    else:
        tech_id = models.execute_kw(
            db, uid, password,
            'x_technology', 'create',
            [{'x_name': name}]
        )
        print(f"[✅ Created] Technology '{name}' with ID: {tech_id}")
        return tech_id

def get_or_create_product(part_number, description, product_type, category_name, technology_name):
    
    tmpl_ids = models.execute_kw(
        db, uid, password,
        'product.template', 'search',
        [[['default_code', '=', part_number]]]
    )
    if tmpl_ids:
        product_ids = models.execute_kw(
            db, uid, password,
            'product.product', 'search',
            [[['product_tmpl_id', '=', tmpl_ids[0]]]]
        )
        return product_ids[0]
    
    # Only create technology if provided
    technology_id = None
    if technology_name:
        technology_id = get_or_create_technology(technology_name)

    odoo_type = map_product_type(product_type, "consu")
    
    valid_category = validate_category(category_name)

    # Step 3: Search category (we assume it's pre-defined and valid)
    category_id = None
    if valid_category:
        category_ids = models.execute_kw(
            db, uid, password,
            'product.category', 'search',
            [[['name', '=', valid_category]]]
        )
        if category_ids:
            category_id = category_ids[0]
            
            
            
        data = {
            'name': description,
            'default_code': part_number,
            'type': odoo_type,
            'list_price': 1.0,
            'standard_price': 0.0,
            'sale_ok': True,
            'purchase_ok': False,
            'categ_id': category_id
        }

        if technology_id is not None:
            data['x_technology_id'] = technology_id
                    

        # Remove all None values from the dict before pushing to Odoo
        data = {k: v for k, v in data.items() if v is not None}

        tmpl_id = models.execute_kw(
            db, uid, password,
            'product.template', 'create',
            [data]
        )

    product_ids = models.execute_kw(
        db, uid, password,
        'product.product', 'search',
        [[['product_tmpl_id', '=', tmpl_id]]]
    )
    print(f"[✅ PRODUCT CREATED] Template ID: {tmpl_id}, Product ID: {product_ids[0]}")

    return product_ids[0]

