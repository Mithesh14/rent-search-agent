import hashlib
import re

from rentsearch.models import PropertyListing


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def compute_dedupe_key(listing: PropertyListing) -> str:
    if listing.source_id:
        return f"{listing.source}:{listing.source_id}"
    if listing.url:
        return f"url:{_normalize(listing.url)}"
    fingerprint = listing.description_fingerprint()
    fallback = f"{_normalize(listing.address)}|{listing.rent}|{listing.bhk}|{fingerprint}"
    return f"fallback:{hashlib.sha256(fallback.encode('utf-8')).hexdigest()}"


def compute_listing_id(dedupe_key: str) -> str:
    return hashlib.sha256(dedupe_key.encode("utf-8")).hexdigest()[:16]
