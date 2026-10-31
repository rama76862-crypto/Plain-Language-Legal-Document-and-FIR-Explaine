/**
 * WorkspaceRouter Component
 * Guards /workspace access:
 * - Empty in-memory session -> redirects to / with banner explanation.
 * - Extracts step from query string (?step=extracting|review|results).
 * - Enforces progression: extracting -> review -> results.
 * - Mounts PipelineStepBar.
 */

import React from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useSession } from '../lib/session';
import { useT } from '../lib/i18n';
import { PipelineStepBar } from './PipelineStepBar';
import { Banner } from '../design/primitives';

// Placeholders for features that will be fully implemented in P5, P7, P8
import { ExtractionScreen } from '../features/upload/ExtractionScreen';
import { ReviewWorkspace } from '../features/review/ReviewWorkspace';
import { ResultsContainer } from '../features/results/ResultsContainer';

export const WorkspaceRouter: React.FC = () => {
  const { t } = useT();
  const { documentId, documentStatus, reviewConfirmed } = useSession();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const stepParam = searchParams.get('step') as 'extracting' | 'review' | 'results' | null;
  const currentStep = stepParam || 'extracting';

  // Guard: No active session
  if (!documentId) {
    return (
      <main className="p-8 max-w-xl mx-auto">
        <Banner
          variant="warn"
          title={t('errors.expiredTitle')}
          action={{ label: t('errors.returnToUpload'), onClick: () => navigate('/') }}
        >
          {t('errors.NOT_FOUND')}
        </Banner>
      </main>
    );
  }

  // Guard: Trying to access review while still extracting
  if (currentStep === 'review' && documentStatus === 'extracting') {
    setSearchParams({ step: 'extracting' });
    return null;
  }

  // Guard: Trying to access results before review confirmed
  if (currentStep === 'results' && !reviewConfirmed) {
    setSearchParams({ step: 'review' });
    return null;
  }

  const handleNavigateStep = (step: 'review' | 'results') => {
    setSearchParams({ step });
  };

  return (
    <div className="flex-1 flex flex-col">
      <PipelineStepBar
        currentStep={currentStep}
        onNavigateStep={handleNavigateStep}
      />
      <div className="flex-1 flex flex-col">
        {currentStep === 'extracting' && <ExtractionScreen />}
        {currentStep === 'review' && <ReviewWorkspace />}
        {currentStep === 'results' && <ResultsContainer />}
      </div>
    </div>
  );
};
