from abc import ABC, abstractmethod
from typing import List

from rentsearch.models import PropertyListing


class ListingSource(ABC):
    name: str

    @abstractmethod
    def fetch(self, config: dict) -> List[PropertyListing]:
        """Return normalized PropertyListing objects for this source.
        Implementations should let network/parse errors propagate; callers (fetch.py)
        are responsible for isolating one source's failure from the others."""
        raise NotImplementedError
