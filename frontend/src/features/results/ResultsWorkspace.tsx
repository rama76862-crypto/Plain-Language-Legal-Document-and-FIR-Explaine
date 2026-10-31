/**
 * ResultsWorkspace Component (C-07)
 * Primary workspace for document explanations, attention cues, deadlines, Q&A, and export.
 * Follows exact ResultsWorkspaceProps contract.
 */

import React from 'react';
import { ActionPackPanel } from './ActionPackPanel';
import { ComparePanel } from './ComparePanel';
import { SourceVerificationPanel } from './SourceVerificationPanel';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  Calendar,
  MessageSquare,
  Download,
  RotateCw,
  Sparkles,
  Layers,
  ShieldAlert,
  Scale,
  ClipboardList,
  GitCompare,
  ShieldCheck,
} from 'lucide-react';
import type { ResultsWorkspaceProps, OutputLanguage } from '../../lib/types';
import { ResultProvider, useResult, ResultTab } from './ResultContext';
import { useT } from '../../lib/i18n';
import { OverviewSummaryPanel } from './OverviewSummaryPanel';
import { ClauseExplanationList } from './ClauseExplanationList';
import { AttentionPanel } from './AttentionPanel';
import { DeadlinePanel } from './DeadlinePanel';
import { QuestionPanel } from './QuestionPanel';
import { ResultExport } from './ResultExport';
import { LegalAidDirectoryCard } from './LegalAidDirectoryCard';
import { GlassCard, Button, Banner, SegmentedControl } from '../../design/primitives';

