/**
 * LegalAidDirectoryCard Component (C-14)
 * Provides verified pathways to free government legal aid:
 * - Official NALSA (National Legal Services Authority) & DLSA directory links
 * - Toll-free Legal Aid Helpline: 15100
 * - Statutory notice: Eligibility decided by authorities
 * - Strict outbound labeling: "Opens an official external site; internet needed"
 */

import React from 'react';
import { ExternalLink, Phone, ShieldCheck, Scale, Globe } from 'lucide-react';
import type { LegalAidLink } from '../../lib/types';
import { GlassCard } from '../../design/primitives';

interface LegalAidDirectoryCardProps {
  legalAid?: LegalAidLink[];
  variant?: 'full' | 'compact';
  className?: string;
}

export const LegalAidDirectoryCard: React.FC<LegalAidDirectoryCardProps> = ({
  legalAid = [],
  variant = 'full',
  className = '',
}) => {
  const defaultAid: LegalAidLink[] = [
    {
      title: 'National Legal Services Authority (NALSA) - Online Legal Aid Application',
      url: 'https://nalsa.gov.in/legal-aid/',
    },
    {
      title: 'State & District Legal Services Authorities (SLSA / DLSA Directory)',
      url: 'https://nalsa.gov.in/state-legal-services-authorities',
    },
  ];

  const links = legalAid.length > 0 ? legalAid : defaultAid;

  if (variant === 'compact') {
    return (
      <div
        className={`p-3 rounded-lg border border-cyan/30 bg-paper/80 flex flex-wrap items-center justify-between gap-3 text-xs ${className}`}
      >
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-cyan shrink-0" />
          <span className="font-semibold text-navy">Need help? Free legal aid is available.</span>
          <span className="text-mute hidden sm:inline">
            Call NALSA helpline: <strong className="text-navy font-mono">15100</strong>
          </span>
        </div>

        <a
          href="https://nalsa.gov.in/legal-aid/"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-semibold rounded bg-cyan/15 text-cyan hover:bg-cyan/25 transition-colors"
          aria-label="National Legal Services Authority (Opens an official external site; internet needed)"
        >
          <span>NALSA Portal</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    );
  }

  return (
    <GlassCard className={`p-6 border-cyan/30 bg-paper space-y-4 shadow-card ${className}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded bg-cyan/10 text-cyan">
              Public Legal Assistance
            </span>
            <span className="text-xs font-mono text-mute">Government of India</span>
          </div>
          <h4 className="text-base font-bold text-navy flex items-center gap-2">
            <Scale className="w-5 h-5 text-cyan shrink-0" />
            Free Legal Aid & Representation
          </h4>
        </div>

        {/* Helpline Pill */}
        <div className="flex flex-col items-end shrink-0">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-navy text-white text-xs font-mono font-bold shadow-xs">
            <Phone className="w-3.5 h-3.5 text-cyan shrink-0" />
            <span>15100</span>
          </div>
          <span className="text-[10px] text-mute mt-1 font-mono">Toll-free NALSA helpline</span>
        </div>
      </div>

      {/* Official Legal Explanatory Copy */}
      <div className="p-3.5 rounded-lg bg-bg2/60 border border-line text-xs text-navy/90 leading-relaxed space-y-2">
        <p>
          Free legal aid is available through <strong>District Legal Services Authorities (DLSA)</strong>{' '}
          and <strong>NALSA</strong> under the Legal Services Authorities Act, 1987 for eligible people,
          including women, children, members of SC/ST, and persons with annual income below prescribed ceilings.
        </p>
        <p className="text-[11px] text-mute italic">
          Eligibility for free legal aid is decided by the respective legal services authority.
        </p>
      </div>

      {/* Directory Links */}
      <div className="space-y-2 pt-1">
        <span className="text-[11px] font-mono uppercase text-mute font-semibold">
          Official Government Portals
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {links.map((link, idx) => (
            <a
              key={idx}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-3 rounded-md border border-line bg-paper hover:bg-bg2/40 hover:border-cyan/50 transition-all flex items-center justify-between text-xs text-navy group"
              aria-label={`${link.title} (Opens an official external site; internet needed)`}
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
          Official external government resources
        </span>
        <span>Internet connection needed</span>
      </div>
    </GlassCard>
  );
};
export default LegalAidDirectoryCard;
