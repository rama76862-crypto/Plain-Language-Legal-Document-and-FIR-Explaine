/**
 * EvidenceBeam Component
 * Draws an animated SVG beam with traveling pulses between
 * an evidence button on the right pane and the highlighted source passage on the left pane.
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
  const pathD = `M ${coords.x1} ${coords.y1} C ${coords.x1 + dx * 0.5} ${coords.y1}, ${
    coords.x2 - dx * 0.5
  } ${coords.y2}, ${coords.x2} ${coords.y2}`;

  return (
    <svg
      className="fixed inset-0 w-full h-full pointer-events-none z-40 overflow-visible"
      aria-hidden="true"
    >
      <path
        d={pathD}
        fill="none"
        stroke="var(--cyan)"
        strokeWidth="2"
        strokeDasharray="6 6"
        opacity="0.8"
      />
      <circle r="4" fill="var(--blue)">
        <animateMotion path={pathD} dur="1.2s" repeatCount="indefinite" />
      </circle>
    </svg>
  );
};
export default EvidenceBeam;
