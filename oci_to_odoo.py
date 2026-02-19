import json
import os
from Preprocessing.ocr_service import oracle_extract_text_oci_object
from config import CLIENT_ID, SCOPES, TENANT_ID
from llm_services.llm_parser import extract_quotation_data
from oci_utils import get_namespace, get_oci_client
from odoo_services.quotation_pipeline import process_quotation_data
from odoo_services.sales_order_service import get_sales_order
from odoo_services.utils import get_odoo_connection
from Preprocessing.doc_classifier import classify_file
from Preprocessing.extractor import extract_text
from collections import defaultdict
import tempfile
import oci
from odoo_to_outlook import get_email_json_by_id, reply_to_email
from outlook_to_oci import get_outlook_token

def list_unprocessed_so_folders(bucket_name, config):
    client = get_oci_client(config)
    namespace = get_namespace(client)
    response = client.list_objects(namespace, bucket_name, prefix="attachments/unprocessed/", fields="name", delimiter="/")
    return [prefix.strip("/").split("/")[-1] for prefix in response.data.prefixes]  # ['SO3977', 'SO4210', ...]

def list_unprocessed_files(bucket_name, so_folder, config):
    client = get_oci_client(config)
    namespace = get_namespace(client)
    prefix = f"attachments/unprocessed/{so_folder}/"
    files = client.list_objects(namespace, bucket_name, prefix=prefix).data.objects
    return [f.name for f in files if f.name.endswith((".pdf", ".png", ".jpg"))]

def download_file_from_oci(object_name, config, bucket_name):
    client = get_oci_client(config)
    namespace = get_namespace(client)
    obj = client.get_object(namespace, bucket_name, object_name)
    tmp_path = os.path.join(tempfile.gettempdir(), os.path.basename(object_name))
    with open(tmp_path, "wb") as f:
        f.write(obj.data.content)
    return tmp_path

def move_attachment_to_processed(bucket_name, file_path, config):
    client = get_oci_client(config)
    namespace = get_namespace(client)
    processed_path = file_path.replace("unprocessed/", "processed/")
    
    # Copy then delete
    obj = client.get_object(namespace, bucket_name, file_path)
    client.put_object(namespace, bucket_name, processed_path, obj.data.content)
    client.delete_object(namespace, bucket_name, file_path)

# ---- Multi thread issue ------

def oci_file_exists(bucket_name, object_name, oci_cfg):
    client = get_oci_client(oci_cfg)
    namespace = get_namespace(client)
    try:
        client.get_object_metadata(namespace, bucket_name, object_name)
        return True
    except Exception:
        return False

def put_dummy_file(bucket_name, object_name, oci_cfg):
    client = get_oci_client(oci_cfg)
    namespace = get_namespace(client)

    # Only create if it doesn't already exist (ensures atomicity)
    try:
        client.put_object(
            namespace,
            bucket_name,
            object_name,
            b"lock",
            if_none_match="*"
        )
        return True
    except oci.exceptions.ServiceError as e:
        if e.status == 412:  # Precondition failed, object already exists
            return False
        else:
            raise

def delete_file(bucket_name, object_name, oci_cfg):
    client = get_oci_client(oci_cfg)
    namespace = get_namespace(client)
    try:
        client.delete_object(namespace, bucket_name, object_name)
    except oci.exceptions.ServiceError as e:
        if e.status != 404:
            raise

def run_step_two_all(config, classify_file, extract_text, extract_quotation_data, process_quotation_data, get_odoo_connection):
    bucket_name = config["oci"]["bucket_name"]
    oci_cfg = config["oci"]
    ms = config["microsoft"]
    so_folders = list_unprocessed_so_folders(bucket_name, oci_cfg)

    print(f"📦 Found {len(so_folders)} SO folders: {so_folders}")

    models, db, uid, password = get_odoo_connection()

    for so_folder in so_folders:

        try:
                so_number, email_id = so_folder.split("_", 1)
        except ValueError:
            print(f"[⚠️ Skipping] Invalid folder name: {so_folder}")
            continue

        print(f"\n🔍 Processing SO Folder: {so_folder} (SO={so_number}, Email ID={email_id})")

        # 🔒 Attempt to acquire lock atomically
        lock_path = f"attachments/locks/{so_folder}.lock"
        acquired = put_dummy_file(bucket_name, lock_path, oci_cfg)
        if not acquired:
            print(f"🔒 Skipping {so_folder} — already being processed")
            continue
  
        try:

            # ✅ Skip SOs not found in Odoo
            order_id = get_sales_order(so_number)
            if not order_id:
                print(f"[⚠️ WARNING] Sales Order {so_number} not found — skipping.")
                continue
            
            all_files = list_unprocessed_files(bucket_name, so_folder, oci_cfg)
            grouped_by_sin = defaultdict(list)

            for obj_path in all_files:
                filename = os.path.basename(obj_path)
                local_file = download_file_from_oci(obj_path, oci_cfg, bucket_name)
                file_type = classify_file(local_file)
                
                print(f"📄 {filename} → {file_type}")
                
                if file_type == ("PDF (text-based)"):
                    extracted = extract_text(local_file)
                    
                elif file_type == ("PDF (scanned/image)"):
                    # Skip local OCR; use Oracle directly on the object in OCI
                    extracted = oracle_extract_text_oci_object(obj_path, oci_cfg) #download from object storage                    
                else:
                    print(f"[⚠️ Unsupported or error type] {filename} → {file_type}")
                    continue          
                structured_data = extract_quotation_data(extracted)
                print(f"[✅ llm] {structured_data}")

                if structured_data and "Items" in structured_data and "Vendor" in structured_data:
                    grouped_by_sin[so_number].append(structured_data)
                    print(f"[✅ Processed] {filename}")
                else:
                    print(f"[⚠️ Invalid structure] {filename}")


            if not grouped_by_sin[so_number]:
                print(f"🚫 No valid quotations for {so_number}. Skipping push.")
                continue

            # Push to Odoo
            payload = {
                "SIN": so_number,
                "quotations": grouped_by_sin[so_number]
            }

            print(f"🚀 Pushing {len(payload['quotations'])} to Odoo for {so_number}")
            process_quotation_data(payload)
            
            
            access_token = get_outlook_token(
                client_id=ms["client_id"],
                tenant_id=ms["tenant_id"],
                scopes=ms["scopes"]
            )
            email_json = get_email_json_by_id(so_folder, oci_cfg)

            sender_name = email_json["from_name"]
            print(f"sender name {sender_name}")

            num_of_attachment = len(all_files)
            
            reply_to_email(
                sender_name,
                num_of_attachment,
                so_number,
                original_message_id=email_json["id"],  
                access_token=access_token,
            )
        
            # ✅ After successful push, move all related files to "processed"
            for obj_path in all_files:
                move_attachment_to_processed(bucket_name, obj_path, oci_cfg)
                print(f"[📂 Moved] {os.path.basename(obj_path)} to processed")
                
            # Save payload
            result_path = f"emails/processed/{so_number}_grouped.json"
            client = get_oci_client(oci_cfg)
            namespace = get_namespace(client)
            client.put_object(namespace, bucket_name, result_path, json.dumps(payload, indent=2).encode("utf-8"))
            print(f"[💾 Saved] {result_path}")
            
        except Exception as e:
            print(f"[❌ Failed] {e}")
        finally:
            # ✅ Always release lock even if there's an error
            delete_file(bucket_name, lock_path, oci_cfg)
            print(f"🔓 Lock released for {so_number}")

    print("✅ Attachment pipeline complete.")


