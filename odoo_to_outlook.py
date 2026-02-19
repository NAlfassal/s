import json
from oci_utils import get_namespace, get_oci_client
import requests

def get_email_json_by_id(email_id, oci_cfg):
    client = get_oci_client(oci_cfg)
    namespace = get_namespace(client)
    bucket = oci_cfg["bucket_name"]
    path = f"emails/raw/{email_id}.json"
    
    try:
        response = client.get_object(namespace, bucket, path)
        return json.loads(response.data.text)
    except Exception as e:
        print(f"[⚠️ Could not fetch email JSON] {email_id}: {e}")
        return None

def reply_to_email(sender_name, num_of_attachment, so_number, original_message_id, access_token):
    
    first_name = sender_name.split()[0] if sender_name else "Valued Customer"
        
    attachment_info = "quotation has" if num_of_attachment == 1 else f"{num_of_attachment} quotations have"

    # 📨 Clean HTML body
    reply_body = f"""
    <p>Dear <strong>{first_name}</strong>,</p>

    <p>Thank you for your submission.</p>

    <p>Your {attachment_info} been successfully received and processed for <strong>{so_number}</strong> in Odoo.</p>

    <p>The associated Purchase Order (PO) has been created, and all relevant items have been added accordingly.</p>

    <p>Best regards,<br>Sales Bot</p>
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Step 1: Create the reply draft
    create_reply_url = f"https://graph.microsoft.com/v1.0/me/messages/{original_message_id}/createReply"
    response = requests.post(create_reply_url, headers=headers)

    if response.status_code != 201:
        print(f"[❌ Failed to create reply] {response.status_code} — {response.text}")
        return

    draft = response.json()
    draft_id = draft["id"]

    # Step 2: Update the reply body
    update_url = f"https://graph.microsoft.com/v1.0/me/messages/{draft_id}"
    update_body = {
        "body": {
            "contentType": "HTML",  
            "content": reply_body
        }
    }
    update_resp = requests.patch(update_url, headers=headers, json=update_body)
    if update_resp.status_code != 200:
        print(f"[❌ Failed to update reply] {update_resp.status_code} — {update_resp.text}")
        return

    # Step 3: Send the reply
    send_url = f"https://graph.microsoft.com/v1.0/me/messages/{draft_id}/send"
    send_resp = requests.post(send_url, headers=headers)
    if send_resp.status_code == 202:
        print(f"[📧 Sent] Reply to original email {original_message_id}")
    else:
        print(f"[❌ Failed to send reply] {send_resp.status_code} — {send_resp.text}")
