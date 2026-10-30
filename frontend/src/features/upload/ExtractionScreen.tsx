/**
 * ExtractionScreen Component (P-02)
 * Asynchronous polling screen while server runs local PDF parser and OCR.
 * - Displays honest status text without synthetic progress percentages
 * - Measures real elapsed time in mono
 * - Fetches authenticated binary Blob upon extraction readiness
 * - Gracefully handles cancel, session deletion, and low scan quality warnings
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../../lib/session';
import { useT } from '../../lib/i18n';
import { useToast } from '../../design/primitives';
import { usePolling } from '../../lib/usePolling';
import { getDocument, fetchSourceBlob, getExtraction, ApiClientError } from '../../lib/api';
import { config } from '../../lib/config';
import { fixtureRentAgreementExtraction } from '../../lib/fixtures';
import type { DocumentSummary } from '../../lib/types';
import { GlassCard, Button, Banner, MonoLabel } from '../../design/primitives';
import { useReducedMotion } from '../../design/motion';
import { ErrorConflictOverlay } from '../../app/ErrorConflictOverlay';
import { FileText, Loader2, XCircle, Clock } from 'lucide-react';

export const ExtractionScreen: React.FC = () => {
  const {
    documentId,
    sessionToken,
    filename,
    inputLanguage,
    outputLanguage,
    documentType,
    setDocumentStatus,
    setSourceBlobUrl,
    setWarnings,
    setServerExpiresAt,
    resetSession,
  } = useSession();
  const { t } = useT();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const reduced = useReducedMotion();

  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [showErrorOverlay, setShowErrorOverlay] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);

  // Elapsed time counter
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatElapsed = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Poll function
  const pollDoc = useCallback(
    async (signal: AbortSignal): Promise<DocumentSummary> => {
      const isFixture = config.useFixtures || documentId?.startsWith('doc_fixture_');
      if (isFixture) {
        // Fixture simulation: after 2 seconds transition to awaiting_review
        if (elapsedSeconds >= 2) {
          return {
            document_id: documentId || 'doc_fixture_rent_01',
            status: 'awaiting_review',
            revision: 1,
            filename: filename || 'sample_document.pdf',
            document_type: documentType,
            input_language: inputLanguage,
            warnings: fixtureRentAgreementExtraction.warnings,
            extraction_ready: true,
          };
        }
        return {
          document_id: documentId || 'doc_fixture_rent_01',
          status: 'extracting',
          revision: 1,
          filename: filename || 'sample_document.pdf',
          document_type: documentType,
          input_language: inputLanguage,
          warnings: [],
          extraction_ready: false,
        };
      }

      if (!documentId || !sessionToken) {
        throw new Error('No session active');
      }

      return await getDocument(documentId, sessionToken, signal);
    },
    [documentId, sessionToken, filename, documentType, inputLanguage, elapsedSeconds]
  );

  const handleExtractionComplete = useCallback(
    async (doc: DocumentSummary) => {
      setDocumentStatus(doc.status);
      if (doc.expires_at) {
        setServerExpiresAt(doc.expires_at);
      }
      if (doc.warnings && doc.warnings.length > 0) {
        setWarnings(doc.warnings);
      }

      const isFixture = config.useFixtures || documentId?.startsWith('doc_fixture_');
      if (isFixture) {
        // Create a valid minimal PDF Blob for PDF viewer in fixture mode
        const minimalPdfBytes = new Uint8Array([
          0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x34, 0x0a, 0x31, 0x20, 0x30, 0x20, 0x6f, 0x62, 0x6a,
          0x3c, 0x3c, 0x2f, 0x54, 0x79, 0x70, 0x65, 0x2f, 0x43, 0x61, 0x74, 0x61, 0x6c, 0x6f, 0x67, 0x2f,
          0x50, 0x61, 0x67, 0x65, 0x73, 0x20, 0x32, 0x20, 0x30, 0x20, 0x52, 0x3e, 0x3e, 0x65, 0x6e, 0x64,
          0x6f, 0x62, 0x6a, 0x0a, 0x32, 0x20, 0x30, 0x20, 0x6f, 0x62, 0x6a, 0x3c, 0x3c, 0x2f, 0x54, 0x79,
          0x70, 0x65, 0x2f, 0x50, 0x61, 0x67, 0x65, 0x73, 0x2f, 0x43, 0x6f, 0x75, 0x6e, 0x74, 0x20, 0x31,
          0x2f, 0x4b, 0x69, 0x64, 0x73, 0x5b, 0x33, 0x20, 0x30, 0x20, 0x52, 0x5d, 0x3e, 0x3e, 0x65, 0x6e,
          0x64, 0x6f, 0x62, 0x6a, 0x0a, 0x33, 0x20, 0x30, 0x20, 0x6f, 0x62, 0x6a, 0x3c, 0x3c, 0x2f, 0x54,
          0x79, 0x70, 0x65, 0x2f, 0x50, 0x61, 0x67, 0x65, 0x2f, 0x4d, 0x65, 0x64, 0x69, 0x61, 0x42, 0x6f,
          0x78, 0x5b, 0x30, 0x20, 0x30, 0x20, 0x36, 0x31, 0x32, 0x20, 0x37, 0x39, 0x32, 0x5d, 0x2f, 0x50,
          0x61, 0x72, 0x65, 0x6e, 0x74, 0x20, 0x32, 0x20, 0x30, 0x20, 0x52, 0x2f, 0x52, 0x65, 0x73, 0x6f,
          0x75, 0x72, 0x63, 0x65, 0x73, 0x3c, 0x3c, 0x3e, 0x3e, 0x3e, 0x3e, 0x65, 0x6e, 0x64, 0x6f, 0x62,
          0x6a, 0x0a, 0x78, 0x72, 0x65, 0x66, 0x0a, 0x30, 0x20, 0x34, 0x0a, 0x30, 0x30, 0x30, 0x30, 0x30,
          0x30, 0x30, 0x30, 0x30, 0x30, 0x20, 0x36, 0x35, 0x35, 0x33, 0x35, 0x20, 0x66, 0x20, 0x0a, 0x30,
          0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x39, 0x20, 0x30, 0x30, 0x30, 0x30, 0x30, 0x20,
          0x6e, 0x20, 0x0a, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x35, 0x32, 0x20, 0x30, 0x30,
          0x30, 0x30, 0x30, 0x20, 0x6e, 0x20, 0x0a, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x31, 0x30,
          0x31, 0x20, 0x30, 0x30, 0x30, 0x30, 0x30, 0x20, 0x6e, 0x20, 0x0a, 0x74, 0x72, 0x61, 0x69, 0x6c,
          0x65, 0x72, 0x3c, 0x3c, 0x2f, 0x53, 0x69, 0x7a, 0x65, 0x20, 0x34, 0x2f, 0x52, 0x6f, 0x6f, 0x74,
          0x20, 0x31, 0x20, 0x30, 0x20, 0x52, 0x3e, 0x3e, 0x0a, 0x73, 0x74, 0x61, 0x72, 0x74, 0x78, 0x72,
          0x65, 0x66, 0x0a, 0x31, 0x37, 0x38, 0x0a, 0x25, 0x25, 0x45, 0x4f, 0x46, 0x0a
        ]);
        const dummyBlob = new Blob([minimalPdfBytes], { type: 'application/pdf' });
        const blobUrl = URL.createObjectURL(dummyBlob);
        setSourceBlobUrl(blobUrl);
        navigate('/workspace?step=review');
        return;
      }

      if (!documentId || !sessionToken) return;

      try {
        // 1. Fetch authenticated binary source blob
        const blob = await fetchSourceBlob(documentId, sessionToken);
        const blobUrl = URL.createObjectURL(blob);
        setSourceBlobUrl(blobUrl);

        // 2. Fetch extracted clauses
        const ext = await getExtraction(documentId, sessionToken);
        if (ext.warnings && ext.warnings.length > 0) {
          setWarnings(ext.warnings);
        }

        // 3. Proceed to review screen
        navigate('/workspace?step=review');
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to retrieve extracted clauses';
        setErrorMessage(msg);
        setErrorCode('EXTRACTION_FAILED');
        setShowErrorOverlay(true);
      }
    },
    [documentId, sessionToken, setDocumentStatus, setSourceBlobUrl, setWarnings, navigate]
  );

  const { connectionLost, retry, stop } = usePolling<DocumentSummary>(pollDoc, {
    intervalMs: 1500,
    shouldStop: (doc) => doc.status === 'awaiting_review' || doc.status === 'failed',
    onSuccess: (doc) => {
      if (doc.status === 'awaiting_review') {
        handleExtractionComplete(doc);
      } else if (doc.status === 'failed') {
        setDocumentStatus('failed');
        setErrorMessage('Extraction engine failed to parse document text.');
        setErrorCode('EXTRACTION_FAILED');
      }
    },
    onError: (err: unknown) => {
      if (err instanceof ApiClientError) {
        if (err.status === 404) {
          stop();
          setErrorCode('NOT_FOUND');
          setErrorMessage(t('errors.NOT_FOUND'));
          setShowErrorOverlay(true);
        } else if (err.code === 'OCR_UNAVAILABLE') {
          stop();
          setErrorCode('OCR_UNAVAILABLE');
          setErrorMessage(t('extraction.ocrUnavailableWarn'));
          setShowErrorOverlay(true);
        }
      }
    },
  });

  const handleCancelUpload = async () => {
    setIsCancelling(true);
    stop();
    await resetSession(true);
    showToast(t('privacy.uploadCancelledToast'), 'info');
    navigate('/');
  };

  return (
    <main className="min-h-[75vh] flex items-center justify-center p-6">
      <GlassCard className="max-w-xl w-full p-8 rounded-lg shadow-card space-y-6 text-center">
        {/* Animated Document Scan Graphic */}
        <div className="relative w-28 h-36 mx-auto bg-paper rounded-lg shadow-sm border border-line flex flex-col justify-between p-3 overflow-hidden select-none">
          <div className="space-y-1.5 opacity-60">
            <div className="w-12 h-2 bg-blue/30 rounded" />
            <div className="w-full h-1.5 bg-line rounded" />
            <div className="w-4/5 h-1.5 bg-line rounded" />
            <div className="w-full h-1.5 bg-line rounded" />
          </div>

          {!reduced && (
            <div className="absolute inset-x-0 h-1 bg-gradient-to-r from-transparent via-cyan to-transparent animate-pulse transform -translate-y-full"
                 style={{
                   animation: 'scan-loop 2s ease-in-out infinite alternate',
                 }}
            />
          )}

          <div className="flex justify-between items-center text-[10px] font-mono text-mute border-t border-line/60 pt-1">
            <span>OCR</span>
            <span>PDF</span>
          </div>
        </div>

        <style>{`
          @keyframes scan-loop {
            0% { top: 0%; }
            100% { top: 100%; }
          }
        `}</style>

        {/* File Metadata */}
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 font-semibold text-navy text-sm max-w-sm truncate">
            <FileText className="w-4 h-4 text-blue shrink-0" aria-hidden="true" />
            <span className="truncate">{filename || 'Document'}</span>
          </div>
          <div className="text-xs font-mono text-mute flex items-center justify-center gap-3">
            <span>Input: {inputLanguage.toUpperCase()}</span>
            <span>·</span>
            <span>Target: {outputLanguage.toUpperCase()}</span>
            <span>·</span>
            <span>Type: {documentType}</span>
          </div>
        </div>

        {/* Real Status Copy (No Fake Percentage) */}
        <div className="space-y-2 py-2">
          <div className="flex items-center justify-center gap-2 text-sm font-bold text-navy">
            <Loader2 className="w-4 h-4 text-blue animate-spin" aria-hidden="true" />
            <span>{t('status.extracting')}</span>
          </div>
          <div className="text-xs font-mono text-mute flex items-center justify-center gap-1.5">
            <Clock className="w-3.5 h-3.5" aria-hidden="true" />
            <span>{t('extraction.elapsed', { time: formatElapsed(elapsedSeconds) })}</span>
          </div>
        </div>

        {/* Long Extraction Note (after 45s) */}
        {elapsedSeconds >= 45 && (
          <div className="text-xs text-mute font-medium bg-bg2/80 p-2.5 rounded border border-line">
            {t('extraction.largeFileNote')}
          </div>
        )}

        {/* Connection Lost Banner */}
        {connectionLost && (
          <Banner
            variant="error"
            title={t('results.connectionLost')}
            action={{ label: t('results.retryAnalysis'), onClick: retry }}
          >
            {t('errors.NETWORK_ERROR')}
          </Banner>
        )}

        {/* Failure Message */}
        {errorMessage && (
          <Banner
            variant="error"
            title={t('extraction.failedTitle')}
            action={{ label: t('extraction.retryClearer'), onClick: () => navigate('/') }}
          >
            {errorMessage}
          </Banner>
        )}

        {/* Actions Row */}
        <div className="pt-4 border-t border-line flex items-center justify-between">
          <MonoLabel>LOCAL EXTRACTION PIPELINE</MonoLabel>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCancelUpload}
            isLoading={isCancelling}
            leftIcon={<XCircle className="w-4 h-4 text-mute" />}
          >
            {t('extraction.cancelButton')}
          </Button>
        </div>
      </GlassCard>

      {/* Global Error Conflict Overlay */}
      <ErrorConflictOverlay
        isOpen={showErrorOverlay}
        errorCode={errorCode || 'UNKNOWN'}
        errorMessage={errorMessage || 'An error occurred'}
        onRetry={retry}
        onWipe={async () => {
          setShowErrorOverlay(false);
          await resetSession(true);
          navigate('/');
        }}
        onClose={() => setShowErrorOverlay(false)}
      />
    </main>
  );
};
export default ExtractionScreen;
