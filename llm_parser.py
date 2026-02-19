import json
import random
import re
import time

from openai import OpenAI, RateLimitError

from config import OPENAI_API_KEY, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

prompt_template = """
You are an intelligent assistant that extracts structured data from procurement documents.
Given the following raw document text, extract and return the structured data in **JSON format** with this schema:
{

"  "Vendor": {
    "name": "",
    "name_ar": "",
    "address": "",
    "short_name": "",
    "vat": "",
    "email": "",
    "phone": "",
    "mobile": "",
    "city": "",
    "zip": "",
    "state": "",
    "country": "",
    "website": "",
    "sector": ""
  },"
  "Items": [
    {
      "Part Number"(Extract only if there’s a true Part Number, SKU or model number, if not omit it): "",
      "Full Description"(including bullet points or multiple lines, if present): "",
      "Quantity"(Extract the number of units (Qty/Quantity), NOT duration, term, days, or any other field. If both appear, use the value from 'Qty' column or the unit count field.): "",
      "Unit Price"(U Price, if only total price is provided, devide by Quantity): "",
      "Currency": "",
      "Type": "",
      "Technology": "",
      "Category": ""
    }
  ]
}

• Include every item in the list, even if the "Part Number" or description is repeated.
• Do NOT merge duplicate Part Numbers — treat each line as a separate quotation entry.
• If any field is missing, omit it.  


• Use ISO codes for Country  
• For "Currency", only use one of the following ISO codes: SAR, USD, EUR, GBP, AED. If the currency is not one of those or unclear, leave it empty.

• Do not add commentary—return ONLY the JSON object.
• For the "Technology" field, infer the technology based on the product description or part number, it should represent the **vendor or platform**

• For the "Type" field, determine the product type based on the description:
  - Use "Service" for anything related to services, installation, support, or training.
  - Use "Storable Product" for tangible items that can be stored in inventory like hardware.
  - Use "Consumable" for software licenses, accessories, or items consumed during use.

• For the "Category" field, infer it based on product description and known keywords:
  - Use "EX - Training" for anything related to training or certification.
  - Use "EX - Support" for support services or maintenance.
  - Use "EX - Products (HW Only)" for physical hardware.
  - Use "EX - PS" for setup, integration, or BoQ-related services.
  - Use "EX - Outsourcing" for staff augmentation or outsourcing resources.
  - Use "EX - MSS" for managed security services or SOC operations.
  - Use "EX - MDS" for general managed services or remote support.
  - Use "EX - License" for software licenses or subscriptions.
  - Use "EX - Consulting" for advisory or strategic consulting.
  

• For the "Vendor" section:
    - Identify the sender of the quotation, not the recipient 
    - If multiple info exist, prefer those **matching the vendor's domain name**.
    - Ignore customer or end-user information, even if it looks complete.
    - If possible, infer the vendor's sector: one of 'government', 'coroporate', or 'non_profit', based on the vendor name, email domain, or associated entities. If unsure, leave it empty
    
Here is the input text:
---
<INSERT RAW QUOTATION TEXT HERE>
"""

def extract_quotation_data(raw_text: str) -> dict:
    prompt = prompt_template.replace("<INSERT RAW QUOTATION TEXT HERE>", raw_text)
    
    max_retries = 5
    response = None

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a smart assistant that extracts procurement data into structured format."},
                    {"role": "user", "content": prompt}
                ]
            )
            break  # success
           
        except RateLimitError as e:
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            print(f"[⏳ Retry {attempt+1}] Rate limit hit — waiting {wait_time:.2f} seconds...")
            time.sleep(wait_time)
            
        except Exception as e:
            print(f"[❌ ERROR] Failed to call OpenAI API: {e}")
            return {}

    if not response:
        print("[🚫 Failed] No response from OpenAI.")
        return {}
  
    result_text = response.choices[0].message.content.strip()

    # 🔧 Strip triple backticks if present
    if result_text.startswith("```"):
        result_text = re.sub(r"^```(json)?", "", result_text)
        result_text = result_text.rstrip("`").strip()

    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        print("[⚠️ WARNING] Response not in JSON format")
        return {"raw_response": result_text}

