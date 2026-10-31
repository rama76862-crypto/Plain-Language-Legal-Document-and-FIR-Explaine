/**
 * EvidenceBeam Component
 * Draws a glowing energetic SVG beam with traveling photon pulses between
 * an evidence citation button on the right pane and the highlighted source passage on the left pane.
 * Automatically recalculates coordinates on scroll or resize.
 */

import React, { useEffect, useState } from 'react';
import { useReducedMotion } from '../motion';

interface EvidenceBeamProps {
  fromSelector?: string;
  toSelector?: string;
}

export const EvidenceBeam: React.FC<EvidenceBeamProps> = ({
  fromSelector = '[data-evidence-source="active"]',
  toSelector = '[data-evidence-target="active"]',
}) => {
  const reduced = useReducedMotion();
  const [coords, setCoords] = useState<{ x1: number; y1: number; x2: number; y2: number } | null>(null);

  useEffect(() => {
    if (reduced || window.innerWidth < 1024) {
      setCoords(null);
      return;
    }

    const updateCoords = () => {
      const fromEl = document.querySelector(fromSelector);
      const toEl = document.querySelector(toSelector);

      if (!fromEl || !toEl) {
        setCoords(null);
        return;
      }

      const rect1 = fromEl.getBoundingClientRect();
      const rect2 = toEl.getBoundingClientRect();

      setCoords({
        x1: rect1.left + rect1.width / 2,
        y1: rect1.top + rect1.height / 2,
        x2: rect2.left + rect2.width / 2,
        y2: rect2.top + rect2.height / 2,
      });
    };

    updateCoords();

    window.addEventListener('resize', updateCoords);
    window.addEventListener('scroll', updateCoords, true);

    return () => {
      window.removeEventListener('resize', updateCoords);
      window.removeEventListener('scroll', updateCoords, true);
    };
  }, [fromSelector, toSelector, reduced]);

  if (reduced || !coords) return null;

  const dx = coords.x2 - coords.x1;
  const pathD = `M ${coords.x1} ${coords.y1} C ${coords.x1 + dx * 0.45} ${coords.y1}, ${
    coords.x2 - dx * 0.45
  } ${coords.y2}, ${coords.x2} ${coords.y2}`;

  return (
    <svg
      className="fixed inset-0 w-full h-full pointer-events-none z-50 overflow-visible"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="beamGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#2F6BFF" stopOpacity="0.3" />
          <stop offset="50%" stopColor="#07B3D1" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#00FFFF" stopOpacity="0.4" />
        </linearGradient>
        <filter id="beamGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* Soft Ambient Glow Halo */}
      <path
        d={pathD}
        fill="none"
        stroke="url(#beamGradient)"
        strokeWidth="6"
        opacity="0.25"
      />

      {/* Core Glowing Dashed Line */}
      <path
        d={pathD}
        fill="none"
        stroke="url(#beamGradient)"
        strokeWidth="2.5"
        strokeDasharray="8 6"
        filter="url(#beamGlow)"
      />

      {/* Leading Traveling Photon Dot 1 */}
      <circle r="4.5" fill="#00FFFF" filter="url(#beamGlow)">
        <animateMotion path={pathD} dur="1.2s" repeatCount="indefinite" />
      </circle>

      {/* Trailing Photon Dot 2 */}
      <circle r="3" fill="#2F6BFF" opacity="0.8">
        <animateMotion path={pathD} dur="1.2s" begin="0.3s" repeatCount="indefinite" />
      </circle>
    </svg>
  );
};

export default EvidenceBeam;
