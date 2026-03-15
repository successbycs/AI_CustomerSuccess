"""Vendor intelligence extraction schema.

This module defines the schema used to represent extracted vendor intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class VendorIntelligence:
    vendor_name: str
    website: str
    icp: List[str] = field(default_factory=list)
    case_studies: List[str] = field(default_factory=list)
    value_statements: List[str] = field(default_factory=list)
    pricing: List[str] = field(default_factory=list)

    def validate(self) -> None:
        """Validate the schema structure and types.

        Raises:
            TypeError: If any field is missing or has an unexpected type.
        """
        if not isinstance(self.vendor_name, str):
            raise TypeError("vendor_name must be a string")
        if not isinstance(self.website, str):
            raise TypeError("website must be a string")

        for field_name in ["icp", "case_studies", "value_statements", "pricing"]:
            value = getattr(self, field_name)
            if not isinstance(value, list):
                raise TypeError(f"{field_name} must be a list")
            if not all(isinstance(item, str) for item in value):
                raise TypeError(f"All items in {field_name} must be strings")


def extract_vendor_intelligence(homepage_payload: dict) -> VendorIntelligence:
    """Convert a homepage payload into a VendorIntelligence object.

    This MVP implementation keeps extraction simple and only maps the
    fields that are already available in the homepage payload.
    """

    return VendorIntelligence(
        vendor_name=homepage_payload["vendor_name"],
        website=homepage_payload["website"],
    )