const ResultsWorkspaceInner: React.FC<ResultsWorkspaceProps> = ({
  revision,
  onNavigateEvidence,
}) => {
  const { t } = useT();
  const {
    status,
    progress,
    result,
    activeTab,
    setActiveTab,
    outputLanguage,
    changeOutputLanguage,
    isAnalyzing,
    isDimmedLoading,
    pendingLanguage,
    error,
    startAnalysis,
    retryAnalysis,
    cancelAnalysis,
    isCancelling,
    analysisId,
    actionPack,
    verificationResult,
  } = useResult();

  const attentionCount = result?.items.filter(
    (i) => i.kind === 'attention' || i.kind === 'allegation' || i.kind === 'notice_action'
  ).length ?? 0;

  const datesCount = result?.deadlines.length ?? 0;

  const actionPackCount = actionPack?.checklist ? actionPack.checklist.length : undefined;
  const verifyIssuesCount =
    verificationResult?.issues && verificationResult.issues.length > 0
      ? verificationResult.issues.length
      : undefined;

  const tabs: { id: ResultTab; label: string; icon: React.FC<{ className?: string }>; badge?: number }[] = [
    { id: 'overview', label: t('tabs.overview'), icon: Layers },
    {
      id: 'actionPack',
      label: t('tabs.actionPack'),
      icon: ClipboardList,
      badge: actionPackCount && actionPackCount > 0 ? actionPackCount : undefined,
    },
    { id: 'compare', label: t('tabs.compare'), icon: GitCompare },
    {
      id: 'verify',
      label: t('tabs.verify'),
      icon: ShieldCheck,
      badge: verifyIssuesCount,
    },
    { id: 'clauses', label: t('tabs.clauses'), icon: FileText },
    {
      id: 'attention',
      label: t('tabs.attention'),
      icon: ShieldAlert,
      badge: attentionCount > 0 ? attentionCount : undefined,
    },
    {
      id: 'dates',
      label: t('tabs.deadlines'),
      icon: Calendar,
      badge: datesCount > 0 ? datesCount : undefined,
    },
    {
      id: 'legalAid',
      label: t('tabs.legalAid'),
      icon: Scale,
    },
    { id: 'ask', label: t('tabs.ask'), icon: MessageSquare },
    { id: 'export', label: t('tabs.export'), icon: Download },
  ];

  const languageOptions = [
    { value: 'en', label: 'English' },
    { value: 'hi', label: 'हिन्दी' },
    { value: 'pa', label: 'ਪੰਜਾਬੀ' },
  ];

  return (
    <div className="h-full flex flex-col bg-paper/60 backdrop-blur-sm overflow-hidden">
      {/* Top Bar: Title & Output Language Selector */}
      <div className="px-6 py-3 border-b border-line bg-paper/80 flex flex-wrap items-center justify-between gap-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded bg-blue/10 flex items-center justify-center text-blue">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-navy">{t('results.headerTitle')}</h2>
            <div className="text-[11px] font-mono text-mute">
              {t('review.revisionLabel', { rev: revision })} · {t('results.serverProcessingNote')}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-mute font-medium">{t('upload.explainInLabel')}:</span>
          <SegmentedControl
            options={languageOptions}
            value={pendingLanguage || outputLanguage}
            onChange={(val) => changeOutputLanguage(val as OutputLanguage)}
          />
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6 relative">
        {/* State 1: Idle (Not yet started) */}
        {status === 'idle' && (
          <div className="max-w-md mx-auto py-12 text-center space-y-4">
            <GlassCard className="p-8 space-y-4">
              <div className="w-12 h-12 rounded-full bg-blue/10 text-blue flex items-center justify-center mx-auto">
                <Sparkles className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-navy">{t('results.readyTitle')}</h3>
                <p className="text-xs text-mute leading-relaxed">
                  {t('results.readyDescription', { lang: outputLanguage.toUpperCase() })}
                </p>
              </div>
              <Button
                variant="primary"
                size="md"
                className="w-full"
                onClick={() => startAnalysis()}
              >
                {t('results.analyseNow')}
              </Button>
              <p className="text-[11px] text-mute font-mono">
                {t('results.serverProcessingNote')}
              </p>
            </GlassCard>
          </div>
        )}

        {/* State 2: Queued or Running */}
        {isAnalyzing && (
          <div className="max-w-md mx-auto py-12 space-y-6">
            <GlassCard className="p-8 text-center space-y-5">
              <div className="flex items-center justify-center">
                <RotateCw className="w-8 h-8 text-blue animate-spin" />
              </div>

              <div className="space-y-1">
                <h3 className="text-base font-bold text-navy">
                  {status === 'queued'
                    ? t('review.submitting')
                    : t('results.processedSummary', {
                        completed: progress.completed_clauses,
                        total: progress.total_clauses,
                      })}
                </h3>
                <p className="text-xs text-mute font-mono">
                  {t('results.evaluatingCues')}
                </p>
              </div>

              {/* Real Segmented Progress Rail (No fake percentage) */}
              {progress.total_clauses > 0 && (
                <div className="space-y-2">
                  <div className="flex gap-1 h-2 rounded overflow-hidden bg-bg2 p-0.5 border border-line">
                    {Array.from({ length: progress.total_clauses }).map((_, idx) => {
                      const isComplete = idx < progress.completed_clauses;
                      const isCurrent = idx === progress.completed_clauses;
                      return (
                        <div
                          key={idx}
                          className={`flex-1 h-full rounded-xs transition-colors duration-200 ${
                            isComplete
                              ? 'bg-ok'
                              : isCurrent
                              ? 'bg-blue animate-pulse'
                              : 'bg-line/40'
                          }`}
                        />
                      );
                    })}
                  </div>
                  <div className="text-[11px] font-mono text-mute flex justify-between">
                    <span>{t('results.clauseItem', { num: 1 })}</span>
                    <span>
                      {t('results.processedSummary', {
                        completed: progress.completed_clauses,
                        total: progress.total_clauses,
                      })}
                      {progress.failed_clauses
                        ? ` · ${t('results.failedSummary', { count: progress.failed_clauses })}`
                        : ''}
                    </span>
                    <span>{t('results.clauseItem', { num: progress.total_clauses })}</span>
                  </div>
                </div>
              )}
            </GlassCard>
          </div>
        )}

        {isAnalyzing && analysisId && (
          <div className="px-6 pb-4">
            <Button
              variant="secondary"
              disabled={isCancelling}
              onClick={() => void cancelAnalysis()}
            >
              {t('upload.cancelAnalysis')}
            </Button>
          </div>
        )}

        {/* State 3: Error Banner */}
        {error && (
          <div className="mb-6">
            <Banner
              variant="error"
              title={t('results.analysisErrorTitle')}
              action={
                error.retryable
                  ? { label: t('results.retryAnalysisBtn'), onClick: retryAnalysis }
                  : undefined
              }
            >
              {error.message}
            </Banner>
          </div>
        )}

        {/* State 4: Complete or Needs Review */}
        {(status === 'complete' || status === 'needs_review') && result && (
          <div className="space-y-6">
            {/* Needs Review Amber Banner */}
            {status === 'needs_review' && (
              <Banner variant="warn" title={t('results.needsReviewBannerTitle')}>
                {t('results.needsReviewBannerBody')}
              </Banner>
            )}

            {/* Dimmed Loading Overlay for Language Switch */}
            {isDimmedLoading && (
              <div className="absolute inset-0 bg-paper/60 backdrop-blur-xs flex items-center justify-center z-20">
                <div className="p-4 rounded-lg bg-navy text-white shadow-card flex items-center gap-3 text-xs font-mono">
                  <RotateCw className="w-4 h-4 animate-spin text-cyan" />
                  <span>{t('results.loadingLanguage', { lang: pendingLanguage?.toUpperCase() || '' })}</span>
                </div>
              </div>
            )}

            {/* Navigation Tabs Bar */}
            <div className="flex items-center gap-1 border-b border-line pb-1 overflow-x-auto">
              {tabs.map((tab) => {
                const isSelected = activeTab === tab.id;
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className={`relative px-3.5 py-2 text-xs font-semibold rounded-t-md transition-colors flex items-center gap-1.5 shrink-0 cursor-pointer ${
                      isSelected
                        ? 'text-blue font-bold border-b-2 border-blue'
                        : 'text-mute hover:text-navy hover:bg-bg2/40'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{tab.label}</span>
                    {tab.badge !== undefined && (
                      <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded-full bg-blue/10 text-blue">
                        {tab.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Active Tab Panel */}
            <div className="pt-2">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeTab}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.15 }}
                >
                  {activeTab === 'overview' && (
                    <OverviewSummaryPanel
                      onNavigateEvidence={onNavigateEvidence}
                      onGoToClauses={() => setActiveTab('clauses')}
                    />
                  )}
                  {activeTab === 'actionPack' && (
                    <ActionPackPanel onNavigateEvidence={onNavigateEvidence} />
                  )}
                  {activeTab === 'compare' && (
                    <ComparePanel onNavigateEvidence={onNavigateEvidence} />
                  )}
                  {activeTab === 'verify' && (
                    <SourceVerificationPanel onNavigateEvidence={onNavigateEvidence} />
                  )}
                  {activeTab === 'clauses' && (
                    <ClauseExplanationList
                      onNavigateEvidence={onNavigateEvidence}
                    />
                  )}
                  {activeTab === 'attention' && (
                    <AttentionPanel
                      onNavigateEvidence={onNavigateEvidence}
                      onGoToClauses={() => setActiveTab('clauses')}
                    />
                  )}
                  {activeTab === 'dates' && (
                    <DeadlinePanel
                      onNavigateEvidence={onNavigateEvidence}
                    />
                  )}
                  {activeTab === 'legalAid' && (
                    <LegalAidDirectoryCard
                      variant="full"
                      legalAid={result?.legal_aid}
                    />
                  )}
                  {activeTab === 'ask' && (
                    <QuestionPanel onNavigateEvidence={onNavigateEvidence} />
                  )}
                  {activeTab === 'export' && <ResultExport />}
                </motion.div>
              </AnimatePresence>
            </div>

            {/* Persistent Legal Aid Footer Strip (hidden when on legalAid tab) */}
            {activeTab !== 'legalAid' && (
              <div className="pt-6 border-t border-line">
                <LegalAidDirectoryCard
                  variant="compact"
                  legalAid={result?.legal_aid}
                  onOpenFull={() => setActiveTab('legalAid')}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export const ResultsWorkspace: React.FC<ResultsWorkspaceProps> = (props) => {
  return (
    <ResultProvider
      documentId={props.documentId}
      sessionToken={props.sessionToken}
      revision={props.revision}
      initialOutputLanguage={props.outputLanguage}
      onDeleted={props.onDeleted}
    >
      <ResultsWorkspaceInner {...props} />
    </ResultProvider>
  );
};

export default ResultsWorkspace;
