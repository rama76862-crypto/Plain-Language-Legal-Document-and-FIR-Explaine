/**
 * ResultsContainer Component
 * Orchestrates the two-pane results view:
 * - Left Pane: SourceDocumentViewer (PDF canvas or DOCX paragraphs)
 * - Right Pane: ResultsWorkspace (Overview, Clauses, Attention, Dates, Q&A, Export)
 * - Synchronizes clause evidence navigation across panes
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { SourceDocumentViewer, SourceDocumentViewerRef } from '../source/SourceDocumentViewer';
import { ResultsWorkspace } from './ResultsWorkspace';
import { useSession } from '../../lib/session';
import { getExtraction } from '../../lib/api';
import { config } from '../../lib/config';
import { fixtureRentAgreementExtraction } from '../../lib/fixtures';
import type { Clause } from '../../lib/types';
import { Skeleton, SegmentedControl } from '../../design/primitives';

export const ResultsContainer: React.FC = () => {
  const {
    documentId,
    sessionToken,
    revision,
    filename,
    outputLanguage,
    selectedClauseId,
    sourceBlobUrl,
    selectClause,
    resetSession,
  } = useSession();

  const navigate = useNavigate();
  const sourceViewerRef = useRef<SourceDocumentViewerRef | null>(null);

  const [clauses, setClauses] = useState<Clause[]>([]);
  const [loadingClauses, setLoadingClauses] = useState<boolean>(true);
  const [mobileTab, setMobileTab] = useState<'source' | 'results'>('results');

  // Load clauses for source viewer navigation
  useEffect(() => {
    let isCancelled = false;

    async function load() {
      if (config.useFixtures) {
        setClauses(fixtureRentAgreementExtraction.clauses);
        setLoadingClauses(false);
        return;
      }

      if (!documentId || !sessionToken) {
        navigate('/');
        return;
      }

      try {
        const ext = await getExtraction(documentId, sessionToken);
        if (!isCancelled) {
          setClauses(ext.clauses);
        }
      } catch {
        // Non-blocking; source viewer can render empty or fallback
      } finally {
        if (!isCancelled) {
          setLoadingClauses(false);
        }
      }
    }

    load();
    return () => {
      isCancelled = true;
    };
  }, [documentId, sessionToken, revision, navigate]);

  const handleNavigateEvidence = useCallback(
    (clauseId: string) => {
      selectClause(clauseId);
      sourceViewerRef.current?.scrollToClause(clauseId);
      // On mobile, auto-switch to source view
      if (window.innerWidth < 1024) {
        setMobileTab('source');
      }
    },
    [selectClause]
  );

  const handleDeleted = useCallback(async () => {
    await resetSession(false);
    navigate('/');
  }, [resetSession, navigate]);

  if (loadingClauses) {
    return (
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 p-6 gap-6">
        <div className="lg:col-span-5">
          <Skeleton className="h-[75vh] rounded-lg" />
        </div>
        <div className="lg:col-span-7">
          <Skeleton className="h-[75vh] rounded-lg" />
        </div>
      </div>
    );
  }

  if (!documentId || !sessionToken) {
    return null;
  }

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-8.5rem)] overflow-hidden">
      {/* Mobile Switcher (Visible on < lg screens) */}
      <div className="lg:hidden p-2 bg-paper border-b border-line flex justify-center">
        <SegmentedControl
          options={[
            { value: 'results', label: 'Plain Explanations' },
            { value: 'source', label: 'Original Document' },
          ]}
          value={mobileTab}
          onChange={(val) => setMobileTab(val as 'source' | 'results')}
        />
      </div>

      {/* Main Two-Pane Split */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 h-full overflow-hidden">
        {/* Left Pane: Source Document Viewer (5 cols) */}
        <div
          className={`lg:col-span-5 h-full overflow-hidden ${
            mobileTab === 'source' ? 'block' : 'hidden lg:block'
          }`}
        >
          <SourceDocumentViewer
            ref={sourceViewerRef}
            filename={filename}
            blobUrl={sourceBlobUrl}
            clauses={clauses}
            activeClauseId={selectedClauseId}
          />
        </div>

        {/* Right Pane: Results Workspace (7 cols) */}
        <div
          className={`lg:col-span-7 h-full overflow-hidden border-l border-line ${
            mobileTab === 'results' ? 'block' : 'hidden lg:block'
          }`}
        >
          <ResultsWorkspace
            documentId={documentId}
            sessionToken={sessionToken}
            revision={revision}
            outputLanguage={outputLanguage}
            onNavigateEvidence={handleNavigateEvidence}
            onDeleted={handleDeleted}
          />
        </div>
      </div>
    </div>
  );
};
export default ResultsContainer;
