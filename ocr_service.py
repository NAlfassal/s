from time import sleep
from oci.ai_document import AIServiceDocumentClient
from oci.ai_document.models import AnalyzeDocumentDetails, ObjectStorageDocumentDetails, DocumentTextExtractionFeature
from oci.exceptions import ServiceError


def oracle_extract_text_oci_object(obj_path, oci_cfg, retries=2):

    client = AIServiceDocumentClient(oci_cfg)
    # Input document in Object Storage
    document = ObjectStorageDocumentDetails(
        source="OBJECT_STORAGE",
        namespace_name=oci_cfg["namespace"],
        bucket_name=oci_cfg["bucket_name"],
        object_name=obj_path
    )    
    details = AnalyzeDocumentDetails(
        document=document,
        features=[DocumentTextExtractionFeature()],
        document_type="OTHERS",
        compartment_id=oci_cfg["compartment_id"]
    )
    response = client.analyze_document(analyze_document_details=details)

    for attempt in range(retries + 1):
        try:
            response = client.analyze_document(analyze_document_details=details)
            lines = []
            for page in (response.data.pages or []):
                for ln in (page.lines or []):
                    if ln.text:
                        lines.append(ln.text)
            final_text = "\n".join(lines).strip()
            print(f"\n📝 Reconstructed OCR Text: {final_text}")
            return final_text
        except ServiceError as e:
            # retry only on transient server-side errors
            if e.status in (500, 502, 503, 504) and attempt < retries:
                sleep(1.0 * (attempt + 1))
                continue
            raise
