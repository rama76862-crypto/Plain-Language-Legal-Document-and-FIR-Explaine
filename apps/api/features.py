"""Clauseora-inspired source-linked Action Pack and document version comparison."""
from __future__ import annotations
import re
import asyncio
import time
from difflib import SequenceMatcher
from fastapi import Header
from pydantic import BaseModel,Field
from apps.api.schemas import ApiError


def action_pack(record,snapshot):
    result=snapshot['result'];deadlines=result.get('deadlines',[]);checklist=[];questions=[]
    language=result.get('output_language','en')
    labels={
        'en':{'payment_penalty':'What exact wording defines this charge, its trigger and exceptions?','automatic_renewal':'How does the stated renewal and cancellation wording operate?','waived_rights':'Which right does this wording give up, and what exceptions are stated?','unilateral_change':'What changes does this wording permit, and what notice or approval is stated?','date':'Which event starts this period, and what date or counting rule must be confirmed?'},
        'hi':{'payment_penalty':'इस शुल्क, इसकी शर्त और अपवाद को कौन सा सटीक पाठ निर्धारित करता है?','automatic_renewal':'नवीनीकरण और रद्द करने की लिखी शर्तों का क्या अर्थ है?','waived_rights':'इस पाठ में किस अधिकार का त्याग है और कौन से अपवाद लिखे हैं?','unilateral_change':'किन बदलावों की अनुमति है और क्या सूचना या स्वीकृति लिखी है?','date':'यह अवधि किस घटना से शुरू होती है और किस तारीख या गणना की पुष्टि चाहिए?'},
        'pa':{'payment_penalty':'ਇਸ ਚਾਰਜ, ਇਸ ਦੀ ਸ਼ਰਤ ਅਤੇ ਅਪਵਾਦ ਨੂੰ ਕਿਹੜਾ ਸਹੀ ਪਾਠ ਨਿਰਧਾਰਤ ਕਰਦਾ ਹੈ?','automatic_renewal':'ਨਵੀਨੀਕਰਨ ਅਤੇ ਰੱਦ ਕਰਨ ਦੀਆਂ ਲਿਖੀਆਂ ਸ਼ਰਤਾਂ ਦਾ ਕੀ ਅਰਥ ਹੈ?','waived_rights':'ਇਸ ਪਾਠ ਵਿੱਚ ਕਿਹੜਾ ਹੱਕ ਛੱਡਿਆ ਗਿਆ ਹੈ ਅਤੇ ਕਿਹੜੇ ਅਪਵਾਦ ਹਨ?','unilateral_change':'ਕਿਹੜੇ ਬਦਲਾਅ ਦੀ ਇਜਾਜ਼ਤ ਹੈ ਅਤੇ ਕੀ ਸੂਚਨਾ ਜਾਂ ਮਨਜ਼ੂਰੀ ਲਿਖੀ ਹੈ?','date':'ਇਹ ਮਿਆਦ ਕਿਹੜੀ ਘਟਨਾ ਤੋਂ ਸ਼ੁਰੂ ਹੁੰਦੀ ਹੈ ਅਤੇ ਕਿਹੜੀ ਤਾਰੀਖ ਜਾਂ ਗਿਣਤੀ ਦੀ ਪੁਸ਼ਟੀ ਚਾਹੀਦੀ ਹੈ?'},
    }[language]
    for clause in record.clauses:
        if re.search(r'\b(?:must|shall|required\s+to|agrees?\s+to)\b|करना होगा|लाज़मी|ਲਾਜ਼ਮੀ|ਹੋਵੇਗਾ',clause.reviewed_text,re.I):
            roles=re.findall(r'\b(?:tenant|landlord|borrower|lender|buyer|seller|provider|customer|recipient|sender)\b|किरायेदार|मकान मालिक|ऋणदाता|उधारकर्ता|खरीदार|विक्रेता|ग्राहक|प्रदाता|ਕਿਰਾਏਦਾਰ|ਮਕਾਨ ਮਾਲਕ|ਕਰਜ਼ਦਾਤਾ|ਕਰਜ਼ਦਾਰ|ਖਰੀਦਦਾਰ|ਵਿਕਰੇਤਾ|ਗਾਹਕ|ਪ੍ਰਦਾਤਾ',clause.reviewed_text,re.I)
            dates=[d['source_quote'] for d in deadlines if d['clause_id']==clause.clause_id]
            checklist.append({'id':clause.clause_id,'statement':clause.reviewed_text,'party':', '.join(dict.fromkeys(role.casefold() for role in roles)) if roles else 'not_detected','due_or_trigger':dates,'clause_id':clause.clause_id,'source_ref':clause.source_ref.model_dump(),'review_status':'needs_review'})
    seen=set()
    for item in result.get('items',[]):
        category=item.get('category')
        if item.get('kind')=='attention' and category in labels and category not in seen:
            questions.append({'question':labels[category],'clause_ids':[item['clause_id']],'reason':'source_attention_cue'});seen.add(category)
    unresolved=[d['clause_id'] for d in deadlines if not d.get('resolved_date')]
    if unresolved:questions.append({'question':labels['date'],'clause_ids':list(dict.fromkeys(unresolved)),'reason':'unresolved_source_period'})
    return {'document_id':record.document_id,'analysis_id':snapshot['analysis_id'],'document_revision':record.revision,'checklist':checklist,'lawyer_questions':questions[:5],'limitations':['Source wording only; a checkbox records your review, not legal compliance.','No legal action, enforceability or eligibility decision is recommended.'],'independent_review':False}


