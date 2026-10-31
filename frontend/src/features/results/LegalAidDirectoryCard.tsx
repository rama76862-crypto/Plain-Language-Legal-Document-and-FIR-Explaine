/**
 * LegalAidDirectoryCard Component (C-14)
 * Provides verified pathways to free government legal aid:
 * - Official NALSA (National Legal Services Authority) & DLSA directory links
 * - Toll-free Legal Aid Helpline: 15100 (clickable with tel:15100)
 * - Statutory notice: Eligibility decided by authorities under Legal Services Authorities Act, 1987
 * - Strict outbound labeling: "Opens an official external site; internet needed"
 */

import React from 'react';
import { ExternalLink, Phone, ShieldCheck, Scale, Globe, Building2 } from 'lucide-react';
import type { LegalAidLink } from '../../lib/types';
import { GlassCard } from '../../design/primitives';
import { useT } from '../../lib/i18n';
import { useReducedMotion } from '../../design/motion';

const RotatingScalesEmblem: React.FC = () => {
  const reduced = useReducedMotion();
  return (
    <div
      className="relative w-8 h-8 [perspective:500px] flex items-center justify-center shrink-0 select-none"
      aria-hidden="true"
    >
      <div
        className="w-8 h-8 rounded-full bg-gradient-to-tr from-navy via-navy to-blue/80 text-cyan flex items-center justify-center shadow-md border border-cyan/50"
        style={{
          animation: reduced ? 'none' : 'scales-rock 4s ease-in-out infinite alternate',
          transformStyle: 'preserve-3d',
        }}
      >
        <Scale className="w-4 h-4 text-cyan drop-shadow-[0_0_4px_rgba(7,179,209,0.8)]" />
      </div>
      <style>{`
        @keyframes scales-rock {
          0% { transform: rotateY(-28deg) rotateX(8deg); }
          50% { transform: rotateY(0deg) rotateX(0deg); }
          100% { transform: rotateY(28deg) rotateX(-8deg); }
        }
      `}</style>
    </div>
  );
};

interface LegalAidDirectoryCardProps {
  legalAid?: LegalAidLink[];
  variant?: 'full' | 'compact';
  className?: string;
  onOpenFull?: () => void;
}

