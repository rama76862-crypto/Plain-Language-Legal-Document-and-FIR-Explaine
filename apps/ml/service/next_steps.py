"""Non-advisory clarification checklists, anchored to the uploaded document."""
from __future__ import annotations
from apps.ml.service.contracts import AnalysisRequest, AnalysisResult

_MESSAGES = {
    "penalty": {
        "en": "Clarify the stated penalty amount, the event that triggers it, and any exception.",
        "hi": "लिखे गए जुर्माने की राशि, उसके लागू होने की शर्त और किसी अपवाद को स्पष्ट करें।",
        "pa": "ਲਿਖੇ ਜੁਰਮਾਨੇ ਦੀ ਰਕਮ, ਲਾਗੂ ਹੋਣ ਦੀ ਸ਼ਰਤ ਅਤੇ ਕਿਸੇ ਛੋਟ ਬਾਰੇ ਸਪਸ਼ਟੀਕਰਨ ਲਵੋ।",
    },
    "renewal": {
        "en": "Locate the renewal period and cancellation notice requirement; ask about anything not stated.",
        "hi": "नवीनीकरण अवधि और रद्द करने की सूचना की शर्त देखें; जो नहीं लिखा है उस पर स्पष्टीकरण लें।",
        "pa": "ਨਵੀਨੀਕਰਨ ਦੀ ਮਿਆਦ ਅਤੇ ਰੱਦ ਕਰਨ ਦੀ ਸੂਚਨਾ ਦੀ ਸ਼ਰਤ ਵੇਖੋ; ਨਾ ਲਿਖੀਆਂ ਗੱਲਾਂ ਬਾਰੇ ਸਪਸ਼ਟੀਕਰਨ ਲਵੋ।",
    },
    "waiver": {
        "en": "Ask which right or claim this wording gives up and what exceptions are stated.",
        "hi": "पूछें कि इस शब्दावली में कौन सा अधिकार या दावा छोड़ा गया है और कौन से अपवाद लिखे हैं।",
        "pa": "ਪੁੱਛੋ ਕਿ ਇਸ ਲਿਖਤ ਵਿੱਚ ਕਿਹੜਾ ਹੱਕ ਜਾਂ ਦਾਅਵਾ ਛੱਡਿਆ ਗਿਆ ਹੈ ਅਤੇ ਕਿਹੜੀਆਂ ਛੋਟਾਂ ਲਿਖੀਆਂ ਹਨ।",
    },
    "deadline": {
        "en": "Confirm the missing date or counting rule before relying on this relative period. No legal due date has been calculated.",
        "hi": "इस सापेक्ष अवधि पर भरोसा करने से पहले अनुपलब्ध तारीख या गणना नियम की पुष्टि करें। कानूनी अंतिम तारीख की गणना नहीं की गई है।",
        "pa": "ਇਸ ਮਿਆਦ ਉੱਤੇ ਭਰੋਸਾ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ ਗੁੰਮ ਮਿਤੀ ਜਾਂ ਗਿਣਤੀ ਦੇ ਨਿਯਮ ਦੀ ਪੁਸ਼ਟੀ ਕਰੋ। ਕਾਨੂੰਨੀ ਆਖਰੀ ਮਿਤੀ ਨਹੀਂ ਗਿਣੀ ਗਈ।",
    },
    "fir": {
        "en": "Separate recorded allegations from established facts. Take the original FIR and any unclear references to a legal-aid professional.",
        "hi": "दर्ज आरोपों को सिद्ध तथ्यों से अलग रखें। मूल प्राथमिकी और अस्पष्ट संदर्भ कानूनी सहायता विशेषज्ञ को दिखाएँ।",
        "pa": "ਦਰਜ ਇਲਜ਼ਾਮਾਂ ਨੂੰ ਸਾਬਤ ਤੱਥਾਂ ਤੋਂ ਵੱਖ ਰੱਖੋ। ਅਸਲ ਐਫਆਈਆਰ ਅਤੇ ਅਸਪਸ਼ਟ ਹਵਾਲੇ ਕਾਨੂੰਨੀ ਸਹਾਇਤਾ ਮਾਹਰ ਨੂੰ ਦਿਖਾਓ।",
    },
    "aid": {
        "en": "For independent help, use the official NALSA legal-aid page to find assistance. This tool does not determine eligibility or give legal advice.",
        "hi": "स्वतंत्र सहायता के लिए आधिकारिक NALSA कानूनी सहायता पृष्ठ का उपयोग करें। यह उपकरण पात्रता तय नहीं करता और कानूनी सलाह नहीं देता।",
        "pa": "ਸੁਤੰਤਰ ਮਦਦ ਲਈ ਅਧਿਕਾਰਤ NALSA ਕਾਨੂੰਨੀ ਸਹਾਇਤਾ ਪੰਨਾ ਵਰਤੋ। ਇਹ ਸਾਧਨ ਯੋਗਤਾ ਤੈਅ ਨਹੀਂ ਕਰਦਾ ਅਤੇ ਕਾਨੂੰਨੀ ਸਲਾਹ ਨਹੀਂ ਦਿੰਦਾ।",
    },
}
def build_next_steps(request: AnalysisRequest, result: AnalysisResult) -> list[dict]:
    language = request.output_language if request.output_language in {"en", "hi", "pa"} else "en"
    steps = []
    for category, key in (("payment_penalty", "penalty"), ("automatic_renewal", "renewal"), ("waived_rights", "waiver")):
        items = [item for item in result.items if item.kind == "attention" and item.category == category]
        if items:
            steps.append({"kind": "clarification", "text": _MESSAGES[key][language], "clause_ids": list(dict.fromkeys(i.clause_id for i in items)), "review_status": "needs_review"})
    if any(d.status == "needs_information" for d in result.deadlines):
        steps.append({"kind": "missing_information", "text": _MESSAGES["deadline"][language], "clause_ids": list(dict.fromkeys(d.clause_id for d in result.deadlines if d.status == "needs_information")), "review_status": "needs_review"})
    if request.document_type == "fir":
        steps.append({"kind": "information", "text": _MESSAGES["fir"][language], "clause_ids": [], "review_status": "needs_review"})
    steps.append({"kind": "legal_aid", "text": _MESSAGES["aid"][language], "clause_ids": [], "url": "https://nalsa.gov.in/legal-aid/", "review_status": "needs_review" if language != "en" else "supported"})
    return steps

