"""Literal multilingual dates/periods. Never calculate a legal due date."""
from __future__ import annotations

from datetime import date
import re
import unicodedata
from apps.ml.service.contracts import ClauseInput, Deadline, Language

_WORDS = {word: i for i, word in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
_WORDS.update({"thirty": 30, "sixty": 60, "ninety": 90})
_COUNT = r"\d+|" + "|".join(sorted(_WORDS, key=len, reverse=True))
_EN = re.compile(rf"\b(?P<trigger>within|at\s+least|no\s+later\s+than)\s+(?P<count>{_COUNT})\s+(?P<business>business\s+|working\s+)?(?P<unit>days?|weeks?|months?|years?)(?:\s+(?:of|after|from|before)\s+(?:the\s+)?(?P<anchor>receipt|service|delivery|expiry|expiration|termination|signing|due\s+date))?", re.I)
_HI = re.compile(r"(?P<anchor>प्राप्ति|तामील|डिलीवरी|समाप्ति)?\s*(?:के|से)?\s*(?P<count>\d+)\s*(?P<unit>दिनों?|सप्ताह|महीन[ेों]+|वर्ष)\s*(?:के\s*)?(?:भीतर|पहले|बाद)")
_PA = re.compile(r"(?P<anchor>ਪ੍ਰਾਪਤੀ|ਤਾਮੀਲ|ਡਿਲੀਵਰੀ|ਸਮਾਪਤੀ)?\s*(?:ਤੋਂ|ਦੇ)?\s*(?P<count>\d+)\s*(?P<unit>ਦਿਨਾਂ?|ਹਫ਼ਤ[ੇਿਆਂ]+|ਮਹੀਨ[ੇਿਆਂ]+|ਸਾਲ)\s*(?:ਦੇ\s*)?(?:ਅੰਦਰ|ਪਹਿਲਾਂ|ਬਾਅਦ)")
_UNIT = {"day": ("दिन", "ਦਿਨ"), "week": ("सप्ताह", "ਹਫ਼ਤੇ"), "month": ("महीने", "ਮਹੀਨੇ"), "year": ("वर्ष", "ਸਾਲ")}
_ANCHOR = {"प्राप्ति": "receipt", "ਪ੍ਰਾਪਤੀ": "receipt", "तामील": "service", "ਤਾਮੀਲ": "service", "डिलीवरी": "delivery", "ਡਿਲੀਵਰੀ": "delivery", "समाप्ति": "expiry", "ਸਮਾਪਤੀ": "expiry"}
_MONTHS = {name.lower(): i for i, name in enumerate("January February March April May June July August September October November December".split(), 1)}
_MONTHS.update({key[:3]: value for key, value in list(_MONTHS.items())})
for names in ("जनवरी फरवरी मार्च अप्रैल मई जून जुलाई अगस्त सितंबर अक्टूबर नवंबर दिसंबर", "ਜਨਵਰੀ ਫਰਵਰੀ ਮਾਰਚ ਅਪ੍ਰੈਲ ਮਈ ਜੂਨ ਜੁਲਾਈ ਅਗਸਤ ਸਤੰਬਰ ਅਕਤੂਬਰ ਨਵੰਬਰ ਦਸੰਬਰ"):
    _MONTHS.update({name:index for index,name in enumerate(names.split(),1)})
_NAMED_DATE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(_MONTHS) + r")\s+(\d{4})\b", re.I)
_NUMERIC_DATE = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)|(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?!\d)")

def _unit(value: str) -> str:
    for pattern, result in ((r"day|दिन|ਦਿਨ", "day"), (r"week|सप्ताह|ਹਫ਼ਤ", "week"), (r"month|महीन|ਮਹੀਨ", "month")):
        if re.search(pattern, value, re.I):
            return result
    return "year"

def extract_relative_deadlines(clause: ClauseInput, output_language: Language = "en") -> list[Deadline]:
    # Decimal digit normalization is one-to-one so original offsets remain exact.
    text = "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in clause.reviewed_text)
    records = []
    for pattern in (_EN, _HI, _PA):
        for match in pattern.finditer(text):
            raw = match.group("count").lower()
            count = int(raw) if raw.isdecimal() else _WORDS[raw]
            unit = _unit(match.group("unit"))
            anchor_raw = match.group("anchor")
            anchor = _ANCHOR.get(anchor_raw, anchor_raw.lower().replace(" ", "_") if anchor_raw else "unspecified_event")
            quote = clause.reviewed_text[match.start():match.end()]
            display = f"{count} {unit}{'' if count == 1 else 's'}; {quote}"
            if output_language in {"hi", "pa"}:
                display = f"{count} {_UNIT[unit][0 if output_language == 'hi' else 1]}; {quote}"
            missing = [f"{anchor}_date"]
            if "business" in match.groupdict() and match.group("business"):
                missing.append("business_calendar_and_counting_rules")
            records.append((match.start(), Deadline(deadline_id="pending", clause_id=clause.clause_id, source_quote=quote, display_text=display, anchor=anchor, resolved_date=None, status="needs_information", missing_information=missing)))
    recurring_patterns=(r'\b(?:on\s+or\s+before|by)\s+(?:the\s+)?\d{1,2}(?:st|nd|rd|th)?\s+of\s+(?:every|each)\s+month\b',r'हर\s+महीने\s+की\s*\d{1,2}\s*तारीख\s*तक',r'ਹਰ\s+ਮਹੀਨੇ\s+ਦੀ\s*\d{1,2}\s*ਤਾਰੀਖ\s*ਤੱਕ')
    for pattern in recurring_patterns:
        for match in re.finditer(pattern,text,re.I):
            day_match=re.search(r'\d{1,2}',match.group())
            if not day_match or not 1<=int(day_match.group())<=31: continue
            quote=clause.reviewed_text[match.start():match.end()]
            records.append((match.start(),Deadline(deadline_id='pending',clause_id=clause.clause_id,source_quote=quote,display_text=quote,anchor='monthly_recurrence',resolved_date=None,status='needs_information',missing_information=['next_applicable_month_and_year','calendar_and_exception_rules'])))
    for pattern in (_NUMERIC_DATE, _NAMED_DATE):
        for match in pattern.finditer(text):
            resolved, ambiguous = None, False
            try:
                if pattern is _NAMED_DATE:
                    day, month, year = match.groups()
                    resolved = date(int(year), _MONTHS[month.lower()], int(day))
                elif match.group(1):
                    resolved = date(*map(int, match.groups()[:3]))
                else:
                    day, month, year = map(int, match.groups()[3:])
                    ambiguous = day <= 12 and month <= 12 and day != month
                    if not ambiguous:
                        resolved = date(year, month, day)
            except (ValueError, TypeError):
                continue
            quote = clause.reviewed_text[match.start():match.end()]
            context = text[max(0, match.start()-70):match.end()+35]
            if not re.search(r"\b(?:by|before|deadline|due|on\s+or\s+before|expires?|expiry)\b|तक|अंतिम|ਤੱਕ|ਆਖਰੀ", context, re.I):
                continue
            records.append((match.start(), Deadline(deadline_id="pending", clause_id=clause.clause_id, source_quote=quote, display_text=quote, anchor="explicit_date", resolved_date=resolved, status="needs_review" if ambiguous else "explicit", missing_information=["date_format"] if ambiguous else [])))
    records.sort(key=lambda value: value[0])
    seen, result = set(), []
    for _, deadline in records:
        if deadline.source_quote in seen:
            continue
        seen.add(deadline.source_quote)
        deadline.deadline_id = f"{clause.clause_id}-deadline-{len(result)+1}"
        result.append(deadline)
    return result

