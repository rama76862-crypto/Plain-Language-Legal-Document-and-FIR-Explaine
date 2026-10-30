"""Literal deadline extraction; this module never computes legal due dates."""

from __future__ import annotations

import re

from apps.ml.service.contracts import ClauseInput, Deadline, Language

_EN = re.compile(
    r"\bwithin\s+(?P<count>\d+|one|two|three|four|five|six|seven|eight|nine|ten|\w+)\s+"
    r"(?P<unit>days?|weeks?)\s+of\s+(?P<anchor>receipt|service|delivery)\b",
    re.IGNORECASE,
)
_HI = re.compile(r"प्राप्ति\s+के\s+(?P<count>\d+)\s+दिनों?\s+के\s+भीतर")
_PA = re.compile(r"ਪ੍ਰਾਪਤੀ\s+ਤੋਂ\s+(?P<count>\d+)\s+ਦਿਨਾਂ?\s+ਦੇ\s+ਅੰਦਰ")

_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def extract_relative_deadlines(
    clause: ClauseInput,
    output_language: Language = "en",
) -> list[Deadline]:
    """Extract an explicit relative period and leave its anchor unresolved."""
    text = clause.reviewed_text
    matches: list[tuple[re.Match[str], str, str]] = []
    for match in _EN.finditer(text):
        anchor = match.group("anchor").lower()
        matches.append((match, anchor, match.group("unit").lower()))
    for match in _HI.finditer(text):
        matches.append((match, "receipt", "days"))
    for match in _PA.finditer(text):
        matches.append((match, "receipt", "days"))

    deadlines: list[Deadline] = []
    for index, (match, anchor, unit) in enumerate(matches, start=1):
        raw_count = match.group("count")
        try:
            count = int(raw_count)
        except ValueError:
            count = _NUMBER_WORDS.get(raw_count.lower())
        if count is None:
            continue

        unit_label = "day" if unit.startswith("day") else "week"
        unit_plural = unit_label if count == 1 else f"{unit_label}s"
        if output_language == "hi":
            display = f"प्राप्ति के {count} दिनों के भीतर" if anchor == "receipt" else match.group(0)
        elif output_language == "pa":
            display = f"ਪ੍ਰਾਪਤੀ ਤੋਂ {count} ਦਿਨਾਂ ਦੇ ਅੰਦਰ" if anchor == "receipt" else match.group(0)
        else:
            display = f"{count} {unit_plural} after {anchor}"

        deadlines.append(
            Deadline(
                deadline_id=f"{clause.clause_id}-deadline-{index}",
                clause_id=clause.clause_id,
                source_quote=match.group(0),
                display_text=display,
                anchor=anchor,
                resolved_date=None,
                status="needs_information",
                missing_information=[f"{anchor}_date"],
            )
        )
    return deadlines

