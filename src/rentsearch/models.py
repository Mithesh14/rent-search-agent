import hashlib
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class PropertyListing:
    source: str
    url: str
    title: str
    locality: str
    address: str
    rent: int
    source_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    deposit: Optional[int] = None
    maintenance: Optional[int] = None
    bhk: Optional[int] = None
    property_type: str = "unknown"
    age_years: Optional[int] = None
    parking: str = "unknown"
    furnishing: Optional[str] = None
    bathrooms: Optional[int] = None
    description_raw: str = ""
    posting_date: Optional[str] = None

    def description_hash(self) -> str:
        normalized = re.sub(r"\s+", " ", self.description_raw or "").strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def description_fingerprint(self, length: int = 500) -> str:
        normalized = re.sub(r"\s+", " ", self.description_raw or "").strip().lower()
        return hashlib.sha256(normalized[:length].encode("utf-8")).hexdigest()
