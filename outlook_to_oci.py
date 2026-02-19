import json
import requests
import base64
import hashlib
import oci
import os
from msal import PublicClientApplication, SerializableTokenCache
from tempfile import NamedTemporaryFile
from PIL import Image
from oci_utils import get_namespace, get_oci_client

# def get_outlook_token(client_id, tenant_id, scopes):
#     authority = f"https://login.microsoftonline.com/{tenant_id}"
#     app = PublicClientApplication(client_id, authority=authority)
#     result = app.acquire_token_interactive(scopes)
#     return result['access_token']

# === AUTH ===
def get_outlook_token(client_id, tenant_id, scopes, cache_path="token_cache.json"):
    authority = f"https://login.microsoftonline.com/{tenant_id}"

    # Load token cache from file if exists
    cache = SerializableTokenCache()
    if os.path.exists(cache_path):
        cache.deserialize(open(cache_path, "r").read())

    app = PublicClientApplication(client_id, authority=authority, token_cache=cache)

    # Try to acquire token silently
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if result:
            return result['access_token']

    # Fallback to device code flow
    flow = app.initiate_device_flow(scopes=scopes)
    if 'user_code' not in flow:
        raise Exception("Device flow initiation failed")

    print(f"\n🔑 To sign in, use a web browser to open:\n{flow['verification_uri']}")
    print(f"And enter the code: {flow['user_code']}\n")

    result = app.acquire_token_by_device_flow(flow)

    # Save updated cache
    if cache.has_state_changed:
        with open(cache_path, "w") as f:
            f.write(cache.serialize())

    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Failed to acquire token: {result}")

# === METADATA TRACKING ===
# def generate_email_uid(email_id):
#     return hashlib.sha256(email_id.encode()).hexdigest()[:12]

def get_processed_ids(bucket_name, config):
    client = get_oci_client(config)
    namespace = get_namespace(client)
    object_name = "metadata/processed_emails.json"
    try:
        obj = client.get_object(namespace, bucket_name, object_name)
        content = obj.data.content.decode("utf-8")
        return set(json.loads(content).get("ids", []))
    except oci.exceptions.ServiceError as e:
        if e.status == 404:
            return set()
        else:
            raise

def save_processed_ids(bucket_name, config, processed_ids):
    client = get_oci_client(config)
    namespace = get_namespace(client)
    object_name = "metadata/processed_emails.json"
    content = json.dumps({"ids": list(processed_ids)}, indent=2)
    client.put_object(namespace, bucket_name, object_name, content.encode("utf-8"))

def load_last_processed_time(bucket_name, config):
    client = get_oci_client(config)
    namespace = get_namespace(client)
    object_name = "metadata/last_processed_time.txt"
    try:
        obj = client.get_object(namespace, bucket_name, object_name)
        return obj.data.content.decode("utf-8").strip()
    except oci.exceptions.ServiceError as e:
        if e.status == 404:
            return None
        else:
            raise

def save_last_processed_time(bucket_name, config, latest_timestamp):
    client = get_oci_client(config)
    namespace = get_namespace(client)
    object_name = "metadata/last_processed_time.txt"
    client.put_object(namespace, bucket_name, object_name, latest_timestamp.encode("utf-8"))

# === EMAIL FETCHING ===
def fetch_emails(access_token, since_iso_datetime=None):
    headers = {'Authorization': f'Bearer {access_token}'}
    url = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top=50"
    if since_iso_datetime:
        url += f"&$filter=receivedDateTime ge {since_iso_datetime}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch emails: {response.text}")
    return response.json().get("value", [])

def fetch_attachments(email_id, headers):
    url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}/attachments"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch attachments for {email_id}: {response.text}")
        return []
    return response.json().get("value", [])

# === ATTACHMENT HANDLING ===
def extract_so_number(subject):
    return subject.upper()

