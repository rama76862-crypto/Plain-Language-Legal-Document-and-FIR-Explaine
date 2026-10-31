/**
 * LandingPage Component (P-01)
 * High-performance intake interface matching the preview design:
 * 3. Section #docs: Built for the judge's five documents with 3D TiltCards
 * 5. Section #aid: Legal aid banner with 15100 helpline number
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { HealthStatusBar } from './HealthStatusBar';
import { UploadDropzone } from './UploadDropzone';
import { LanguageDocTypeSelector } from './LanguageDocTypeSelector';
import { Button, GlassCard, TiltCard, Banner } from '../../design/primitives';
import { useSession } from '../../lib/session';
import { useT } from '../../lib/i18n';
import { createDocument, getCapabilities } from '../../lib/api';
import type { InputLanguage, OutputLanguage, InputDocumentType, HealthResponse } from '../../lib/types';
import { ExternalLink } from 'lucide-react';
import { DocumentPrism } from '../../design/scenes/DocumentPrism';
import { PrivacyCube } from '../../design/scenes/PrivacyCube';
import { DotGridField } from '../../design/DotGridField';

export const LandingPage: React.FC = () => {
  const { startSession } = useSession();
  const { t } = useT();
  const navigate = useNavigate();

  // Form State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [inputLang, setInputLang] = useState<InputLanguage>('auto');
  const [outputLang, setOutputLang] = useState<OutputLanguage>('en');
  const [docType, setDocType] = useState<InputDocumentType>('auto');
  const [processingConsent, setProcessingConsent] = useState(false);
  const [hostedMode,setHostedMode]=useState(false);
  const [externalConsent,setExternalConsent]=useState(false);
  const [limits, setLimits] = useState({ max_upload_bytes: 25 * 1024 * 1024, max_pdf_pages: 50 });
  useEffect(() => {
    const controller = new AbortController();
    getCapabilities(controller.signal)
      .then((value) => {
        if (value?.limits) setLimits(value.limits);
        setHostedMode(value?.processing?.external_ai_inference === true);
      })
      .catch(() => {});
    return () => controller.abort();
  }, []);

  // Submittal & Telemetry State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
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

  const handleHealthChange = useCallback((_isHealthy: boolean, data: HealthResponse | null) => {
    setHealthData(data);
  }, []);

  const handleExtractSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !healthData || !processingConsent || (hostedMode&&!externalConsent)) return;

    setIsSubmitting(true);
    setUploadError(null);

    try {
      if (!processingConsent) throw new Error('Consent to temporary processing is required.');
      const res = await createDocument(selectedFile, inputLang, docType,undefined,externalConsent);
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
              {(() => {
                const title = t('landing.heroTitle');
                const commaIdx = title.indexOf(',');
                if (commaIdx !== -1) {
                  return (
                    <>
                      {title.slice(0, commaIdx + 1)}{' '}
                      <span className="bg-gradient-to-r from-blue via-cyan to-blue bg-clip-text text-transparent bg-[length:200%_auto] animate-shimmer">
                        {title.slice(commaIdx + 1).trim()}
                      </span>
                    </>
                  );
                }
                return title;
              })()}
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
                {t('landing.uploadDocBtn')}
              </a>
              <a
                href="#aid"
                className="btn s font-bold"
              >
                {t('landing.freeLegalAidBtn')}
              </a>
            </div>

            {/* Trust Assurance Row */}
            <div className="trust">
              <span>{t('landing.trust1')}</span>
              <span>{t('landing.trust2')}</span>
              <span>{t('landing.trust3')}</span>
            </div>

            {/* UPLOAD CONSOLE (Glass Card) */}
            <div id="upload-console" className="pt-2">
              <GlassCard className="p-6 rounded-2xl shadow-card border border-line bg-paper/85 backdrop-blur-md space-y-5">
                <form onSubmit={handleExtractSubmit} className="space-y-4">
                  {/* Dropzone */}
                  <UploadDropzone
                    selectedFile={selectedFile}
                    onFileSelect={setSelectedFile}
                    disabled={isSubmitting}
                    maxBytes={limits.max_upload_bytes}
                    maxPages={limits.max_pdf_pages}
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

                  {/* Explicit Reassuring Consent Box (Placed before primary submit button) */}
                  <div className="p-3.5 rounded-xl bg-blue/5 border border-blue/20 space-y-2.5">
                    <label className="flex items-start gap-2.5 text-xs text-navy font-semibold leading-relaxed cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={processingConsent}
                        onChange={(e) => setProcessingConsent(e.target.checked)}
                        className="mt-0.5 rounded text-blue focus:ring-blue border-line"
                      />
                      <span>{t('upload.processingConsent')}</span>
                    </label>

                    {hostedMode && (
                      <label className="flex items-start gap-2.5 text-xs text-navy font-semibold leading-relaxed cursor-pointer select-none pt-2 border-t border-blue/15">
                        <input
                          type="checkbox"
                          checked={externalConsent}
                          onChange={(e) => setExternalConsent(e.target.checked)}
                          className="mt-0.5 rounded text-blue focus:ring-blue border-line"
                        />
                        <span>{t('upload.hostedConsent')}</span>
                      </label>
                    )}
                  </div>

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
                    disabled={!selectedFile || !healthData || isSubmitting || !processingConsent || (hostedMode&&!externalConsent)}
                    isLoading={isSubmitting}
                  >
                    {isSubmitting
                      ? t('upload.extractingButton')
                      : !healthData && selectedFile
                      ? t('landing.connectingEngine')
                      : t('upload.extractButton')}
                  </Button>

                  <div className="text-center space-y-1">
                    <p className="text-[11px] font-mono text-mute">
                      {t('upload.limitsDynamic', { pages: limits.max_pdf_pages, mb: Math.floor(limits.max_upload_bytes / 1024 / 1024) })}
                    </p>
                    <p className="text-[11px] text-mute leading-normal">
                      {t('disclaimers.consent')}
                    </p>
                  </div>
                </form>
              </GlassCard>
            </div>

            {/* Local Engine Health Telemetry */}
            <HealthStatusBar onHealthStatusChange={handleHealthChange} />
          </div>

          {/* Right Column: 3D Document Prism with DotGrid background */}
          <div className="lg:col-span-5 relative flex items-center justify-center">
            <div className="absolute inset-0 pointer-events-none opacity-30 overflow-hidden rounded-2xl">
              <DotGridField performanceTier="medium" glow={true} />
            </div>
            <DocumentPrism />
          </div>
        </div>
      </section>

      {/* 2. CITIZEN DOCUMENT TYPES (#docs) */}
      <section id="docs" className="py-16 px-4 sm:px-6 max-w-6xl mx-auto space-y-8">
        <div className="space-y-2">
          <h2 className="reveal text-2xl sm:text-3xl font-extrabold text-navy tracking-tight">
            {t('landing.docTypesTitle')}
          </h2>
          <p className="lead reveal text-mute text-base max-w-2xl">
            {t('landing.docTypesSub')}
          </p>
        </div>

        <div className="tilt-grid">
          <TiltCard
            className="reveal"
            index="01"
            icon="🏠"
            title={t('docTypes.agreement')}
            description={t('landing.agreementDesc')}
          />
          <TiltCard
            className="reveal"
            index="02"
            icon="💰"
            title={t('landing.loanPaper')}
            description={t('landing.loanPaperDesc')}
          />
          <TiltCard
            className="reveal"
            index="03"
            icon="🗺"
            title={t('landing.landDoc')}
            description={t('landing.landDocDesc')}
          />
          <TiltCard
            className="reveal"
            index="04"
            icon="📨"
            title={t('docTypes.notice')}
            description={t('landing.noticeDesc')}
          />
          <TiltCard
            className="reveal"
            index="05"
            icon="🚔"
            title={t('docTypes.fir')}
            description={t('landing.firDesc')}
          />
        </div>
      </section>

      {/* 4. PRIVACY & TEMPORARY PROCESSING (#privacy) */}
      <section id="privacy" className="py-16 px-4 sm:px-6 max-w-6xl mx-auto space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
          <div className="reveal space-y-4">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-navy tracking-tight">
              {t('landing.privacyTitle')}
            </h2>
            <p className="text-mute text-base leading-relaxed">
              {t('landing.privacySub')}
            </p>
            <div className="pt-2">
              <a href="#upload-console" className="btn p btn-sweep font-bold inline-block">
                {t('landing.seeItWork')}
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
              {t('landing.legalAidTitle')}
            </h2>
            <p className="text-sm text-white/90 leading-relaxed max-w-lg">
              {t('landing.legalAidSub')}
            </p>
            <div className="pt-2">
              <a
                href="https://nalsa.gov.in/legal-aid/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-mono font-bold text-white hover:underline"
              >
                <span>{t('landing.visitNalsa')}</span>
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
