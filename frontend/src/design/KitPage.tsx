/**
 * Dev-Only Design Kit Showcase Page (/kit)
 * Displays all UI primitives, backgrounds, and 3D scenes.
 */

import React, { useState } from 'react';
import {
  Button,
  GlassCard,
  TiltCard,
  StatusPill,
  MonoLabel,
  Kbd,
  Tooltip,
  Modal,
  Tabs,
  SegmentedControl,
  Select,
  Banner,
  ProgressSteps,
  Skeleton,
  EmptyState,
  Accordion,
  NumberTicker,
  MarqueeBand,
  CopyButton,
  useToast,
} from './primitives';
import { LiveBackground } from './LiveBackground';
import { DotGridField } from './DotGridField';
import { DocumentPrism } from './scenes/DocumentPrism';
import { PrivacyCube } from './scenes/PrivacyCube';
import { PipelineStage } from './scenes/PipelineStage';
import { CoverageRing } from './scenes/CoverageRing';
import { ShredDissolve } from './scenes/ShredDissolve';
import { Reveal } from './motion';

export const KitPage: React.FC = () => {
  const { showToast } = useToast();
  const [modalOpen, setModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('one');
  const [activeSeg, setActiveSeg] = useState('en');
  const [selectVal, setSelectVal] = useState('auto');
  const [activeStep, setActiveStep] = useState(1);
  const [showShred, setShowShred] = useState(false);

  return (
    <div className="relative min-h-screen py-12 px-6 max-w-6xl mx-auto space-y-12">
      <LiveBackground />

      <header className="border-b border-line pb-6">
        <MonoLabel>DEV DESIGN SYSTEM PREVIEW</MonoLabel>
        <h1 className="text-3xl font-extrabold text-navy tracking-tight mt-1">
          NyayaSarathi UI &amp; 3D Kit
        </h1>
        <p className="text-sm text-mute mt-1">
          Light mode, high-contrast, fully keyboard accessible.
        </p>
      </header>

      {/* Marquee showcase */}
      <Reveal>
        <section className="space-y-3">
          <MonoLabel>01. MARQUEE BAND</MonoLabel>
          <MarqueeBand text="Information only · Not legal advice · Clause by clause · Evidence you can check · Deleted on request" />
        </section>
      </Reveal>

      {/* Buttons & Pills */}
      <section className="space-y-4">
        <MonoLabel>02. BUTTONS &amp; STATUS PILLS</MonoLabel>
        <div className="flex flex-wrap gap-3 items-center">
          <Button variant="primary" onClick={() => showToast('Primary clicked!', 'success')}>
            Primary with Shimmer
          </Button>
          <Button variant="secondary" onClick={() => showToast('Secondary clicked!')}>
            Secondary
          </Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger-outline">Danger Outline</Button>
          <Button variant="caution-outline">Caution Outline</Button>
          <Button variant="primary" isLoading>
            Loading Button
          </Button>
        </div>

        <div className="flex flex-wrap gap-2 items-center pt-2">
          <StatusPill variant="concern">Potential concern: Auto-renewal</StatusPill>
          <StatusPill variant="caution">Needs review</StatusPill>
          <StatusPill variant="deadline">15 days after receipt</StatusPill>
          <StatusPill variant="ok">Supported by evidence</StatusPill>
          <StatusPill variant="translation">Translation-assisted</StatusPill>
          <StatusPill variant="fixture">DEVELOPMENT FIXTURE</StatusPill>
        </div>
      </section>

      {/* Micro-labels, Kbd, Tooltip, Copy */}
      <section className="space-y-4">
        <MonoLabel>03. METADATA PRIMITIVES</MonoLabel>
        <div className="flex flex-wrap gap-4 items-center glass-card p-4 rounded-lg">
          <div className="flex items-center gap-2">
            <span className="text-sm">Shortcut:</span>
            <Kbd>Cmd + Enter</Kbd>
          </div>
          <Tooltip content="Reset on activity">
            <span className="text-sm underline cursor-help text-blue">Hover me for tooltip</span>
          </Tooltip>
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm">Copy clause ID:</span>
            <CopyButton text="c3" />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-mute">Counter:</span>
            <NumberTicker value={42} className="text-xl text-blue" />
          </div>
        </div>
      </section>

      {/* Cards & Tilts */}
      <section className="space-y-4">
        <MonoLabel>04. CARDS &amp; INTERACTIVE TILT</MonoLabel>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <GlassCard>
            <h3 className="font-bold text-navy mb-2">Standard GlassCard</h3>
            <p className="text-sm text-mute">
              Backdrop blurred paper card with subtle 1px border.
            </p>
          </GlassCard>
          <TiltCard>
            <h3 className="font-bold text-navy mb-2">Interactive TiltCard</h3>
            <p className="text-sm text-mute">
              Gentle pointer-following 3D perspective with radial glare.
            </p>
          </TiltCard>
        </div>
      </section>

      {/* Tabs & Controls */}
      <section className="space-y-4">
        <MonoLabel>05. TABS, SELECT &amp; SEGMENTED CONTROLS</MonoLabel>
        <div className="flex flex-col gap-4">
          <div>
            <Tabs
              tabs={[
                { id: 'one', label: 'Overview' },
                { id: 'two', label: 'Clauses', badge: 7 },
                { id: 'three', label: 'Attention', badge: 3 },
                { id: 'four', label: 'Dates' },
              ]}
              activeId={activeTab}
              onChange={setActiveTab}
            />
          </div>
          <div className="flex flex-wrap gap-4 items-center">
            <SegmentedControl
              options={[
                { value: 'en', label: 'EN' },
                { value: 'hi', label: 'हिन्दी' },
                { value: 'pa', label: 'ਪੰਜਾਬੀ' },
              ]}
              value={activeSeg}
              onChange={setActiveSeg}
            />
            <div className="w-64">
              <Select
                value={selectVal}
                onChange={setSelectVal}
                options={[
                  { value: 'auto', label: 'Auto-detect' },
                  { value: 'agreement', label: 'Rental Agreement' },
                  { value: 'fir', label: 'Police FIR' },
                ]}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Pipeline Steps & Banners */}
      <section className="space-y-4">
        <MonoLabel>06. PROGRESS STEPS &amp; BANNERS</MonoLabel>
        <GlassCard className="p-4">
          <ProgressSteps
            steps={[
              { id: '1', label: 'Upload', status: 'done' },
              { id: '2', label: 'Read & OCR', status: 'active' },
              { id: '3', label: 'Review', status: 'ready' },
              { id: '4', label: 'Explain', status: 'ready' },
              { id: '5', label: 'Ask', status: 'ready' },
            ]}
          />
        </GlassCard>

        <div className="space-y-2">
          <Banner variant="info" title="Information notice">
            This is general information to help you understand a document.
          </Banner>
          <Banner variant="warn" title="Low OCR scan quality">
            Please review extracted text carefully against the original image.
          </Banner>
          <Banner
            variant="error"
            title="Extraction failed"
            action={{ label: 'Retry with clear file', onClick: () => showToast('Retrying...', 'info') }}
          >
            Zero selectable text found in uploaded file.
          </Banner>
        </div>
      </section>

      {/* 3D Scenes Showcase */}
      <section className="space-y-6">
        <MonoLabel>07. 3D SCENES &amp; FALLBACKS</MonoLabel>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <GlassCard className="flex flex-col items-center">
            <h4 className="font-mono text-xs text-mute uppercase mb-2">Scene 1: DocumentPrism (Hero)</h4>
            <DocumentPrism />
          </GlassCard>

          <GlassCard className="flex flex-col items-center">
            <h4 className="font-mono text-xs text-mute uppercase mb-2">Scene 2: PrivacyCube</h4>
            <PrivacyCube />
          </GlassCard>
        </div>

        <GlassCard className="space-y-4">
          <h4 className="font-mono text-xs text-mute uppercase">Scene 3: PipelineStage (3D Rail)</h4>
          <PipelineStage activeStep={activeStep} onStepSelect={setActiveStep} />
        </GlassCard>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <GlassCard className="flex flex-col items-center justify-center">
            <h4 className="font-mono text-xs text-mute uppercase mb-2">Scene 4: CoverageRing (Coverage Only)</h4>
            <CoverageRing analysed={7} total={8} />
          </GlassCard>

          <GlassCard className="flex flex-col items-center justify-center space-y-4">
            <h4 className="font-mono text-xs text-mute uppercase mb-2">Scene 5: Interactive DotGridField</h4>
            <div className="relative w-full h-44 border border-line rounded-md overflow-hidden bg-white/50">
              <DotGridField />
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowShred(true)}
            >
              Test Scene 6: ShredDissolve
            </Button>
          </GlassCard>
        </div>
      </section>

      {/* Accordion, Skeleton, EmptyState & Modal */}
      <section className="space-y-4 pb-12">
        <MonoLabel>08. ACCORDION, EMPTY STATE &amp; MODAL</MonoLabel>
        <Accordion title="Technical Details (Model & Rules Provenance)">
          <div className="space-y-1 font-mono text-xs text-mute">
            <div>Classifier: baseline-unfair-tos-v1</div>
            <div>Generator: local-qwen3-4b-instruct-q4</div>
            <div>Rules Engine: v1.0.2</div>
          </div>
        </Accordion>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-28 w-full" />
          <EmptyState
            title="No attention cues detected"
            description="All configured checks passed. Review all clauses normally."
            action={
              <Button size="sm" variant="secondary" onClick={() => setModalOpen(true)}>
                Open Modal Test
              </Button>
            }
          />
        </div>

        <Modal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          title="Confirm Document Review"
        >
          <div className="space-y-4 text-sm text-ink">
            <p>
              Please verify that all clauses were extracted accurately before proceeding to AI analysis.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  setModalOpen(false);
                  showToast('Review confirmed!', 'success');
                }}
              >
                Confirm &amp; Proceed
              </Button>
            </div>
          </div>
        </Modal>

        {showShred && <ShredDissolve onDone={() => setShowShred(false)} />}
      </section>
    </div>
  );
};
export default KitPage;
