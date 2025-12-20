import uuid

def generate_uuid_from_url(url: str) -> str:
    """
    Generate a UUID based on the given URL using UUID5.
    
    Args:
        url (str): The URL to generate the UUID from
        
    Returns:
        str: The generated UUID as a string
    """
    namespace = uuid.NAMESPACE_URL
    return str(uuid.uuid5(namespace, url))