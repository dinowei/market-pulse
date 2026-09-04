from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EditorialBlockType(StrEnum):
    FACT = "FACT"
    THIRD_PARTY_CONSENSUS = "THIRD_PARTY_CONSENSUS"
    CONDITIONAL_SCENARIO = "CONDITIONAL_SCENARIO"
    RISK = "RISK"
    LIMITATION = "LIMITATION"


class EditorialStatus(StrEnum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class EditorialSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=200)
    publisher: str = Field(min_length=1, max_length=200)
    url: str | None = Field(default=None, max_length=1000)
    retrieved_at: datetime | None = None
    justification: str | None = Field(default=None, max_length=1000)


class EditorialBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: EditorialBlockType
    text: str = Field(min_length=1, max_length=5000)
    sources: tuple[EditorialSource, ...] = ()
    attribution: str | None = Field(default=None, max_length=500)


class EditorialViolation(BaseModel):
    code: str
    message: str
    block_index: int


class EditorialValidationReport(BaseModel):
    valid: bool
    violations: tuple[EditorialViolation, ...] = ()


_PRESCRIPTIVE = (
    r"\bcompre\b",
    r"\bvenda\s+[A-Z]{2,}\d{1,2}\b",
    r"\bvenda\s+agora\b",
    r"\bvender\s+agora\b",
    r"\bhora\s+de\s+vender\b",
    r"\bmantenha\b",
    r"\bsegure\b",
    r"\baumente\b",
    r"\breduza\b",
    r"\bmonte\b",
    r"\bzer(ar|e|em)\b",
    r"\bentre\s+agora\b",
    r"\bsaia\s+agora\b",
    r"\b(lucro|retorno)\s+garantido\b",
    r"\boportunidade\s+imperdivel\b",
    r"\bsinal\s+de\s+(compra|venda)\b",
    r"\brecomendamos\s+(comprar|vender|a venda)\b",
    r"\bmelhor\s+ativo\s+para\s+comprar\b",
    r"\b(vai|ira)\s+(subir|cair)\b",
)
_CONDITIONAL = re.compile(
    r"\b(se|caso|pode|podem|poderia|poderiam|cenario|hipotese|eventualmente)\b",
    re.IGNORECASE,
)


def _normalized(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()


def _has_prescriptive_language(text: str) -> bool:
    normalized = _normalized(text)
    return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _PRESCRIPTIVE)


def validate_editorial_blocks(
    blocks: tuple[EditorialBlock, ...] | list[EditorialBlock],
) -> EditorialValidationReport:
    violations: list[EditorialViolation] = []
    for index, block in enumerate(blocks):
        if _has_prescriptive_language(block.text):
            violations.append(
                EditorialViolation(
                    code="PRESCRIPTIVE_LANGUAGE",
                    message="Linguagem prescritiva ou promessa de retorno não é publicável.",
                    block_index=index,
                )
            )
        if block.content_type is EditorialBlockType.FACT and not block.sources:
            violations.append(
                EditorialViolation(
                    code="FACT_SOURCE_REQUIRED",
                    message="Bloco FACT exige ao menos uma fonte identificada.",
                    block_index=index,
                )
            )
        if block.content_type is EditorialBlockType.THIRD_PARTY_CONSENSUS:
            if not block.sources:
                violations.append(
                    EditorialViolation(
                        code="CONSENSUS_SOURCE_REQUIRED",
                        message="Consenso de terceiros exige fonte identificada.",
                        block_index=index,
                    )
                )
            if not block.attribution:
                violations.append(
                    EditorialViolation(
                        code="CONSENSUS_ATTRIBUTION_REQUIRED",
                        message="Consenso de terceiros exige atribuição explícita.",
                        block_index=index,
                    )
                )
        if block.content_type is EditorialBlockType.CONDITIONAL_SCENARIO:
            if not _CONDITIONAL.search(block.text):
                violations.append(
                    EditorialViolation(
                        code="SCENARIO_CONDITIONAL_LANGUAGE_REQUIRED",
                        message="Cenário exige linguagem condicional e incerteza explícitas.",
                        block_index=index,
                    )
                )
            if not block.sources:
                violations.append(
                    EditorialViolation(
                        code="SCENARIO_SOURCE_REQUIRED",
                        message="Cenário condicional exige fonte para fatos e premissas.",
                        block_index=index,
                    )
                )
        if block.content_type is EditorialBlockType.RISK and not block.sources:
            violations.append(
                EditorialViolation(
                    code="RISK_SOURCE_REQUIRED",
                    message="Bloco de risco exige fonte ou justificativa rastreável.",
                    block_index=index,
                )
            )
    return EditorialValidationReport(valid=not violations, violations=tuple(violations))
