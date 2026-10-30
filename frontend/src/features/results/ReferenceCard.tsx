/**
 * ReferenceCard Component
 * Displays verified official legal statutory references (e.g. Acts, Sections).
 * Strictly renders references ONLY when they resolve against result.references.
 * Never invents, hallucinates, or fabricates citations.
 */

import React, { useState } from 'react';
import { BookOpen, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import type { Reference } from '../../lib/types';
import { useT } from '../../lib/i18n';

interface ReferenceCardProps {
  reference: Reference;
  className?: string;
}

export const ReferenceCard: React.FC<ReferenceCardProps> = ({ reference, className = '' }) => {
  const { t } = useT();
  const [expanded, setExpanded] = useState<boolean>(false);

  return (
    <div
      className={`p-3 rounded-lg border border-line bg-paper/90 text-xs space-y-2 shadow-xs ${className}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 font-bold text-navy">
          <BookOpen className="w-3.5 h-3.5 text-blue shrink-0" />
          <span>{reference.title}</span>
          {reference.section && (
            <span className="text-[11px] font-mono px-1.5 py-0.2 rounded bg-bg2 text-mute">
              {reference.section}
            </span>
          )}
        </div>

        {reference.url && (
          <a
            href={reference.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue hover:underline shrink-0"
            aria-label={`Official link for ${reference.title} (${t('results.opensExternalSite')})`}
          >
            <span>{t('results.officialText')}</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>

      {reference.version && (
        <div className="text-[10px] font-mono text-mute">
          {t('results.statuteVersion', { version: reference.version })}
        </div>
      )}

      {reference.excerpt && (
        <div className="space-y-1">
          <div
            className={`font-serif italic text-navy/90 border-l-2 border-blue/40 pl-2 leading-relaxed ${
              expanded ? '' : 'line-clamp-3'
            }`}
          >
            "{reference.excerpt}"
          </div>
          {reference.excerpt.length > 120 && (
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="text-[11px] text-blue hover:underline flex items-center gap-0.5 font-medium"
            >
              <span>{expanded ? t('results.showLess') : t('results.readExcerpt')}</span>
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          )}
        </div>
      )}

      <div className="text-[10px] text-mute flex items-center justify-between pt-1 border-t border-line/60">
        <span>{t('results.officialSourceDisclaimer')}</span>
        <span>{t('results.opensExternalSite')}</span>
      </div>
    </div>
  );
};
export default ReferenceCard;
