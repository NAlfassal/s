import json
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Odoo config
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

# Email / Microsoft Graph
CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")  
SCOPES = json.loads(os.getenv("SCOPES", '["Mail.Read","Mail.Send"]'))  # convert string → list
FROM_EMAIL = os.getenv("FROM_EMAIL")

MICROSOFT_CONFIG = {
    "client_id": CLIENT_ID,
    "tenant_id": TENANT_ID,
    "scopes": SCOPES,
}

# OCI
OCI_USER = os.getenv("OCI_USER")
FINGERPRINT = os.getenv("FINGERPRINT")
TENANCY = os.getenv("TENANCY")
REGION = os.getenv("REGION")
KEY_FILE = os.getenv("KEY_FILE")
BUCKET_NAME = os.getenv("BUCKET_NAME")
NAMESPACE = os.getenv("NAMESPACE")
COMPARTMENT_OCID = os.getenv("COMPARTMENT_OCID")

OCI_CONFIG = {
    "user": OCI_USER,
    "fingerprint": FINGERPRINT,
    "tenancy": TENANCY,
    "region": REGION,
    "key_file": KEY_FILE,
    "namespace": NAMESPACE,
    "compartment_id": COMPARTMENT_OCID
}

# LLM
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Feature toggles
ENABLE_CLASSIFICATION = os.getenv("ENABLE_CLASSIFICATION", "False") == "True"
ENABLE_OCR = os.getenv("ENABLE_OCR", "False") == "True"
ENABLE_LLM_EXTRACTION = os.getenv("ENABLE_LLM_EXTRACTION", "False") == "True"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
