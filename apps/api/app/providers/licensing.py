from dataclasses import dataclass
from enum import StrEnum

from app.providers.models import DataLevel, ProviderCapability, ProviderDatasetRef


class LicenseDecision(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class DatasetAccessRequest:
    dataset: ProviderDatasetRef
    capability: ProviderCapability
    purpose: str
    modality: str
    environment: str
    data_level: DataLevel
    plan: str | None = None


@dataclass(frozen=True)
class DatasetAccessDecision:
    decision: LicenseDecision
    code: str
    reason: str

    @property
    def allowed(self) -> bool:
        return self.decision is LicenseDecision.ALLOW


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

    def decide_access(self, request: DatasetAccessRequest) -> DatasetAccessDecision:
        dataset = request.dataset
        dimensions = {
            "provider": dataset.provider,
            "plan": dataset.plan or request.plan,
            "endpoint": dataset.endpoint,
            "dataset": dataset.dataset,
            "purpose": dataset.purpose,
            "modality": dataset.modality,
            "environment": dataset.environment,
        }
        if any(value is None or value == "" for value in dimensions.values()):
            return DatasetAccessDecision(
                LicenseDecision.BLOCK,
                "LICENSE_DIMENSION_MISSING",
                "all licensing dimensions are required",
            )
        if dataset.endpoint != request.capability.value:
            return DatasetAccessDecision(
                LicenseDecision.BLOCK,
                "LICENSE_ENDPOINT_MISMATCH",
                "dataset endpoint is not approved for requested capability",
            )
        if dataset.purpose != request.purpose or dataset.modality != request.modality:
            return DatasetAccessDecision(
                LicenseDecision.BLOCK,
                "LICENSE_PURPOSE_MISMATCH",
                "dataset purpose or modality is not approved",
            )
        if dataset.environment != request.environment:
            return DatasetAccessDecision(
                LicenseDecision.BLOCK,
                "LICENSE_ENVIRONMENT_MISMATCH",
                "dataset environment is not approved",
            )
        if dataset.license_status != "PUBLIC_APPROVED":
            return DatasetAccessDecision(
                LicenseDecision.BLOCK,
                "LICENSE_STATUS_BLOCKED",
                "dataset is not approved for the requested data level",
            )
        if not dataset.public_approved or not dataset.evidence:
            return DatasetAccessDecision(
                LicenseDecision.BLOCK,
                "LICENSE_EVIDENCE_MISSING",
                "public approval evidence is missing",
            )
        return DatasetAccessDecision(LicenseDecision.ALLOW, "LICENSE_ALLOWED", "approved")
