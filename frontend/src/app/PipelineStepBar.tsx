/**
 * PipelineStepBar Component
 * Sticky under header on /workspace route.
 * Steps: Upload · Extract · Review · Explain · Ask
 * Gliding active pill indicator driven by real session state.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { useSession } from '../lib/session';
import { useT } from '../lib/i18n';

interface PipelineStepBarProps {
  currentStep: 'extracting' | 'review' | 'results';
  onNavigateStep?: (step: 'review' | 'results') => void;
}

export const PipelineStepBar: React.FC<PipelineStepBarProps> = ({
  currentStep,
  onNavigateStep,
}) => {
  const { t } = useT();
  const { documentStatus, reviewConfirmed } = useSession();

  const steps = [
    { id: 'upload', label: t('pipeline.step1'), status: 'done' as const },
    {
      id: 'extract',
      label: t('pipeline.step2'),
      status: currentStep === 'extracting' ? ('active' as const) : ('done' as const),
    },
    {
      id: 'review',
      label: t('pipeline.step3'),
      status:
        currentStep === 'review'
          ? ('active' as const)
          : reviewConfirmed
          ? ('done' as const)
          : ('ready' as const),
    },
    {
      id: 'results',
      label: t('pipeline.step4'),
      status:
        currentStep === 'results' && documentStatus === 'complete'
          ? ('done' as const)
          : currentStep === 'results'
          ? ('active' as const)
          : ('ready' as const),
    },
    {
      id: 'qa',
      label: t('pipeline.step5'),
      status: currentStep === 'results' ? ('ready' as const) : ('ready' as const),
    },
  ];

  return (
    <div className="sticky top-16 z-30 w-full bg-paper/85 backdrop-blur-md border-b border-line shadow-sm py-2.5 px-6">
      <div className="max-w-5xl mx-auto flex items-center justify-between">
        <nav aria-label="Analysis Pipeline Progress" className="w-full">
          <ol className="flex items-center justify-between gap-1 sm:gap-4">
            {steps.map((st) => {
              const isActive = st.status === 'active';
              const isDone = st.status === 'done';
              const isClickable =
                (st.id === 'review' && reviewConfirmed && currentStep === 'results') ||
                (st.id === 'results' && reviewConfirmed && currentStep === 'review');

              return (
                <li key={st.id} className="relative flex-1 flex items-center justify-center">
                  <button
                    type="button"
                    disabled={!isClickable}
                    onClick={() => {
                      if (st.id === 'review') onNavigateStep?.('review');
                      if (st.id === 'results') onNavigateStep?.('results');
                    }}
                    className={`relative px-2 sm:px-3 py-1.5 rounded-pill text-xs font-semibold flex items-center gap-1 sm:gap-1.5 transition-all select-none ${
                      isActive
                        ? 'text-white font-bold'
                        : isDone
                        ? 'text-navy hover:text-blue cursor-pointer'
                        : 'text-mute opacity-60 cursor-not-allowed'
                    }`}
                  >
                    {isActive && (
                      <motion.div
                        layoutId="active-pipeline-pill"
                        className="absolute inset-0 bg-navy rounded-pill shadow-sm"
                        transition={{ type: 'spring', bounce: 0.2, duration: 0.35 }}
                      />
                    )}
                    <span className="relative z-10 flex items-center gap-1 sm:gap-1.5 min-w-0">
                      <span
                        className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-mono shrink-0 ${
                          isActive
                            ? 'bg-cyan text-navy font-bold'
                            : isDone
                            ? 'bg-ok text-white'
                            : 'bg-line text-mute'
                        }`}
                      >
                        {isDone ? '✓' : ''}
                      </span>
                      <span className="truncate max-w-[62px] sm:max-w-none">{st.label}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        </nav>
      </div>
    </div>
  );
};
