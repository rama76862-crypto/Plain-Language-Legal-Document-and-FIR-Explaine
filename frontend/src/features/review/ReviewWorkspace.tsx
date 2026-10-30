/**
 * ReviewWorkspace Component (P-03)
 * Orchestrates the two-pane review layout:
 * - Left Pane: SourceDocumentViewer (PDF canvas or DOCX structure)
 * - Right Pane: ExtractionReviewList (clause review, editing, revision management)
 * - Manages optimistic locking (PATCH /extraction) and conflict resolution (409)
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { SourceDocumentViewer, SourceDocumentViewerRef } from '../source/SourceDocumentViewer';
import { ExtractionReviewList } from './ExtractionReviewList';
import { useSession } from '../../lib/session';
import { getExtraction, patchExtraction, ApiClientError } from '../../lib/api';
import { config } from '../../lib/config';
import { fixtureRentAgreementExtraction } from '../../lib/fixtures';
import type { Clause, PatchRequest } from '../../lib/types';
import { ErrorConflictOverlay } from '../../app/ErrorConflictOverlay';
import { Skeleton } from '../../design/primitives';

export const ReviewWorkspace: React.FC = () => {
  const {
    documentId,
    sessionToken,
    revision,
    filename,
    inputLanguage,
    outputLanguage,
    documentType,
    selectedClauseId,
    sourceBlobUrl,
    warnings,
    setRevision,
    setInputLanguage,
    setOutputLanguage,
    setDocumentType,
    selectClause,
    setReviewConfirmed,
    setWarnings,
    resetSession,
  } = useSession();

  const navigate = useNavigate();
  const sourceViewerRef = useRef<SourceDocumentViewerRef | null>(null);

  const [clauses, setClauses] = useState<Clause[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [conflictOpen, setConflictOpen] = useState<boolean>(false);
  const [conflictError, setConflictError] = useState<{ message: string; code: string }>({
    message: '',
    code: '',
  });

  // Fetch extraction on mount
  const loadExtraction = useCallback(async () => {
    setLoading(true);

    if (config.useFixtures) {
      setClauses(fixtureRentAgreementExtraction.clauses);
      if (fixtureRentAgreementExtraction.warnings) {
        setWarnings(fixtureRentAgreementExtraction.warnings);
      }
      setLoading(false);
      return;
    }

    if (!documentId || !sessionToken) {
      navigate('/');
      return;
    }

    try {
      const ext = await getExtraction(documentId, sessionToken);
      setClauses(ext.clauses);
      setRevision(ext.revision);
      if (ext.input_language === 'en' || ext.input_language === 'hi' || ext.input_language === 'pa') {
        setInputLanguage(ext.input_language);
      }
      if (['agreement', 'fir', 'notice', 'other'].includes(ext.document_type)) {
        setDocumentType(ext.document_type);
      }
      if (ext.warnings && ext.warnings.length > 0) {
        setWarnings(ext.warnings);
      }
    } catch (err: unknown) {
      if (err instanceof ApiClientError && err.status === 404) {
        setConflictError({ code: 'NOT_FOUND', message: 'Session expired' });
        setConflictOpen(true);
      }
    } finally {
      setLoading(false);
    }
  }, [documentId, sessionToken, setRevision, setWarnings, setInputLanguage, setDocumentType, navigate]);

  useEffect(() => {
    loadExtraction();
  }, [loadExtraction]);

  const handleSelectClause = (clauseId: string) => {
    selectClause(clauseId);
    sourceViewerRef.current?.scrollToClause(clauseId);
  };

  const handleSubmitReview = async (patch: PatchRequest) => {
    setIsSubmitting(true);

    if (config.useFixtures) {
      setTimeout(() => {
        // Increment revision if corrections exist
        if (patch.corrections.length > 0) {
          setRevision(revision + 1);
        }
        setReviewConfirmed(true);
        setIsSubmitting(false);
        navigate('/workspace?step=results');
      }, 500);
      return;
    }

    if (!documentId || !sessionToken) return;

    try {
      const res = await patchExtraction(documentId, sessionToken, patch);
      setRevision(res.revision);
      setReviewConfirmed(true);
      navigate('/workspace?step=results');
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        if (err.status === 409 || err.code === 'REVISION_CONFLICT') {
          setConflictError({
            code: 'REVISION_CONFLICT',
            message: 'The document was modified in another session. Your view is outdated.',
          });
          setConflictOpen(true);
        } else if (err.status === 404) {
          setConflictError({
            code: 'NOT_FOUND',
            message: 'Document session expired.',
          });
          setConflictOpen(true);
        }
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReloadConflict = async () => {
    setConflictOpen(false);
    await loadExtraction();
  };

  if (loading) {
    return (
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 p-6 gap-6">
        <Skeleton className="h-[70vh] rounded-lg" />
        <Skeleton className="h-[70vh] rounded-lg" />
      </div>
    );
  }

  return (
    <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 h-[calc(100vh-8.5rem)] overflow-hidden">
      {/* Left Pane: Source Document Viewer (5 cols) */}
      <div className="lg:col-span-5 h-full overflow-hidden">
        <SourceDocumentViewer
          ref={sourceViewerRef}
          filename={filename}
          blobUrl={sourceBlobUrl}
          clauses={clauses}
          activeClauseId={selectedClauseId}
        />
      </div>

      {/* Right Pane: Extraction Review & Correction (7 cols) */}
      <div className="lg:col-span-7 h-full overflow-hidden border-l border-line">
        <ExtractionReviewList
          clauses={clauses}
          revision={revision}
          warnings={warnings}
          filename={filename}
          inputLanguage={inputLanguage}
          outputLanguage={outputLanguage}
          documentType={documentType}
          selectedClauseId={selectedClauseId}
          isSubmitting={isSubmitting}
          onSelectClause={handleSelectClause}
          onSubmitReview={handleSubmitReview}
          onChangeInputLanguage={setInputLanguage}
          onChangeOutputLanguage={setOutputLanguage}
          onChangeDocumentType={setDocumentType}
        />
      </div>

      {/* Revision Conflict Overlay */}
      <ErrorConflictOverlay
        isOpen={conflictOpen}
        errorCode={conflictError.code}
        errorMessage={conflictError.message}
        onReload={handleReloadConflict}
        onWipe={async () => {
          setConflictOpen(false);
          await resetSession(true);
          navigate('/');
        }}
        onClose={() => setConflictOpen(false)}
      />
    </div>
  );
};
export default ReviewWorkspace;
