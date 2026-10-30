/**
 * ClauseInspectorPreview Component
 * Exact match to Section #try in the preview HTML:
 * - Interactive clause-by-clause inspector
 * - Trilingual explanations (EN, HI, PA) reacting to active language
 * - Colored tags for concerns, auto-renewal, and deadlines
 * - Animated explanation reveal (pop keyframe)
 * - Animated coverage indicator bar
 */

import React, { useState } from 'react';
import { useT } from '../../lib/i18n';

interface SampleClause {
  q: string;
  t: [string, string][];
  p: string;
  e: { en: string; hi: string; pa: string };
}

const SAMPLE_CLAUSES: SampleClause[] = [
  {
    q: 'The Tenant shall pay ₹18,000 on or before the 5th of every month.',
    t: [['g', 'Information']],
    p: 'Cl. 2 · p.1',
    e: {
      en: 'Rent is ₹18,000, due by the 5th of each month.',
      hi: 'किराया ₹18,000 है, हर महीने की 5 तारीख तक देना है।',
      pa: 'ਕਿਰਾਇਆ ₹18,000 ਹੈ, ਹਰ ਮਹੀਨੇ ਦੀ 5 ਤਾਰੀਖ਼ ਤੱਕ ਦੇਣਾ ਹੈ।',
    },
  },
  {
    q: 'A penalty of 3% per week shall be levied on delayed rent.',
    t: [['r', 'Potential concern · Penalty']],
    p: 'Cl. 5 · p.1',
    e: {
      en: 'Late rent adds a 3% charge for every week of delay.',
      hi: 'देर होने पर हर हफ़्ते 3% अतिरिक्त शुल्क लगेगा।',
      pa: 'ਦੇਰੀ ਹੋਣ ’ਤੇ ਹਰ ਹਫ਼ਤੇ 3% ਵਾਧੂ ਖ਼ਰਚਾ ਲੱਗੇਗਾ।',
    },
  },
  {
    q: 'This agreement shall automatically renew for 11 months unless notice is given 60 days prior.',
    t: [
      ['a', 'Potential concern · Auto-renewal'],
      ['c', 'Deadline · 60 days'],
    ],
    p: 'Cl. 8 · p.2',
    e: {
      en: 'The lease renews itself for 11 months unless notice is given 60 days before it ends.',
      hi: 'नोटिस न देने पर समझौता अपने-आप 11 महीने बढ़ जाएगा; नोटिस 60 दिन पहले देना है।',
      pa: 'ਨੋਟਿਸ ਨਾ ਦੇਣ ’ਤੇ ਸਮਝੌਤਾ ਆਪਣੇ-ਆਪ 11 ਮਹੀਨੇ ਵਧ ਜਾਵੇਗਾ; ਨੋਟਿਸ 60 ਦਿਨ ਪਹਿਲਾਂ ਦੇਣਾ ਹੈ।',
    },
  },
  {
    q: 'The Tenant waives all rights to approach any court regarding eviction.',
    t: [['r', 'Potential concern · Waived right']],
    p: 'Cl. 11 · p.2',
    e: {
      en: 'This clause says you give up the right to go to court over eviction.',
      hi: 'यह शर्त बेदखली पर अदालत जाने का आपका अधिकार छोड़ने को कहती है।',
      pa: 'ਇਹ ਸ਼ਰਤ ਬੇਦਖ਼ਲੀ ਬਾਰੇ ਅਦਾਲਤ ਜਾਣ ਦਾ ਤੁਹਾਡਾ ਅਧਿਕਾਰ ਛੱਡਣ ਲਈ ਕਹਿੰਦੀ ਹੈ।',
    },
  },
  {
    q: 'Security deposit of ₹54,000 is refundable within 30 days of vacating.',
    t: [['c', 'Deadline · 30 days']],
    p: 'Cl. 13 · p.3',
    e: {
      en: 'Deposit of ₹54,000 is to be returned within 30 days of vacating.',
      hi: 'खाली करने के 30 दिन के भीतर ₹54,000 की जमा राशि लौटाई जानी है।',
      pa: 'ਖ਼ਾਲੀ ਕਰਨ ਦੇ 30 ਦਿਨਾਂ ਦੇ ਅੰਦਰ ₹54,000 ਦੀ ਜਮ੍ਹਾਂ ਰਕਮ ਮੁੜਨੀ ਹੈ।',
    },
  },
];

export const ClauseInspectorPreview: React.FC = () => {
  const { uiLanguage } = useT();
  const [selectedIndex, setSelectedIndex] = useState<number>(1);
  const [animKey, setAnimKey] = useState<number>(0);

  const activeClause = SAMPLE_CLAUSES[selectedIndex] || SAMPLE_CLAUSES[0];
  const langKey = (uiLanguage === 'hi' || uiLanguage === 'pa' ? uiLanguage : 'en') as 'en' | 'hi' | 'pa';

  const handleSelect = (idx: number) => {
    setSelectedIndex(idx);
    setAnimKey((prev) => prev + 1);
  };

  return (
    <section id="try" className="py-16 px-4 sm:px-6 max-w-6xl mx-auto space-y-6">
      <div className="space-y-2">
        <h2 className="reveal text-2xl sm:text-3xl font-extrabold text-navy tracking-tight">
          Clause-by-clause inspector
        </h2>
        <p className="lead reveal text-mute text-base max-w-2xl">
          Pick a clause on the left. The explanation, concern label and source evidence follow — in
          the language you choose. Sample content for preview.
        </p>
      </div>

      <div className="insp reveal">
        {/* Left Pane: Original Document */}
        <div className="pane">
          <h3>
            <span>ORIGINAL DOCUMENT</span>
            <span className="font-mono text-mute">Rent agreement</span>
          </h3>
          <div className="space-y-1">
            {SAMPLE_CLAUSES.map((c, i) => (
              <button
                key={i}
                type="button"
                onClick={() => handleSelect(i)}
                className={`cl ${i === selectedIndex ? 'on' : ''}`}
              >
                <em>{i + 1}</em>
                <span>{c.q}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Right Pane: Plain-Language Explanation */}
        <div className="pane flex flex-col justify-between">
          <div>
            <h3>
              <span>PLAIN-LANGUAGE EXPLANATION</span>
              <span className="font-mono font-bold text-blue">{langKey.toUpperCase()}</span>
            </h3>

            {/* Tags */}
            <div className="mb-2">
              {activeClause.t.map(([colorCode, tagLabel], idx) => (
                <span key={idx} className={`tag t-${colorCode}`}>
                  {tagLabel}
                </span>
              ))}
            </div>

            {/* Explanation with pop animation */}
            <p key={animKey} id="ex" className="text-navy font-medium">
              {activeClause.e[langKey]}
            </p>

            {/* Evidence box */}
            <div className="ev">
              Evidence: <strong className="text-navy font-mono">{activeClause.p}</strong> — opens the
              exact passage in the source viewer
            </div>
          </div>

          {/* Coverage Bar */}
          <div className="cov pt-4 border-t border-line/40">
            <span className="font-mono text-xs text-mute shrink-0">Analysed 5 / 5 clauses</span>
            <div className="bar">
              <i />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
export default ClauseInspectorPreview;