export const LegalAidDirectoryCard: React.FC<LegalAidDirectoryCardProps> = ({
  legalAid = [],
  variant = 'full',
  className = '',
  onOpenFull,
}) => {
  const { t } = useT();
  const defaultAid: LegalAidLink[] = [
    {
      title: 'National Legal Services Authority (NALSA) - Online Legal Aid Application',
      url: 'https://nalsa.gov.in/legal-aid/',
    },
    {
      title: 'State & District Legal Services Authorities (SLSA / DLSA Directory)',
      url: 'https://nalsa.gov.in/directory/',
    },
    {
      title: 'Tele-Law Service (Department of Justice) - Free Legal Advice',
      url: 'https://doj.gov.in/tele-law/',
    },
  ];

  const links = [...legalAid,...defaultAid].filter((link,index,all)=>all.findIndex(candidate=>candidate.url===link.url)===index);

  if (variant === 'compact') {
    return (
      <div
        className={`p-3 rounded-lg border border-cyan/30 bg-paper/80 flex flex-wrap items-center justify-between gap-3 text-xs ${className}`}
      >
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-cyan shrink-0" />
          <span className="font-semibold text-navy">{t('legalAid.needHelp')}</span>
          <span className="text-mute hidden sm:inline">
            {t('legalAid.callHelpline')}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {onOpenFull && (
            <button
              type="button"
              onClick={onOpenFull}
              className="px-2.5 py-1 text-[11px] font-semibold rounded bg-blue/10 text-blue hover:bg-blue/20 transition-colors"
            >
              {t('legalAid.freeAidTitle')} &rarr;
            </button>
          )}
          <a
            href="https://nalsa.gov.in/legal-aid/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-semibold rounded bg-cyan/15 text-cyan hover:bg-cyan/25 transition-colors"
            aria-label={`National Legal Services Authority (${t('legalAid.internetNeeded')})`}
          >
            <span>NALSA Portal</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    );
  }

  return (
    <GlassCard className={`p-6 border-cyan/40 bg-paper space-y-5 shadow-card hover:shadow-[0_0_30px_-5px_rgba(7,179,209,0.25)] transition-shadow duration-500 ${className}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded bg-cyan/10 text-cyan">
              {t('legalAid.publicAssistance')}
            </span>
            <span className="text-xs font-mono text-mute">{t('legalAid.govIndia')}</span>
          </div>
          <h4 className="text-lg font-bold text-navy flex items-center gap-2.5">
            <RotatingScalesEmblem />
            {t('legalAid.freeAidTitle')}
          </h4>
          <p className="text-xs text-mute">
            {t('legalAid.eligibilityNote')}
          </p>
        </div>

        {/* Helpline Click-to-call Pill */}
        <div className="flex flex-col items-end shrink-0">
          <a
            href="tel:15100"
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-md bg-navy text-white text-xs font-mono font-bold shadow-xs hover:bg-navy/90 hover:ring-2 hover:ring-cyan/50 transition-all"
            title="Call Toll-free Legal Aid Helpline 15100"
          >
            <Phone className="w-4 h-4 text-cyan shrink-0 animate-pulse" />
            <span>15100</span>
          </a>
          <span className="text-[10px] text-mute mt-1 font-mono">{t('legalAid.tollFree')}</span>
        </div>
      </div>

      {/* Official Legal Explanatory Copy */}
      <div className="p-3.5 rounded-lg bg-bg2/60 border border-line text-xs text-navy/90 leading-relaxed space-y-2">
        <p className="font-semibold text-navy">
          {t('disclaimers.legalAidNotice')}
        </p>
        <p className="text-[11px] text-mute italic">
          {t('legalAid.eligibilityNote')}
        </p>
      </div>

      {/* Legal Aid Hierarchy Cards (NALSA vs DLSA) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
        <div className="p-3.5 rounded-lg border border-line bg-bg2/40 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-navy">
            <Building2 className="w-4 h-4 text-blue" />
            <span>District Legal Services Authority (DLSA)</span>
          </div>
          <p className="text-xs text-mute leading-relaxed">
            {t('legalAid.districtDescription')}
          </p>
          <div className="text-[11px] font-mono text-blue font-semibold">
            {t('legalAid.directoryHint')}
          </div>
        </div>

        <div className="p-3.5 rounded-lg border border-line bg-bg2/40 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-navy">
            <Scale className="w-4 h-4 text-cyan" />
            <span>National Legal Services Authority (NALSA)</span>
          </div>
          <p className="text-xs text-mute leading-relaxed">
            {t('legalAid.nationalDescription')}
          </p>
          <div className="text-[11px] font-mono text-cyan font-semibold">
            {t('legalAid.applicationHint')}
          </div>
        </div>
      </div>

      <a href="https://nalsa.gov.in/faqs/" target="_blank" rel="noopener noreferrer" className="text-sm text-blue underline">
        {t('legalAid.officialFaq')} ({t('legalAid.internetNeeded')})
      </a>

      {/* Directory Links */}
      <div className="space-y-2 pt-1">
        <span className="text-[11px] font-mono uppercase text-mute font-semibold">
          {t('legalAid.portalsHeader')}
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {links.map((link, idx) => (
            <a
              key={idx}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-3 rounded-md border border-line bg-paper hover:bg-bg2/40 hover:border-cyan/50 transition-all flex items-center justify-between text-xs text-navy group"
              aria-label={`${link.title} (${t('legalAid.internetNeeded')})`}
            >
              <div className="flex items-center gap-2 truncate pr-2">
                <Globe className="w-3.5 h-3.5 text-cyan shrink-0" />
                <span className="font-medium truncate group-hover:text-blue">{link.title}</span>
              </div>
              <ExternalLink className="w-3.5 h-3.5 text-mute group-hover:text-blue shrink-0" />
            </a>
          ))}
        </div>
      </div>

      {/* Outbound Notice Disclaimer */}
      <div className="pt-2 border-t border-line/60 flex items-center justify-between text-[10px] font-mono text-mute">
        <span className="flex items-center gap-1">
          <ShieldCheck className="w-3 h-3 text-ok" />
          {t('legalAid.externalResources')}
        </span>
        <span>{t('legalAid.internetNeeded')}</span>
      </div>
    </GlassCard>
  );
};
export default LegalAidDirectoryCard;
