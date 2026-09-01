from enum import StrEnum

from app.providers.models import ProviderDatasetRef


class LicenseDecision(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


class LicenseService:
    """Fail-closed public-use decision for provider datasets."""

    def decide(self, dataset: ProviderDatasetRef | None) -> LicenseDecision:
        if dataset is None:
            return LicenseDecision.BLOCK
        if dataset.license_status != "PUBLIC_APPROVED":
            return LicenseDecision.BLOCK
        if not dataset.public_approved or not dataset.evidence:
            return LicenseDecision.BLOCK
        return LicenseDecision.ALLOW