def compare_records(a,b):
    normalize=lambda text:' '.join(text.casefold().split())
    left={c.clause_id:c for c in a.clauses};right={c.clause_id:c for c in b.clauses}
    unchanged=[];pairs=[]
    for aid,ac in list(left.items()):
        bid=next((key for key,c in right.items() if normalize(c.reviewed_text)==normalize(ac.reviewed_text)),None)
        if bid is not None:unchanged.append((aid,bid));left.pop(aid);right.pop(bid)
    candidates=[];deadline=time.monotonic()+2;budget_exhausted=False
    for aid,ac in left.items():
        for bid,bc in right.items():
            if time.monotonic()>deadline:budget_exhausted=True;break
            ratio=SequenceMatcher(None,normalize(ac.reviewed_text),normalize(bc.reviewed_text),autojunk=True).ratio()
            if ratio>=.45:candidates.append((ratio,aid,bid))
        if budget_exhausted:break
    for _,aid,bid in sorted(candidates,reverse=True):
        if aid in left and bid in right:pairs.append(('modified',left.pop(aid),right.pop(bid)))
    pairs.extend(('removed',c,None) for c in left.values());pairs.extend(('added',None,c) for c in right.values())
    def evidence(record,clause):
        return None if clause is None else {'document_id':record.document_id,'clause_id':clause.clause_id,'quote':clause.reviewed_text,'source_ref':clause.source_ref.model_dump()}
    changes=[{'change_id':f'change-{i+1}','change_type':kind,'before':evidence(a,ac),'after':evidence(b,bc),'review_status':'needs_review','why_review':'Source wording changed. Compare both exact passages and their conditions; semantic or legal significance is not independently established.'} for i,(kind,ac,bc) in enumerate(pairs)]
    return {'document_a':a.document_id,'document_b':b.document_id,'revision_a':a.revision,'revision_b':b.revision,'unchanged_passages':len(unchanged),'changes':changes,'method':'deterministic_text_alignment_v1','limitations':['Changes describe text differences, not legal conclusions.','Reordering, clause splitting and major rewrites can appear as added/removed passages.','Whitespace/case-only changes are ignored; unchanged wording does not establish legal safety.']+(['Alignment time budget reached; unmatched passages are shown as added/removed.'] if budget_exhausted else []),'independent_review':False}


