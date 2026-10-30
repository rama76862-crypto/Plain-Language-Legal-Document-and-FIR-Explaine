/**
 * AppShell Component (C-01)
 * Top-level application frame containing:
 * - LiveBackground and BootIntro sequence
 * - Glass header with language switcher, session inactivity timer, and delete button
 * - Assurance MarqueeBand
 * - InactivityModal & DeleteSessionDialog
 * - Persistent disclaimer footer & NALSA link
 * - Development fixture badge
 */

import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LiveBackground } from '../design/LiveBackground';
import { BootIntro } from '../design/scenes/BootIntro';
import { Button, Tooltip, MarqueeBand } from '../design/primitives';
import { InactivityModal } from './InactivityModal';
import { DeleteSessionDialog } from './DeleteSessionDialog';
import { useSession } from '../lib/session';
import { useT } from '../lib/i18n';
import { config } from '../lib/config';
import { isWebGLAvailable } from '../design/webglUtils';
import { ShieldCheck, Clock, ExternalLink } from 'lucide-react';

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { documentId, inactivityRemainingSeconds, serverExpiresAt } = useSession();
  const { t, uiLanguage, setUiLanguage } = useT();
  const location = useLocation();

  const [bootDone, setBootDone] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [bootReady, setBootReady] = useState({
    fonts: true,
    health: true,
    webgl: isWebGLAvailable(),
  });

  useEffect(() => {
    // Fonts readiness
    if (document.fonts) {
      document.fonts.ready.then(() => {
        setBootReady((prev) => ({ ...prev, fonts: true }));
      });
    }
  }, []);

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const isLanding = location.pathname === '/';

  return (
    <div className="relative min-h-screen flex flex-col font-sans bg-bg text-ink overflow-x-hidden selection:bg-blue/20">
      {/* Global Background */}
      <LiveBackground />

      {/* Boot sequence for initial load */}
      {!bootDone && (
        <BootIntro onDone={() => setBootDone(true)} ready={bootReady} />
      )}

      {/* Development Fixture Badge */}
      {config.useFixtures && (
        <aside
          role="status"
          aria-label="Development mock fixture active"
          className="fixed top-2 left-1/2 -translate-x-1/2 z-50 px-3 py-1 bg-caution-bg text-caution-ink border border-caution rounded-pill text-xs font-mono font-bold shadow-md pointer-events-none select-none tracking-wide flex items-center gap-1.5"
        >
          <span>⚠</span>
          <span>DEVELOPMENT FIXTURE MODE</span>
        </aside>
      )}

      {/* Floating Glass Header */}
      <header className="sticky top-0 z-40 my-3 mx-auto w-[min(1120px,94%)] flex items-center justify-between gap-3 px-4 py-2.5 rounded-[18px] bg-[rgba(255,255,255,0.74)] backdrop-blur-md border border-[rgba(14,26,61,0.1)] shadow-[0_18px_50px_-18px_rgba(20,48,107,0.35)]">
        {/* Logo / Brand */}
        <Link
          to="/"
          className="flex items-center gap-2.5 text-navy hover:opacity-95 transition-opacity focus:outline-hidden"
        >
          <i className="w-[34px] h-[34px] rounded-[10px] grid place-items-center bg-gradient-to-br from-navy to-blue text-white not-italic shadow-[0_6px_16px_-4px_var(--blue)] font-bold text-sm">
            ⚖
          </i>
          <div className="flex flex-col">
            <span className="font-extrabold text-[15px] tracking-tight leading-none text-navy block">
              NyayaSarathi
            </span>
            <small className="block font-semibold text-[11px] text-mute -mt-0.5">
              ਨਿਆਂ ਸਾਰਥੀ · न्याय सारथी
            </small>
          </div>
        </Link>

        {/* Landing Navigation Links */}
        {isLanding && (
          <nav aria-label="Quick links" className="hidden md:flex items-center gap-1 text-sm font-semibold text-mute">
            <a href="#try" className="px-2.5 py-1 hover:text-blue transition-colors">
              Inspector
            </a>
            <a href="#docs" className="px-2.5 py-1 hover:text-blue transition-colors">
              Benchmark
            </a>
            <a href="#privacy" className="px-2.5 py-1 hover:text-blue transition-colors">
              Privacy
            </a>
            <a href="#aid" className="px-2.5 py-1 hover:text-blue transition-colors">
              Legal aid
            </a>
          </nav>
        )}

        {/* Right Header Actions */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Local Processing Status Chip */}
          <div className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill bg-ok/10 border border-ok/20 text-ok-ink text-xs font-semibold">
            <ShieldCheck className="w-3.5 h-3.5 text-ok" aria-hidden="true" />
            <span>{t('nav.localProcessing')}</span>
          </div>

          {/* Inactivity Timer Chip (only when session exists) */}
          {documentId && (
            <Tooltip
              content={
                serverExpiresAt
                  ? t('nav.serverRetentionTooltip')
                  : t('nav.inactivityTooltip')
              }
            >
              <div
                tabIndex={0}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-pill bg-paper border border-line text-xs font-mono text-mute shadow-sm"
                aria-label={`Session timer: ${formatTimer(inactivityRemainingSeconds)} remaining`}
              >
                <Clock className="w-3.5 h-3.5 text-blue" aria-hidden="true" />
                <span className="font-bold text-navy">
                  {formatTimer(inactivityRemainingSeconds)}
                </span>
              </div>
            </Tooltip>
          )}

          {/* UI Language Switcher */}
          <div className="lang">
            <button
              type="button"
              className={uiLanguage === 'en' ? 'on' : ''}
              onClick={() => setUiLanguage('en')}
            >
              EN
            </button>
            <button
              type="button"
              className={uiLanguage === 'hi' ? 'on' : ''}
              onClick={() => setUiLanguage('hi')}
            >
              हिं
            </button>
            <button
              type="button"
              className={uiLanguage === 'pa' ? 'on' : ''}
              onClick={() => setUiLanguage('pa')}
            >
              ਪੰ
            </button>
          </div>

          {/* Delete Session Button (only when session exists) */}
          {documentId && (
            <Button
              variant="danger-outline"
              size="sm"
              onClick={() => setDeleteOpen(true)}
            >
              {t('nav.deleteSession')}
            </Button>
          )}
        </div>
      </header>

      {/* Assurance Marquee Band */}
      <MarqueeBand text={t('landing.marquee')} />

      {/* Main Content View */}
      <div className="flex-1 flex flex-col">{children}</div>

      {/* Global Inactivity Expiry Watchdog */}
      <InactivityModal />

      {/* Global Delete Confirmation Dialog */}
      <DeleteSessionDialog
        isOpen={deleteOpen}
        onClose={() => setDeleteOpen(false)}
      />

      {/* Persistent Accessible Screen Reader Announcer */}
      <div id="a11y-announcer" aria-live="polite" className="sr-only" />

      {/* Global Footer */}
      <footer className="mt-auto border-t border-line bg-paper/80 backdrop-blur-md py-8 px-6 text-center text-xs text-mute space-y-3">
        <p className="max-w-3xl mx-auto leading-relaxed">
          {t('disclaimers.footer')}
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4 text-xs font-semibold text-navy pt-2">
          <a
            href="https://nalsa.gov.in/legal-aid/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-blue hover:underline"
            aria-label="National Legal Services Authority (Opens an official external site; internet needed)"
          >
            <span>NALSA Free Legal Aid</span>
            <ExternalLink className="w-3 h-3" aria-hidden="true" />
          </a>
          <span>·</span>
          <span>Legal Aid Helpline: 15100</span>
          <span>·</span>
          <span>NyayaSarathi (CTBF-AI-09)</span>
        </div>
      </footer>
    </div>
  );
};
