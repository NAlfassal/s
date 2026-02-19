import oci

# --- OCI Helpers ---
def get_oci_client(config):
    return oci.object_storage.ObjectStorageClient(config)

def get_namespace(client):
    return client.get_namespace().data
