/**
 * QuestionPanel Component (C-12)
 * Grounded Q&A strictly bound to document evidence:
 * - Document-scoped: answers are derived ONLY from extracted document text
 * - Input validation: 3–4000 chars, trimmed, enter to send
 * - Retry with idempotent client_request_id (UUIDv4 reused on 429 / timeout)
 * - Evidence cards with source quotes and working EvidenceButtons
 * - Honest out-of-scope / insufficient evidence handling
 * - In-memory history strictly capped at 20 questions (never persisted)
 * - Persistent disclaimer: Answers explain the document, not legal advice
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send,
  HelpCircle,
  RotateCw,
  Info,
  Sparkles,
  XCircle,
} from 'lucide-react';
import type { Clause } from '../../lib/types';
import { useResult } from './ResultContext';
import { useSession } from '../../lib/session';
import { askQuestion, ApiClientError } from '../../lib/api';
import { EvidenceButton } from './EvidenceButton';
import { ReferenceCard } from './ReferenceCard';
import { GlassCard, Button, Banner } from '../../design/primitives';
import { useT } from '../../lib/i18n';

interface QuestionPanelProps {
  onNavigateEvidence: (clauseId: string) => void;
  clauses?: Clause[];
}

export const QuestionPanel: React.FC<QuestionPanelProps> = ({
  onNavigateEvidence,
}) => {
  const { t } = useT();
  const { status, result, outputLanguage, analysisId, documentType, qaHistory, addQaHistory } = useResult();
  const { documentId, sessionToken } = useSession();

  const [questionText, setQuestionText] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [lastError, setLastError] = useState<{
    code: string;
    message: string;
    retryable: boolean;
    question: string;
    requestId: string;
  } | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Clean up on unmount
  useEffect(() => {
    setIsSubmitting(false);
    setLastError(null);
    return () => {
      abortControllerRef.current?.abort();
    };
  }, [documentId,analysisId,outputLanguage]);

  // Scroll to bottom on new answer
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [qaHistory, isSubmitting]);

  // Suggested questions
  const suggestedQuestions =
    documentType === 'fir'
      ? [
          'What offences are alleged in this FIR?',
          'Who is assigned to investigate?',
          'What is the alleged incident date?',
        ]
      : documentType === 'notice'
      ? [
          'What action is demanded by this notice?',
          'What is the deadline for replying?',
          'What amount is alleged to be due?',
        ]
      : [
          'What does clause 3 mean?',
          'What is the notice period for cancellation?',
          'Can this agreement renew automatically?',
        ];

  const handleSendQuestion = useCallback(
    async (textToSend?: string, existingRequestId?: string) => {
      const q = (textToSend || questionText).trim();
      if (q.length < 3 || q.length > 4000) return;
      if (isSubmitting) return;

      const reqId = existingRequestId || crypto.randomUUID();
      setIsSubmitting(true);
      setLastError(null);

      abortControllerRef.current?.abort();
      abortControllerRef.current = new AbortController();

      // Clear input if sending new question
      if (!existingRequestId) {
        setQuestionText('');
      }

      if (!documentId || !sessionToken || !analysisId) {
        setIsSubmitting(false);
        return;
      }

      try {
        const resp = await askQuestion(
          documentId,
          sessionToken,
          {
            analysis_id: analysisId,
            question: q,
            output_language: outputLanguage,
            client_request_id: reqId,
          },
          abortControllerRef.current.signal
        );

        addQaHistory({
          id: reqId,
          question: q,
          clientRequestId: reqId,
          answer: resp,
          timestamp: Date.now(),
        });

        setIsSubmitting(false);
      } catch (err: unknown) {
        setIsSubmitting(false);
        if(err instanceof DOMException && err.name==='AbortError') return;

        if (err instanceof ApiClientError) {
          if (err.status === 429) {
            setLastError({
              code: 'MODEL_BUSY',
              message: 'AI processor is currently busy with another task.',
              retryable: true,
              question: q,
              requestId: reqId,
            });
            return;
          }
          if (err.code === 'MODEL_TIMEOUT') {
            setLastError({
              code: 'MODEL_TIMEOUT',
              message: 'Question request timed out. You may retry.',
              retryable: true,
              question: q,
              requestId: reqId,
            });
            return;
          }
        }

        setLastError({
          code: 'NETWORK_ERROR',
          message: 'Unable to reach question answering service.',
          retryable: true,
          question: q,
          requestId: reqId,
        });
      }
    },
    [
      questionText,
      isSubmitting,
      documentId,
      sessionToken,
      analysisId,
      outputLanguage,
      addQaHistory,
    ]
  );

  const handleCancel = () => {
    abortControllerRef.current?.abort();
    setIsSubmitting(false);
  };

  const handleRetry = () => {
    if (lastError && lastError.retryable) {
      handleSendQuestion(lastError.question, lastError.requestId);
    }
  };

  // Disabled state guard until analysis is complete/needs_review
  const isTerminal = status === 'complete' || status === 'needs_review';
  if (!isTerminal) {
    return (
      <GlassCard className="p-8 text-center space-y-4">
        <div className="w-12 h-12 rounded-full bg-blue/10 text-blue flex items-center justify-center mx-auto">
          <HelpCircle className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h3 className="text-base font-bold text-navy">{t('qa.title')}</h3>
          <p className="text-xs text-mute max-w-sm mx-auto">
            {t('qa.sub')}
          </p>
        </div>
      </GlassCard>
    );
  }

  const isLengthValid = questionText.trim().length >= 3 && questionText.trim().length <= 4000;

  return (
    <div className="space-y-6">
      {/* Disclaimer Banner */}
      <div className="text-xs text-mute flex items-center justify-between pb-2 border-b border-line">
        <div className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-blue" />
          <span>{t('qa.sub')}</span>
        </div>
        <span className="font-mono text-[11px] text-mute">
          History: {qaHistory.length}/20 (In-Memory)
        </span>
      </div>

      {/* Suggested Questions */}
      {qaHistory.length === 0 && (
        <div className="space-y-2">
          <span className="text-[11px] font-mono uppercase text-mute font-semibold">
            {t('qa.suggestedTitle')}
          </span>
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions.map((sq, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setQuestionText(sq)}
                className="px-3 py-1.5 rounded-full text-xs bg-paper border border-line hover:border-blue hover:text-blue transition-colors text-navy text-left font-medium"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Conversation Thread */}
      <div className="space-y-4 min-h-[160px]">
        {qaHistory.map((entry) => (
          <div key={entry.id} className="space-y-3">
            {/* User Question */}
            <div className="flex justify-end">
              <div className="max-w-[85%] p-3.5 rounded-lg bg-navy text-white text-xs leading-relaxed shadow-xs">
                {entry.question}
              </div>
            </div>

            {/* System Answer */}
            {entry.answer && (
              <div className="flex justify-start">
                <GlassCard className="max-w-[90%] p-4 space-y-3 border-line bg-paper/90 shadow-card">
                  {/* Status chip */}
                  <div className="flex items-center justify-between pb-2 border-b border-line">
                    <span className="text-[11px] font-mono font-bold uppercase text-blue">
                      Document Grounded Answer
                    </span>
                    {entry.answer.review_status === 'needs_review' ? (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-800 border border-amber-500/20">
                        Unverified / Needs Review
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-ok/10 text-ok border border-ok/20">
                        Verified Grounding
                      </span>
                    )}
                  </div>

                  {/* Answer Text */}
                  <p className="text-xs text-navy font-medium leading-[1.7] whitespace-pre-line">
                    {entry.answer.answer}
                  </p>

                  {/* Insufficient Evidence Notice */}
                  {entry.answer.evidence.length === 0 && (
                    <div className="p-2.5 rounded bg-blue/5 border border-blue/20 text-xs text-navy flex items-start gap-2">
                      <Info className="w-4 h-4 text-blue shrink-0 mt-0.5" />
                      <span>
                        {t('qa.insufficientEvidence')}
                      </span>
                    </div>
                  )}

                  {/* Evidence Quotes */}
                  {entry.answer.evidence.length > 0 && (
                    <div className="space-y-2 pt-2 border-t border-line/60">
                      <span className="text-[10px] font-mono uppercase text-mute font-semibold">
                        Anchored Evidence ({entry.answer.evidence.length})
                      </span>
                      {entry.answer.evidence.map((ev, idx) => (
                        <div
                          key={idx}
                          className="p-2.5 rounded bg-bg2/60 border border-line text-xs space-y-1.5"
                        >
                          <blockquote className="font-serif italic text-navy/90 border-l-2 border-blue pl-2">
                            "{ev.quote}"
                          </blockquote>
                          <div className="flex justify-end">
                            <EvidenceButton
                              clauseId={ev.clause_id}
                              onNavigateEvidence={onNavigateEvidence}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* References (if any resolve) */}
                  {entry.answer.reference_ids && entry.answer.reference_ids.length > 0 && (
                    <div className="space-y-2 pt-2 border-t border-line/60">
                      {entry.answer.reference_ids.map((refId) => {
                        const refObj = result?.references?.find((r) => r.reference_id === refId);
                        if (!refObj) return null;
                        return <ReferenceCard key={refId} reference={refObj} />;
                      })}
                    </div>
                  )}

                  {/* Answer Disclaimer */}
                  <div className="pt-2 border-t border-line/40 text-[10px] font-mono text-mute flex items-center justify-between">
                    <span>{t('disclaimers.footer')}</span>
                    <span>Clause-grounded</span>
                  </div>
                </GlassCard>
              </div>
            )}
          </div>
        ))}

        {/* In-Flight Typing Skeleton */}
        {isSubmitting && (
          <div className="flex justify-start">
            <GlassCard className="p-4 space-y-3 max-w-[80%] bg-paper">
              <div className="flex items-center justify-between">
                <span className="text-xs text-mute font-mono flex items-center gap-2">
                  <RotateCw className="w-3.5 h-3.5 animate-spin text-blue" />
                  {t('qa.askingButton')}
                </span>
                <button
                  type="button"
                  onClick={handleCancel}
                  className="text-xs text-mute hover:text-navy flex items-center gap-1 font-mono"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  {t('privacy.cancel')}
                </button>
              </div>
              <div className="space-y-2">
                <div className="h-3 bg-bg2 rounded w-3/4 animate-pulse" />
                <div className="h-3 bg-bg2 rounded w-1/2 animate-pulse" />
              </div>
            </GlassCard>
          </div>
        )}

        <div ref={messagesEndRef} aria-live="polite" className="sr-only">
          {qaHistory.length > 0 ? 'Answer ready' : ''}
        </div>
      </div>

      {/* Error Retry Banner */}
      {lastError && (
        <Banner
          variant="error"
          title="Question Error"
          action={
            lastError.retryable
              ? { label: 'Retry Question', onClick: handleRetry }
              : undefined
          }
        >
          {lastError.message}
        </Banner>
      )}

      {/* Question Input Form */}
      <div className="space-y-2 pt-2 border-t border-line">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendQuestion();
          }}
          className="space-y-2"
        >
          <div className="relative">
            <textarea
              rows={2}
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendQuestion();
                }
              }}
              placeholder={t('qa.placeholder')}
              disabled={isSubmitting}
              className="w-full p-3 pr-24 text-xs rounded-lg border border-line bg-paper text-navy focus:outline-hidden focus:ring-2 focus:ring-blue resize-none leading-relaxed"
            />

            <div className="absolute right-2 bottom-3 flex items-center gap-2">
              <span className="text-[10px] font-mono text-mute">
                {t('qa.charCount', { count: questionText.trim().length })}
              </span>
              <Button
                type="submit"
                size="sm"
                variant="primary"
                disabled={!isLengthValid || isSubmitting}
                className="px-3 py-1.5"
              >
                {isSubmitting ? (
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Send className="w-3.5 h-3.5" />
                )}
                <span>{t('qa.askButton')}</span>
              </Button>
            </div>
          </div>

          {/* Legal Advice Guard Persistent Notice */}
          <div className="flex items-center justify-between text-[11px] text-mute">
            <span>{t('disclaimers.answersNotAdvice')}</span>
            <span className="font-mono text-[10px]">Enter to send · Shift+Enter newline</span>
          </div>
        </form>
      </div>
    </div>
  );
};
export default QuestionPanel;
