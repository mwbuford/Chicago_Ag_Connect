"""
Website Scraper & URL Discovery Service for Farmers Markets, Farm Stands, CSAs, and Local Ag.
Extracts web URLs from address text, descriptions, USDA data fields, and fallback search domains.
"""
import re
import urllib.parse
from typing import Optional, Dict, Any

URL_REGEX = re.compile(
    r'https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)',
    re.IGNORECASE
)

DOMAIN_CLEAN_REGEX = re.compile(r'^(?:https?://)?(?:www\.)?', re.IGNORECASE)

KNOWN_DOMAIN_KEYWORDS = [
    ".org", ".com", ".edu", ".net", ".farm", ".coop", ".gov", "facebook.com", "instagram.com"
]

def extract_url_from_text(text: Optional[str]) -> Optional[str]:
    """Extracts the first valid HTTP/HTTPS URL from any unstructured text block."""
    if not text or not isinstance(text, str):
        return None
    matches = URL_REGEX.findall(text)
    if matches:
        return matches[0]
    
    # Check for raw www. domain references
    for word in text.split():
        clean_word = word.strip("(),;:'\"<>[]")
        if clean_word.lower().startswith("www.") and any(clean_word.lower().endswith(ext) or ext in clean_word.lower() for ext in KNOWN_DOMAIN_KEYWORDS):
            return f"https://{clean_word}"
        if any(clean_word.lower().endswith(ext) for ext in [".org", ".farm", ".coop", ".gov"]) and "/" not in clean_word and len(clean_word) > 5:
            return f"https://{clean_word}"
            
    return None

def generate_web_search_url(name: str, city: str, state_code: str) -> str:
    """Generates an immediate Google Search lookup link in clean format: '{Name} {City} {State}'."""
    parts = [name.strip()]
    if city and city.strip():
        parts.append(city.strip())
    if state_code and state_code.strip():
        parts.append(state_code.strip())
    query = " ".join(parts)
    return f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"

def generate_social_search_url(name: str, state_code: str) -> str:
    """Generates a Facebook / Instagram local producer search fallback."""
    query = f"{name} {state_code}"
    return f"https://www.facebook.com/search/top?q={urllib.parse.quote_plus(query)}"

def enrich_location_website(name: str, city: str, state_code: str, raw_desc: Optional[str] = None, raw_web: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns enriched web presence metadata:
    - website_url: Verified direct URL or None
    - search_url: Google direct search query
    - maps_url: Google Maps directions query
    - domain_label: Clean display text for the website (e.g., 'greencitymarket.org')
    """
    direct_url = extract_url_from_text(raw_web) or extract_url_from_text(raw_desc)
    domain_label = None

    if direct_url:
        try:
            parsed = urllib.parse.urlparse(direct_url)
            domain_label = parsed.netloc.replace("www.", "")
        except Exception:
            domain_label = "Visit Website"

    return {
        "website_url": direct_url,
        "domain_label": domain_label,
        "search_url": generate_web_search_url(name, city, state_code),
        "maps_url": f"https://maps.google.com/?q={urllib.parse.quote_plus(f'{name} {city} {state_code}')}"
    }
