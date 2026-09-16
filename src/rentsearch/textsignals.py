import re
from typing import Optional

# Matches phrases sellers use to advertise a veg-only building. Absence of a match means
# "unknown", not "non-veg allowed" -- most listings simply don't mention food preference.
_VEG_ONLY_RE = re.compile(
    r"only\s+vegetarian|veg(?:etarian)?\s+only|strictly\s+veg(?:etarian)?|"
    r"no\s+non[-\s]?veg|non[-\s]?veg\s+not\s+allowed|vegetarian\s+family\s+only|"
    r"veg\s+family\s+only|pure\s+veg(?:etarian)?\s+only",
    re.IGNORECASE,
)


def detect_veg_only(*texts: Optional[str]) -> Optional[bool]:
    combined = " ".join(t for t in texts if t)
    if _VEG_ONLY_RE.search(combined):
        return False
    return None