class CompareRequest(BaseModel):
    document_b_id:str=Field(min_length=1,max_length=100)
    expected_revision_a:int=Field(ge=1)
    expected_revision_b:int=Field(ge=1)


class VerifyConsent(BaseModel):
    external_ai_consent:bool=False


def install_feature_routes(app,store,alive):
    verifier_slots=asyncio.Semaphore(2)
    @app.post('/api/v1/documents/{document_id}/analyses/{analysis_id}/verify-source',tags=['features'])
    async def verify_source(document_id:str,analysis_id:str,body:VerifyConsent,x_session_token:str|None=Header(default=None)):
        if not body.external_ai_consent:raise ApiError('CONSENT_REQUIRED','Explicit consent to share selected claims and excerpts with Cloudflare is required.',422)
        record=await store.get(document_id,x_session_token)
        async with record.lock:
            snapshot=record.analyses.get(analysis_id)
            if not alive(record) or not snapshot:raise ApiError('NOT_FOUND','Analysis not found.',404)
            if snapshot.get('document_revision')!=record.revision:raise ApiError('REVISION_CONFLICT','Source revision changed.',409)
            if not snapshot.get('result'):raise ApiError('ANALYSIS_NOT_READY','Analysis is not ready.',409,True)
            cached=record.verification_cache.get(analysis_id)
            if cached and cached.get('status')!='unavailable':return cached
            if verifier_slots.locked():raise ApiError('MODEL_BUSY','Source verifier is busy. Retry explicitly.',429,True)
            from copy import deepcopy
            result=deepcopy(snapshot['result']);revision=record.revision
        from apps.api.verification import verify_selected
        async with verifier_slots:verification=await verify_selected(result)
        async with record.lock:
            if not alive(record,revision) or analysis_id not in record.analyses:raise ApiError('NOT_FOUND','Analysis expired or changed.',404)
            record.verification_cache[analysis_id]=verification
        return verification

    @app.get('/api/v1/documents/{document_id}/analyses/{analysis_id}/action-pack',tags=['features'])
    async def get_action_pack(document_id:str,analysis_id:str,x_session_token:str|None=Header(default=None)):
        record=await store.get(document_id,x_session_token)
        async with record.lock:
            snapshot=record.analyses.get(analysis_id)
            if not alive(record) or not snapshot:raise ApiError('NOT_FOUND','Analysis not found.',404)
            if snapshot.get('document_revision')!=record.revision:raise ApiError('REVISION_CONFLICT','Source revision changed.',409)
            if not snapshot.get('result'):raise ApiError('ANALYSIS_NOT_READY','Analysis is not ready.',409,True)
            return action_pack(record,snapshot)

    @app.post('/api/v1/documents/{document_id}/compare',tags=['features'])
    async def compare(document_id:str,body:CompareRequest,x_session_token:str|None=Header(default=None),x_compare_session_token:str|None=Header(default=None)):
        if document_id==body.document_b_id:raise ApiError('INVALID_REQUEST','Choose a separate revised document.',422)
        a=await store.get(document_id,x_session_token);b=await store.get(body.document_b_id,x_compare_session_token)
        ordered=sorted([a,b],key=lambda r:r.document_id)
        async with ordered[0].lock,ordered[1].lock:
            if not alive(a) or not alive(b):raise ApiError('NOT_FOUND','Document not found.',404)
            if a.revision!=body.expected_revision_a or b.revision!=body.expected_revision_b:raise ApiError('REVISION_CONFLICT','A document revision changed.',409)
            if a.reviewed_revision!=a.revision or b.reviewed_revision!=b.revision:raise ApiError('REVIEW_REQUIRED','Confirm extraction review for both documents.',409)
            if len(a.clauses)>150 or len(b.clauses)>150:raise ApiError('FILE_TOO_LARGE','Compare up to 150 reviewed passages per document.',413)
            return await asyncio.to_thread(compare_records,a,b)
