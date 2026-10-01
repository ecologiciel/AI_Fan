from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from app.editorial.types import EditorialPackage
from app.providers.llm.models import LLMGenerationRequest

PREMATCH_SCRIPT_V1 = "prematch_script_v1"
POSTMATCH_SCRIPT_V1 = "postmatch_script_v1"
HOOK_V1 = "hook_v1"
FACT_REPAIR_V1 = "fact_repair_v1"

SYSTEM_PROMPT_V1 = """You are a football short-form scriptwriter, never a statistical source.
Use ONLY claims and numbers supplied in EVIDENCE. Never create a statistic.
Never turn a correlation into causal certainty. Omit a claim if its proof is insufficient.
Never add an injury, quote, rumor, transfer, or information absent from the input.
The supporter may be emotional; factual statements must remain exact.
Start immediately with a hook; never begin with 'Hola chicos', 'Bienvenidos',
or a generic introduction.
Respect the target word-count range. Write in the requested language, locale, and fan register.
Each numeric segment must reference its EVIDENCE ids. List every football entity
mentioned in mentioned_entities.
Avoid corporate phrasing, personal insults, unverified accusations, and generic calls to subscribe.
"""


def prompt_version_for(content_type: str) -> str:
    return PREMATCH_SCRIPT_V1 if content_type == "PRE_MATCH" else POSTMATCH_SCRIPT_V1


def build_evidence_manifest(package: EditorialPackage) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for insight_index, insight in enumerate(package.insights, start=1):
        for evidence_index, raw in enumerate(insight.evidence, start=1):
            evidence = dict(raw) if isinstance(raw, dict) else {"value": raw}
            evidence["evidence_id"] = f"EV-{insight_index:02d}-{evidence_index:02d}"
            evidence["insight_id"] = str(insight.id)
            evidence["claim"] = insight.claim
            manifest.append(evidence)
    return manifest


def build_script_request(
    package: EditorialPackage,
    evidence_manifest: list[dict[str, Any]],
    recent_summary: list[dict[str, Any]],
) -> LLMGenerationRequest:
    evidence_by_insight: dict[str, list[str]] = {}
    for item in evidence_manifest:
        insight_id = item.get("insight_id")
        if insight_id:
            evidence_by_insight.setdefault(str(insight_id), []).append(item["evidence_id"])
    payload = {
        "task": f"{package.content_type}_SCRIPT",
        "language": package.language,
        "target_duration_seconds": package.duration.target_duration_seconds,
        "target_word_count": package.duration.target_word_count,
        "target_word_count_range": [
            package.duration.minimum_word_count,
            package.duration.maximum_word_count,
        ],
        "match": package.match,
        "character": asdict(package.character),
        "emotion": asdict(package.emotion),
        "narrative_angle": asdict(package.narrative_angle),
        "insights": [
            {
                "id": str(item.id),
                "type": item.insight_type,
                "claim": item.claim,
                "evidence_ids": evidence_by_insight.get(str(item.id), []),
            }
            for item in package.insights
        ],
        "EVIDENCE": evidence_manifest,
        "recent_content_summary": recent_summary,
        "constraints": {
            "no_new_numbers": True,
            "no_unverified_facts": True,
            "hook_immediately": True,
        },
    }
    return LLMGenerationRequest(
        SYSTEM_PROMPT_V1,
        json.dumps(payload, ensure_ascii=False),
        prompt_version_for(package.content_type),
    )


def build_repair_request(
    package: EditorialPackage,
    evidence_manifest: list[dict[str, Any]],
    draft: dict[str, Any],
    issues: list[str],
) -> LLMGenerationRequest:
    payload = {
        "task": "FACT_REPAIR",
        "language": package.language,
        "target_word_count_range": [
            package.duration.minimum_word_count,
            package.duration.maximum_word_count,
        ],
        "EVIDENCE": evidence_manifest,
        "previous_draft": draft,
        "validation_issues": issues,
        "instruction": (
            "Return a corrected full structured draft. Do not introduce any new facts, "
            "numbers, or entities."
        ),
    }
    return LLMGenerationRequest(
        SYSTEM_PROMPT_V1, json.dumps(payload, ensure_ascii=False), FACT_REPAIR_V1
    )
