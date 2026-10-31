/**
 * ExtractionScreen Component (P-02)
 * Asynchronous polling screen while server runs local PDF parser and OCR.
 * - Displays honest status text without synthetic progress percentages
 * - Measures real elapsed time in mono
 * - Fetches authenticated binary Blob upon extraction readiness
 * - Gracefully handles cancel, session deletion, and low scan quality warnings
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../../lib/session';
import { useT } from '../../lib/i18n';
import { useToast } from '../../design/primitives';
import { usePolling } from '../../lib/usePolling';
import { getDocument, fetchSourceBlob, getExtraction, ApiClientError } from '../../lib/api';
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
  const completionAbortRef = useRef<AbortController | null>(null);
  useEffect(() => () => completionAbortRef.current?.abort(), []);

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

      if (!documentId || !sessionToken) {
        throw new Error('No session active');
      }

      return await getDocument(documentId, sessionToken, signal);
    },
    [documentId, sessionToken]
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

      if (!documentId || !sessionToken) return;
      completionAbortRef.current?.abort();
      const controller = new AbortController();
      completionAbortRef.current = controller;

      try {
        // Load both authenticated resources before navigating to review.
        const [blob, ext] = await Promise.all([
          fetchSourceBlob(documentId, sessionToken, controller.signal),
          getExtraction(documentId, sessionToken, controller.signal),
        ]);
        if (controller.signal.aborted) return;
        const blobUrl = URL.createObjectURL(blob);
        setSourceBlobUrl(blobUrl);

        if (ext.warnings && ext.warnings.length > 0) {
          setWarnings(ext.warnings);
        }

        // 3. Proceed to review screen
        navigate('/workspace?step=review');
      } catch (err: unknown) {
        if (controller.signal.aborted) return;
        const msg = err instanceof Error ? err.message : 'Failed to retrieve extracted clauses';
        setErrorMessage(msg);
        setErrorCode('EXTRACTION_FAILED');
        setShowErrorOverlay(true);
      }
    },
    [documentId, sessionToken, setDocumentStatus, setSourceBlobUrl, setWarnings, setServerExpiresAt, navigate]
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
