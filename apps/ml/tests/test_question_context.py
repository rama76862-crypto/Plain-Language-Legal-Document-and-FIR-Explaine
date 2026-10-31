"""Question context must fit local inference and retain exact source evidence."""
import asyncio
import json

from apps.ml.service.contracts import AnalysisResult, ClauseInput, Coverage, QuestionRequest
from apps.ml.tests.test_pipeline import _pipeline, _request, FixtureGenerator
from apps.ml.service.pipeline import _question_windows


def test_indic_context_is_bounded_by_bytes_and_keeps_literal_unicode_quotes():
    clauses = [ClauseInput(clause_id=f'c{i}', reviewed_text='किराया भुगतान की शर्तें। ' * 100) for i in range(5)]
    excerpts, limited = _question_windows(clauses, [c.clause_id for c in clauses], {'किराया'})
    assert limited
    assert 0 < sum(len(c.reviewed_text.encode('utf-8')) for c in excerpts) <= 3000
    assert all(c.reviewed_text in clauses[int(c.clause_id[1:])].reviewed_text for c in excerpts)


def test_long_document_question_uses_bounded_ranked_source_excerpts():
    pipeline, _, _ = _pipeline()
    text = ('This synthetic administrative paragraph describes document handling. ' * 80
            + 'The synthetic monthly fee is INR 1500 and is due on the fifth day of each month.')
    request = _request('agreement', 'long-question', text)
    request.clauses.extend(ClauseInput(clause_id=f'c{i}', reviewed_text=text) for i in range(2, 7))
    result = AnalysisResult(**request.model_dump(exclude={'clauses'}), coverage=Coverage(analysed=0, total=6))

    class InspectGenerator(FixtureGenerator):
        async def generate(self, generation):
            payload = json.loads(generation.user_prompt)
            assert 'available_result_items' not in payload
            assert len(generation.system_prompt + generation.user_prompt) < 8000
            excerpts = payload['relevant_reviewed_clauses']
            assert sum(len(c['reviewed_text'].encode('utf-8')) for c in excerpts) <= 3000
            assert any('INR 1500' in c['reviewed_text'] for c in excerpts)
            return await super().generate(generation)

    pipeline.generator = InspectGenerator()
    question = QuestionRequest(document_id=request.document_id, analysis_id=request.analysis_id,
        document_revision=request.document_revision, output_language='en',
        question='What is the monthly fee?', client_request_id='bounded-question')
    answer = asyncio.run(pipeline.answer(question, request, result))
    assert '1500' in answer.answer
    assert answer.evidence
    originals = {clause.clause_id: clause.reviewed_text for clause in request.clauses}
    assert all(ev.quote in originals[ev.clause_id] for ev in answer.evidence)
    assert 'question_context_limited' in answer.limitations


def test_numbered_clause_question_prioritizes_the_requested_clause():
    pipeline, _, _ = _pipeline()
    request = _request('agreement', 'numbered-question', 'This document has a heading.')
    request.clauses.extend([
        ClauseInput(clause_id='c2', reviewed_text='The tenant must send written notice.'),
        ClauseInput(clause_id='c3', reviewed_text='The monthly fee is INR 1500.'),
    ])
    result = AnalysisResult(**request.model_dump(exclude={'clauses'}), coverage=Coverage(analysed=0, total=3))
    question = QuestionRequest(document_id=request.document_id, analysis_id=request.analysis_id,
        document_revision=request.document_revision, output_language='en',
        question='What does clause 3 mean?', client_request_id='numbered-question')
    answer = asyncio.run(pipeline.answer(question, request, result))
    assert answer.evidence[0].clause_id == 'c3'
