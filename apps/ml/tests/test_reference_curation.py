"""Contract checks for the small, official-source reference demo set."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

import pytest

from apps.ml.retrieval.reference_index import CuratedReference, find_official_references
from apps.ml.service.contracts import ReferenceRecord

MANIFEST_PATH = Path(__file__).parents[1] / "data" / "references.json"
OFFICIAL_HOSTS = {
    "indiacode.nic.in",
    "www.indiacode.nic.in",
    "consumeraffairs.nic.in",
    "nalsa.gov.in",
}


@pytest.fixture(scope="module")
def manifest() -> list[dict[str, object]]:
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(raw, list)
    return raw


@pytest.fixture(scope="module")
def references(manifest: list[dict[str, object]]) -> list[CuratedReference]:
    return [
        CuratedReference(
            record=ReferenceRecord.model_validate(entry["record"]),
            law=str(entry["law"]),
        )
        for entry in manifest
    ]


def _entry_by_id(manifest: list[dict[str, object]], reference_id: str) -> dict[str, object]:
    return next(
        entry
        for entry in manifest
        if entry["record"]["reference_id"] == reference_id  # type: ignore[index]
    )


def test_manifest_records_follow_contract_and_have_reproducible_provenance(
    manifest: list[dict[str, object]],
) -> None:
    assert len(manifest) >= 5
    ids: set[str] = set()
    for entry in manifest:
        record = ReferenceRecord.model_validate(entry["record"])
        assert record.reference_id not in ids
        ids.add(record.reference_id)

        provenance = entry["provenance"]
        assert provenance["source_checked_date"] == "2026-10-30"  # type: ignore[index]
        assert provenance["source_locator"]  # type: ignore[index]
        assert provenance["retrieval_query"]  # type: ignore[index]
        assert provenance["retrieval_method"]  # type: ignore[index]
        assert provenance["reuse_note"]  # type: ignore[index]
        assert provenance["excerpt_sha256_utf8"] == hashlib.sha256(  # type: ignore[index]
            record.excerpt.encode("utf-8")
        ).hexdigest()
        assert urlparse(record.url).hostname in OFFICIAL_HOSTS


def test_exact_section_matches_return_curated_records_only(
    references: list[CuratedReference],
) -> None:
    match = find_official_references(
        references,
        "synthetic lookup fixture for a copy supplied to an informant or victim",
        section="173",
        law="BNSS",
        jurisdiction="IN",
        limit=1,
    )
    assert len(match) == 1
    assert match[0].hit.record_id == "bnss_2023_s173"
    assert match[0].exact_section_match is True
    assert match[0].hit.reference is not None
    assert match[0].hit.reference.url.startswith("https://www.indiacode.nic.in/")


def test_wrong_section_is_never_marked_exact(
    references: list[CuratedReference],
) -> None:
    matches = find_official_references(
        references,
        "synthetic lookup fixture for a copy supplied to an informant or victim",
        section="154",
        law="BNSS",
        jurisdiction="IN",
    )
    assert matches
    assert all(not result.exact_section_match for result in matches)


def test_old_and_new_procedure_references_stay_version_and_law_bound(
    references: list[CuratedReference],
) -> None:
    old = find_official_references(
        references,
        "synthetic fixture for the older procedural-code locator",
        section="154",
        law="CrPC",
        jurisdiction="IN",
        limit=1,
    )
    new = find_official_references(
        references,
        "synthetic fixture for the newer procedural-code locator",
        section="173",
        law="BNSS",
        jurisdiction="IN",
        limit=1,
    )
    assert old[0].hit.record_id == "crpc_1973_s154"
    assert old[0].exact_section_match is True
    assert new[0].hit.record_id == "bnss_2023_s173"
    assert new[0].exact_section_match is True

    crpc_version = old[0].hit.reference.version if old[0].hit.reference else None
    assert crpc_version is not None
    version_filtered = find_official_references(
        references,
        "synthetic fixture for a version-filtered section lookup",
        section="154",
        law="CrPC",
        jurisdiction="IN",
        version=crpc_version,
    )
    assert [result.hit.record_id for result in version_filtered] == ["crpc_1973_s154"]
    assert version_filtered[0].exact_section_match is True

    bnss_version = new[0].hit.reference.version if new[0].hit.reference else None
    assert bnss_version is not None
    wrong_version = find_official_references(
        references,
        "synthetic fixture with a deliberately mismatched code version",
        section="154",
        law="CrPC",
        jurisdiction="IN",
        version=bnss_version,
    )
    assert wrong_version == []

    cross_law = find_official_references(
        references,
        "synthetic fixture deliberately pairing BNSS with the old section number",
        section="154",
        law="BNSS",
        jurisdiction="IN",
    )
    assert all(not result.exact_section_match for result in cross_law)


@pytest.mark.parametrize(
    ("law", "section", "reference_id"),
    [
        (
            "Consumer Protection (E-Commerce) Rules, 2020",
            "2(1)(a)",
            "ecommerce_rules_2020_r2_1_a",
        ),
        (
            "Consumer Protection (E-Commerce) Rules, 2020",
            "4(9)",
            "ecommerce_rules_2020_r4_9",
        ),
        ("National Legal Services Authority official FAQ", "FAQ 11", "nalsa_faq_11"),
    ],
)
def test_nested_rule_and_agency_faq_locators_can_match_exactly(
    references: list[CuratedReference], law: str, section: str, reference_id: str
) -> None:
    matches = find_official_references(
        references,
        "synthetic fixture for an exact curated locator",
        section=section,
        law=law,
        jurisdiction="IN",
        limit=1,
    )
    assert len(matches) == 1
    assert matches[0].hit.record_id == reference_id
    assert matches[0].exact_section_match is True


def test_missing_law_section_and_unrelated_query_return_no_match(
    references: list[CuratedReference],
) -> None:
    assert find_official_references(
        references,
        "synthetic fixture containing unrelated meteorology terms only",
        section="999",
        law="BNSS",
        jurisdiction="IN",
    ) == []
