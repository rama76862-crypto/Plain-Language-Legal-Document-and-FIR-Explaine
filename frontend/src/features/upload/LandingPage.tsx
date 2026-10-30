/**
 * LandingPage Component (P-01)
 * High-performance intake interface matching the preview design:
 * 1. Hero with Upload Console & exact 3D DocumentPrism stage
 * 2. Section #try: Interactive Clause-by-Clause Inspector preview
 * 3. Section #docs: Built for the judge's five documents with 3D TiltCards
 * 4. Section #privacy: 3D Spinning PrivacyCube
 * 5. Section #aid: Legal aid banner with 15100 helpline number
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { HealthStatusBar } from './HealthStatusBar';
import { UploadDropzone } from './UploadDropzone';
import { LanguageDocTypeSelector } from './LanguageDocTypeSelector';
import { DocumentPrism } from '../../design/scenes/DocumentPrism';
import { PrivacyCube } from '../../design/scenes/PrivacyCube';
import { ClauseInspectorPreview } from './ClauseInspectorPreview';
import { Button, GlassCard, TiltCard, Banner } from '../../design/primitives';
import { useSession } from '../../lib/session';
import { useT } from '../../lib/i18n';
import { createDocument } from '../../lib/api';
import { config } from '../../lib/config';
import type { InputLanguage, OutputLanguage, InputDocumentType, HealthResponse } from '../../lib/types';
import { ExternalLink } from 'lucide-react';

export const LandingPage: React.FC = () => {
  const { startSession } = useSession();
  const { t } = useT();
  const navigate = useNavigate();

  // Form State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [inputLang, setInputLang] = useState<InputLanguage>('auto');
  const [outputLang, setOutputLang] = useState<OutputLanguage>('en');
  const [docType, setDocType] = useState<InputDocumentType>('auto');

  // Submittal & Telemetry State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isHealthReady, setIsHealthReady] = useState(true);
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);

  // IntersectionObserver for .reveal elements matching HTML preview behavior
  useEffect(() => {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('in');
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    document.querySelectorAll('.reveal').forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  const handleHealthChange = (isHealthy: boolean, data: HealthResponse | null) => {
    setIsHealthReady(isHealthy);
    setHealthData(data);
  };

  const handleExtractSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !isHealthReady) return;

    setIsSubmitting(true);
    setUploadError(null);

    // If fixtures mode enabled in development
    if (config.useFixtures) {
      setTimeout(() => {
        startSession({
          documentId: 'doc_fixture_rent_01',
          sessionToken: 'opaque_fixture_token',
          revision: 1,
          filename: selectedFile.name,
          inputLanguage: inputLang === 'auto' ? 'en' : inputLang,
          outputLanguage: outputLang,
          documentType: docType === 'auto' ? 'agreement' : docType,
        });
        setIsSubmitting(false);
        navigate('/workspace?step=extracting');
      }, 600);
      return;
    }

    try {
      const res = await createDocument(selectedFile, inputLang, docType);
      startSession({
        documentId: res.document_id,
        sessionToken: res.session_token,
        revision: res.revision,
        filename: selectedFile.name,
        inputLanguage: inputLang === 'auto' ? 'en' : inputLang,
        outputLanguage: outputLang,
        documentType: docType === 'auto' ? 'agreement' : docType,
      });
      navigate('/workspace?step=extracting');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed. Please check network and retry.';
      setUploadError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="w-full">
      {/* 1. HERO SECTION */}
      <section className="relative pt-4 pb-16 px-4 sm:px-6 max-w-6xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center min-h-[calc(100vh-140px)]">
          {/* Left Column: Headlines & Upload Console */}
          <div className="lg:col-span-7 space-y-6 z-10">
            {/* Eyebrow Chip */}
            <div className="eyebrow">
              <b />
              <span>{t('landing.heroTag')}</span>
            </div>

            {/* H1 Heading with gradient shimmer */}
            <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-extrabold text-navy tracking-tight leading-[1.12]">
              Legal papers,{' '}
              <span className="bg-gradient-to-r from-blue via-cyan to-blue bg-clip-text text-transparent bg-[length:200%_auto] animate-shimmer">
                in plain language
              </span>
            </h1>

            {/* Sub copy */}
            <p className="text-base sm:text-lg text-mute max-w-xl leading-relaxed">
              {t('landing.heroSub')}
            </p>

            {/* CTA action buttons */}
            <div className="cta flex gap-3 flex-wrap">
              <a
                href="#upload-console"
                className="btn p btn-sweep font-bold"
              >
                Upload a document
              </a>
              <a
                href="#aid"
                className="btn s font-bold"
              >
                Free legal aid
              </a>
            </div>

            {/* Trust Assurance Row */}
            <div className="trust">
              <span>Punjabi · Hindi · English</span>
              <span>Deleted when you leave</span>
              <span>DLSA / NALSA links</span>
            </div>

            {/* UPLOAD CONSOLE (Glass Card) */}
            <div id="upload-console" className="pt-2">
              <GlassCard className="p-6 rounded-2xl shadow-card border border-line bg-paper/85 backdrop-blur-md space-y-5">
                <form onSubmit={handleExtractSubmit} className="space-y-4">
                  {/* Dropzone */}
                  <UploadDropzone
                    selectedFile={selectedFile}
                    onFileSelect={setSelectedFile}
                    disabled={isSubmitting || !isHealthReady}
                  />

                  {/* Independent Language & DocType Controls */}
                  <LanguageDocTypeSelector
                    inputLanguage={inputLang}
                    outputLanguage={outputLang}
                    documentType={docType}
                    healthData={healthData}
                    onChangeInputLanguage={setInputLang}
                    onChangeOutputLanguage={setOutputLang}
                    onChangeDocumentType={setDocType}
                    disabled={isSubmitting}
                  />

                  {/* Upload Error Banner */}
                  {uploadError && (
                    <Banner
                      variant="error"
                      title="Upload Failed"
                      action={{ label: 'Retry', onClick: () => setUploadError(null) }}
                    >
                      {uploadError}
                    </Banner>
                  )}

                  {/* Primary Extract Action Button */}
                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    className="w-full text-base font-bold shadow-pop btn-sweep"
                    disabled={!selectedFile || !isHealthReady || isSubmitting}
                    isLoading={isSubmitting}
                  >
                    {isSubmitting ? t('upload.extractingButton') : t('upload.extractButton')}
                  </Button>

                  {/* Consent & Privacy Notice Line */}
                  <p className="text-[11px] text-mute leading-normal text-center pt-1">
                    {t('disclaimers.consent')}
                  </p>
                </form>
              </GlassCard>
            </div>

            {/* Local Engine Health Telemetry */}
            <HealthStatusBar onHealthStatusChange={handleHealthChange} />
          </div>

          {/* Right Column: Exact 3D DocumentPrism Scene */}
          <div className="lg:col-span-5 relative hidden lg:flex items-center justify-center">
            <DocumentPrism />
          </div>
        </div>
      </section>

      {/* 2. CLAUSE INSPECTOR PREVIEW SECTION (#try) */}
      <ClauseInspectorPreview />

      {/* 3. CITIZEN DOCUMENT TYPES (#docs) */}
      <section id="docs" className="py-16 px-4 sm:px-6 max-w-6xl mx-auto space-y-8">
        <div className="space-y-2">
          <h2 className="reveal text-2xl sm:text-3xl font-extrabold text-navy tracking-tight">
            Built for the judge’s five documents
          </h2>
          <p className="lead reveal text-mute text-base max-w-2xl">
            Each document type has its own view and checks. Concerns are labelled “potential” —
            never a safety score.
          </p>
        </div>

        <div className="tilt-grid">
          <TiltCard
            className="reveal"
            index="01"
            icon="🏠"
            title="Rent agreement"
            description="Penalties, lock-in, auto-renewal"
          />
          <TiltCard
            className="reveal"
            index="02"
            icon="💰"
            title="Loan paper"
            description="Interest, default, waived rights"
          />
          <TiltCard
            className="reveal"
            index="03"
            icon="🗺"
            title="Land document"
            description="Ownership, encumbrance, dates"
          />
          <TiltCard
            className="reveal"
            index="04"
            icon="📨"
            title="Court notice"
            description="Hearing dates, action demanded"
          />
          <TiltCard
            className="reveal"
            index="05"
            icon="🚔"
            title="FIR copy"
            description="Allegations recorded, who said what"
          />
        </div>
      </section>

      {/* 4. PRIVACY & TEMPORARY PROCESSING (#privacy) */}
      <section id="privacy" className="py-16 px-4 sm:px-6 max-w-6xl mx-auto space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
          <div className="reveal space-y-4">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-navy tracking-tight">
              Your document never leaves the moment
            </h2>
            <p className="text-mute text-base leading-relaxed">
              Processed temporarily, held in memory only, wiped with one tap. No accounts, no
              tracking, no stored copies without your consent.
            </p>
            <div className="pt-2">
              <a href="#upload-console" className="btn p btn-sweep font-bold inline-block">
                See it work
              </a>
            </div>
          </div>

          <div className="reveal flex items-center justify-center">
            <PrivacyCube />
          </div>
        </div>
      </section>

      {/* 5. LEGAL AID SECTION (#aid) */}
      <section id="aid" className="py-16 px-4 sm:px-6 max-w-6xl mx-auto pb-20">
        <div className="aid reveal">
          <div className="space-y-2">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Need a lawyer you can’t afford?
            </h2>
            <p className="text-sm text-white/90 leading-relaxed max-w-lg">
              District Legal Services Authorities (DLSA) and NALSA offer free legal aid to eligible
              people. Find your nearest DLSA from here.
            </p>
            <div className="pt-2">
              <a
                href="https://nalsa.gov.in/legal-aid/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-mono font-bold text-white hover:underline"
              >
                <span>Visit Official NALSA Portal</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          <div className="num">
            15100
            <small>NALSA helpline</small>
          </div>
        </div>
      </section>
    </main>
  );
};
export default LandingPage;
