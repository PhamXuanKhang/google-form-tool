from uuid import uuid5, NAMESPACE_DNS

def generate_uuid_from_url(url: str) -> str:
    """
    Generate a deterministic UUID from url.
    
    Parameters:
        url (str): Url to generate UUID from.
    
    Returns:
        str: An 8-character shortened UUID string.
    """
    return uuid5(NAMESPACE_DNS, url).hex[:8]