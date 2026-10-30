"""Ephemeral review reports. No token, filesystem path or implicit disk retention."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import base64
import json

DISCLAIMER = "Information only, not legal advice. Automated checks do not establish legal correctness. Read the original document and seek qualified help for interpretation."

def build_report(record, snapshot: dict, *, include_questions: bool = False) -> dict:
    result = deepcopy(snapshot["result"])
    report = {
        "schema_version":"review-report-v1",
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "filename":record.filename,
        "document_revision":snapshot["document_revision"],
        "analysis_status":snapshot["status"],
        "disclaimer":DISCLAIMER,
        "independent_review":"not_performed",
        "processing_consent":"temporary_processing_and_Groq_inference" if record.inference_mode=='hosted' else "temporary_processing_only",
        "inference_mode":record.inference_mode,
        "external_ai_disclosure":"Groq receives admitted, identifier-masked text. An optional, separately consented source check sends selected claims/excerpts to Cloudflare." if record.inference_mode=='hosted' else "Primary inference runs locally. An optional source check contacts Cloudflare only after separate explicit consent.",
        "retention":"In memory for the temporary session; downloaded copies remain with the user.",
        "analysis":result,
        "clauses":[{"clause_id":c.clause_id,"reviewed_text":c.reviewed_text,"source_ref":c.source_ref.model_dump()} for c in record.clauses],
        "questions":[],
    }
    if include_questions:
        for entry in record.question_cache.values():
            if entry.get("fingerprint",{}).get("analysis_id")==result["analysis_id"] and entry.get("answer"):
                report["questions"].append({"question":entry["fingerprint"]["question"],"answer":deepcopy(entry["answer"])})
    from apps.api.features import action_pack
    report['action_pack']=action_pack(record,snapshot)
    report['selected_source_verification']=record.verification_cache.get(snapshot['analysis_id'])
    return report

def _safe_text(value) -> str:
    # Export source as text, not executable HTML/Markdown links.
    text=escape(str(value),quote=True)
    for char in [chr(92),"`","*","_","{","}","[","]","#","|"]:
        text=text.replace(char,chr(92)+char)
    return text

def render_markdown(report: dict) -> str:
    result = report["analysis"]
    lines = ["# Document explanation and review report", "", report["disclaimer"],"",
        f"Source: {_safe_text(report['filename'])}",
        f"Revision: {report['document_revision']}",
        f"Generated: {report['generated_at']}",
        f"Status: {report['analysis_status']}; independent review: {report['independent_review']}",
        f"Coverage: {result['coverage']['analysed']} / {result['coverage']['total']} clauses",
        "", "## Warnings", *["- "+_safe_text(w) for w in result.get("warnings",[])],""]
    for clause in report["clauses"]:
        lines += ["## Clause "+_safe_text(clause["clause_id"]),"", "Original reviewed text:"]
        lines += ["> "+_safe_text(line) for line in clause["reviewed_text"].splitlines()]
        for item in result["items"]:
            if item["clause_id"] == clause["clause_id"]:
                lines += ["",f"**{_safe_text(item['kind'])}: {_safe_text(item['category'])}**",_safe_text(item["explanation"]),f"Review: {_safe_text(item['review_status'])}"]
                if item.get("limitations"):
                    lines.append("Limitations: "+_safe_text("; ".join(item["limitations"])))
        lines.append("")
    lines += ["## Deadlines"]
    for deadline in result.get("deadlines",[]):
        lines += ["- "+_safe_text(deadline["display_text"])+f" [{deadline['status']}]", "  Original: "+_safe_text(deadline["source_quote"]), "  Missing: "+_safe_text(", ".join(deadline.get("missing_information",[])))]
    lines += ["", "## Clarification and next steps"]
    lines += ["- "+_safe_text(step["text"]) for step in result.get("next_steps",[])]
    lines += ['', '## Action Pack - source obligation checklist']
    for entry in report.get('action_pack',{}).get('checklist',[]):
        lines += ['- [ ] '+_safe_text(entry['statement']), '  Party: '+_safe_text(entry['party'])+'; source: '+_safe_text(entry['clause_id'])]
    lines += ['', '## Questions for legal aid']
    for entry in report.get('action_pack',{}).get('lawyer_questions',[]):lines.append('- '+_safe_text(entry['question']))
    if report.get('selected_source_verification'):
        lines += ['', '## Optional selected-claim source check',_safe_text(json.dumps(report['selected_source_verification'],ensure_ascii=False))]
    lines += ["", "## Free legal aid"]
    for resource in result.get("legal_aid",[]):
        lines.append("- "+_safe_text(resource["title"])+": "+_safe_text(resource["url"]))
    lines += ["", "## References"]
    for reference in result.get("references",[]):
        lines += ["- "+_safe_text(reference["title"])+"; "+_safe_text(reference.get("section") or "")+"; "+_safe_text(reference.get("version") or "version unavailable"),"  "+_safe_text(reference["url"])]
    lines += ["", "## Source fact ledger", "", "The ledger records source literals and excerpts; it is not a legal interpretation."]
    # Escape Markdown metacharacters in raw content by HTML escaping plus line
    # prefix; HTML export is separately escaped in full.
    for ledger in result.get("structured_facts",[]):
        lines.append("- "+_safe_text(json.dumps(ledger,ensure_ascii=False)))
    if report["questions"]:
        lines += ["", "## Questions and answers"]
        for question in report["questions"]:
            lines += ["", "Question: "+_safe_text(question["question"]), "Answer: "+_safe_text(question["answer"]["answer"]), "Review: "+_safe_text(question["answer"]["review_status"])]
    lines += ["", "## Model and rules provenance", _safe_text(json.dumps(result.get("provenance",{}),ensure_ascii=False)), "", "## Privacy", report["retention"], _safe_text(report['external_ai_disclosure']), 'Processing mode: '+_safe_text(report['inference_mode'])]
    return "\n".join(lines)+"\n"

def render_html(report: dict) -> str:
    # No JS, remote assets or raw document HTML. Print this self-contained file.
    text = escape(render_markdown(report))
    language = report["analysis"].get("output_language","en")
    fonts=Path(__file__).parent/"assets"/"fonts"
    css,licences=[],[]
    for filename,family in (("devanagari","Noto Sans Devanagari"),("gurmukhi","Noto Sans Gurmukhi")):
        path=fonts/(filename+".woff2")
        if path.is_file():
            encoded=base64.b64encode(path.read_bytes()).decode("ascii")
            css.append(f'@font-face{{font-family:"{family}";src:url(data:font/woff2;base64,{encoded}) format("woff2");font-weight:400}}')
        licence=fonts/(filename.upper()+"-LICENSE.txt")
        if licence.exists(): licences.append(escape(licence.read_text(encoding="utf-8")))
    return f'<!doctype html><html lang="{language}"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Document review report</title><style>{"".join(css)}body{{font-family:"Noto Sans Devanagari","Noto Sans Gurmukhi",system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:1rem;line-height:1.8}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}}@media print{{body{{margin:0;max-width:none}}}}</style><body><pre>{text}</pre><details><summary>Bundled font licences</summary><pre>{"<hr>".join(licences)}</pre></details></body></html>'