def upload_attachment_to_oci(attachment, so_number, bucket_name, config, email_id):
    if attachment.get("@odata.type") != "#microsoft.graph.fileAttachment":
        return None

    filename = attachment.get("name", "unnamed_file")
    content_base64 = attachment.get("contentBytes")
    binary_data = base64.b64decode(content_base64)
    
    # Extract file extension
    ext = os.path.splitext(filename)[-1].lower()
    
    client = get_oci_client(config)
    namespace = get_namespace(client)

    # Convert image formats (png, jpg) to PDF before upload
    if ext in [".png", ".jpg", ".jpeg"]:
        with NamedTemporaryFile(suffix=ext) as temp_image_file:
            temp_image_file.write(binary_data)
            temp_image_file.flush()
            image = Image.open(temp_image_file.name).convert("RGB")
            with NamedTemporaryFile(suffix=".pdf") as temp_pdf_file:
                image.save(temp_pdf_file.name, "PDF")
                temp_pdf_file.seek(0)
                binary_data = temp_pdf_file.read()
                filename = filename.rsplit(".", 1)[0] + ".pdf"  # rename as .pdf

    object_name = f"attachments/unprocessed/{so_number}_{email_id}/{email_id}_{filename}"
    client.put_object(namespace, bucket_name, object_name, binary_data)
    return filename

def upload_all_attachment_to_oci(attachment, so_number, bucket_name, config, email_id):
    if attachment.get("@odata.type") != "#microsoft.graph.fileAttachment":
        return None

    filename = attachment.get("name", "unnamed_file")
    content_base64 = attachment.get("contentBytes")
    binary_data = base64.b64decode(content_base64)
    
    object_name = f"attachments/all_attachments/{so_number}/{email_id}_{filename}"
    client = get_oci_client(config)
    namespace = get_namespace(client)
    client.put_object(namespace, bucket_name, object_name, binary_data)
    return filename

def upload_email_metadata(email, so_number, bucket_name, config, email_uid):
    subject = email.get("subject", "No Subject")
    sender_info = email.get("from", {}).get("emailAddress", {})
    sender_name = sender_info.get("name", "Unknown Name")
    sender_email = sender_info.get("address", "Unknown")
    received = email.get("receivedDateTime", "")
    body = email.get("bodyPreview", "No Body")

    content = {
        "id": email["id"],
        "subject": subject,
        "from": sender_email,
        "from_name": sender_name,
        "received": received,
        "body": body
    }
    filename = f"emails/raw/{so_number}_{email_uid}.json"
    client = get_oci_client(config)
    namespace = get_namespace(client)
    client.put_object(namespace, bucket_name, filename, json.dumps(content, indent=2).encode("utf-8"))

# === MAIN STEP ONE FUNCTION ===
def run_step_one(config):
    oci_cfg = config["oci"]
    ms = config["microsoft"]
    bucket_name = oci_cfg["bucket_name"]

    token = get_outlook_token(
        client_id=ms["client_id"],
        tenant_id=ms["tenant_id"],
        scopes=ms["scopes"]
    )
    headers = {'Authorization': f'Bearer {token}'}
    last_time = load_last_processed_time(bucket_name, oci_cfg)
    processed_ids = get_processed_ids(bucket_name, oci_cfg)

    emails = fetch_emails(token, since_iso_datetime=last_time)
    print(f"📥 Found {len(emails)} emails")

    new_ids = set(processed_ids)
    latest_seen = last_time

    for email in emails:
        email_id = email["id"]
        if email_id in processed_ids:
            continue

        subject = email.get("subject", "")
        so_number = extract_so_number(subject)
        if not so_number:
            continue

        # uid = generate_email_uid(email_id)
        upload_email_metadata(email, so_number, bucket_name, oci_cfg, email_id)

        attachments = fetch_attachments(email_id, headers)
        for a in attachments:
            uploaded = upload_attachment_to_oci(a, so_number, bucket_name, oci_cfg, email_id)
            uploaded = upload_all_attachment_to_oci(a, so_number, bucket_name, oci_cfg, email_id)
            if uploaded:
                print(f"📎 Uploaded {uploaded} for SO {so_number}")

        new_ids.add(email_id)
        rcv = email.get("receivedDateTime")
        if rcv and (not latest_seen or rcv > latest_seen):
            latest_seen = rcv

    save_processed_ids(bucket_name, oci_cfg, new_ids)
    if latest_seen:
        save_last_processed_time(bucket_name, oci_cfg, latest_seen)
    print("✅ Step One Complete")

