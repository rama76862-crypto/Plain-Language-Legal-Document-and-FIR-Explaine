"""New backend acceptance regressions. Fixtures are explicitly synthetic."""
import asyncio
import json
from datetime import date
from pathlib import Path
import pytest
from apps.ml.service.contracts import ClauseInput
from apps.ml.service.deadlines import extract_relative_deadlines
from apps.ml.validation.agreement_rules import agreement_attention_items
from apps.ml.validation.source_facts import grounding_issues, source_facts, cross_reference_context, document_profile
from apps.ml.service.bootstrap import reference_is_admitted
from apps.ml.retrieval._bm25 import tokenize

@pytest.mark.parametrize("source,output,issue",[
("The provider may update terms by posting on its website.","The provider can change terms without customer consent.","unsupported_consent_claim"),
("Payment received within 10 days of delivery avoids the fee.","Payment made within 10 days of the due date avoids the fee.","unsupported_anchor:due_date"),
("The tenant must pay INR 500 unless the payment is received within 10 days of receipt.","The tenant must pay INR 500 within 10 days of receipt.","omitted_condition_or_exception"),
("The landlord must return INR 500.","The tenant must return INR 500.","unsupported_actor"),
("The charge does not apply.","The charge applies.","omitted_negation"),
])
def test_known_material_changes_rejected(source,output,issue):
    assert issue in grounding_issues(source,output)

@pytest.mark.parametrize("text,category",[
("The tenant waives the right to claim a refund.","waived_rights"),
("The agreement renews automatically unless cancelled.","automatic_renewal"),
("Auto-renewal is applicable.","automatic_renewal"),
("A late payment fee of INR 500 is charged.","payment_penalty"),
("किरायेदार अपने अधिकार छोड़ देता है।","waived_rights"),
("ਕਿਰਾਏਦਾਰ ਆਪਣੇ ਹੱਕ ਛੱਡ ਦਿੰਦਾ ਹੈ।","waived_rights"),
])
def test_required_cues(text,category):
    assert category in {x.category for x in agreement_attention_items(ClauseInput(clause_id="c",reviewed_text=text))}

@pytest.mark.parametrize("text",[
"The tenant does not waive any rights.",
"These rights shall not be waived.",
"Automatic renewal is not applicable.",
"No late payment fee applies.",
"Late payment fees are excluded.",
])
def test_protective_wording_not_flagged(text):
    assert not agreement_attention_items(ClauseInput(clause_id="c",reviewed_text=text))

@pytest.mark.parametrize("language,unit",[("hi","सप्ताह"),("pa","ਹਫ਼ਤੇ")])
def test_week_never_translates_to_day(language,unit):
    result=extract_relative_deadlines(ClauseInput(clause_id="c",reviewed_text="Reply within 2 weeks of receipt."),language)
    assert result[0].anchor=="receipt"
    assert unit in result[0].display_text
    assert result[0].resolved_date is None
    assert result[0].source_quote=="within 2 weeks of receipt"

@pytest.mark.parametrize("text,expected",[
("Reply by 31 October 2026.",date(2026,10,31)),
("Payment is due on 2026-10-31.",date(2026,10,31)),
("Reply by 31/10/2026.",date(2026,10,31)),
])
def test_explicit_dates(text,expected):
    assert extract_relative_deadlines(ClauseInput(clause_id="c",reviewed_text=text))[0].resolved_date==expected

def test_ambiguous_dates_are_not_guessed():
    result=extract_relative_deadlines(ClauseInput(clause_id="c",reviewed_text="Reply by 03/04/2026."))
    assert result[0].resolved_date is None and result[0].status=="needs_review"

def test_cross_reference_uses_legal_number_not_array_position():
    clauses=[ClauseInput(clause_id="extracted-a",reviewed_text="8. Subject to Clause 3 and Annexure B."),ClauseInput(clause_id="extracted-b",reviewed_text="3. The deposit is refundable.")]
    found,missing=cross_reference_context(clauses[0],clauses)
    assert [x.clause_id for x in found]==["extracted-b"] and missing==["B"]

def test_indic_tokens_preserve_combining_marks():
    assert "प्राप्ति" in tokenize("प्राप्ति के बाद")
    assert "ਜੁਰਮਾਨਾ" in tokenize("ਦੇਰੀ ਦਾ ਜੁਰਮਾਨਾ")

def test_reference_curation_fails_closed():
    manifest=json.loads((Path(__file__).parents[1]/"data"/"references.json").read_text())
    assert not reference_is_admitted(manifest[3])

def test_indian_training_split_families_are_disjoint():
    from apps.ml.training.indian import load_rows, DATA
    rows=load_rows(DATA)
    families={split:{r["family"] for r in rows if r["split"]==split} for split in ("train","validation","test")}
    assert not families["train"] & families["validation"]
    assert not families["train"] & families["test"]
    assert not families["test"] & families["validation"]


@pytest.mark.parametrize("text",[
 "Rent is payable on or before the 5th of every month.",
 "किराया हर महीने की 5 तारीख तक देना है।",
 "ਕਿਰਾਇਆ ਹਰ ਮਹੀਨੇ ਦੀ 5 ਤਾਰੀਖ ਤੱਕ ਦੇਣਾ ਹੈ।",
])
def test_recurring_monthly_deadline_never_invents_next_date(text):
    result=extract_relative_deadlines(ClauseInput(clause_id="recurring",reviewed_text=text))
    assert len(result)==1
    assert result[0].anchor=="monthly_recurrence"
    assert result[0].resolved_date is None and result[0].status=="needs_information"
    assert result[0].source_quote in text

