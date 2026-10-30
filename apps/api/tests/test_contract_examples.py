"""Published frontend examples must satisfy the actual public schema."""
from apps.api.schemas import UploadAccepted,Metadata,ExtractionResponse,ReviewResponse,AnalysisAccepted,HealthResponse,ErrorResponse
from apps.api.ml_client import validate_snapshot,validate_answer
from apps.api.scripts.publish_examples import examples


def test_published_examples_match_public_models_and_evidence():
    data=examples()
    for key,model in [('upload_accepted',UploadAccepted),('document_metadata',Metadata),
                      ('extraction_awaiting_review',ExtractionResponse),('reviewed_patch_response',ReviewResponse),
                      ('analysis_accepted',AnalysisAccepted),('health',HealthResponse)]:
        model.model_validate(data[key])
    for error in data['errors'].values(): ErrorResponse.model_validate(error)
    result=data['analysis_snapshots']['complete']['result']
    payload={k:result[k] for k in ['document_id','analysis_id','document_revision','input_language','output_language','document_type']}
    payload['clauses']=data['extraction_awaiting_review']['clauses']
    for snapshot in data['analysis_snapshots'].values(): validate_snapshot(snapshot,payload)
    validate_answer(data['grounded_answer'],payload,result)
    validate_answer(data['insufficient_evidence_answer'],payload,result)
