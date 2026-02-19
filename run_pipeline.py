from config import FINGERPRINT, KEY_FILE, MICROSOFT_CONFIG, OCI_CONFIG, BUCKET_NAME, REGION, TENANCY, OCI_USER
from outlook_to_oci import run_step_one

from oci_to_odoo import (
    classify_file,
    extract_text,
    extract_quotation_data,
    process_quotation_data,
    get_odoo_connection,
    run_step_two_all
)

def run_full_pipeline():
    print("🚀 Starting Full Pipeline\n")
    
    config = {
        "oci": {
            "bucket_name": BUCKET_NAME,
            **OCI_CONFIG
        },
        "microsoft": MICROSOFT_CONFIG
    }
    
    print("\n📥 STEP ONE: Fetching Emails & Uploading Attachments")
    run_step_one(config)
    
    print("\n📂 STEP TWO: Processing Attachments & Pushing to Odoo")
    run_step_two_all(
        config,
        classify_file,
        extract_text,
        extract_quotation_data,
        process_quotation_data,
        get_odoo_connection
    )

    print("\n✅ Full Pipeline Complete")

if __name__ == "__main__":
    run_full_pipeline()