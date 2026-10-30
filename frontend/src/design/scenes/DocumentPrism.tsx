/**
 * DocumentPrism 3D Hero Scene
 * Exact match to the preview HTML:
 * - 3D stacked sheets (.s0, .s1, .s2)
 * - Animated sweeping laser scan beam (.beam)
 * - Formatted legal lines and highlights (.hl.r, .hl.a, .hl.c)
 * - 3 floating perspective chips (.chip.r, .chip.a, .chip.c) with bob animation
 * - 3D floating shield (.shield)
 * - Interactive pointer parallax setting --rx and --ry dynamically
 */

import React, { useRef } from 'react';
import { useReducedMotion } from '../motion';

export const DocumentPrism: React.FC<{ className?: string }> = ({ className = '' }) => {
  const stageRef = useRef<HTMLDivElement | null>(null);
  const sceneRef = useRef<HTMLDivElement | null>(null);
  const reduced = useReducedMotion();

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (reduced || !stageRef.current || !sceneRef.current) return;
    const r = stageRef.current.getBoundingClientRect();
    const rx = (0.5 - (e.clientY - r.top) / r.height) * 26;
    const ry = ((e.clientX - r.left) / r.width - 0.5) * 40;
    sceneRef.current.style.setProperty('--rx', `${rx}deg`);
    sceneRef.current.style.setProperty('--ry', `${ry}deg`);
  };

  const handlePointerLeave = () => {
    if (!sceneRef.current) return;
    sceneRef.current.style.setProperty('--rx', '8deg');
    sceneRef.current.style.setProperty('--ry', '-16deg');
  };

  return (
    <div
      ref={stageRef}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      className={`stage select-none ${className}`}
      aria-hidden="true"
    >
      <div ref={sceneRef} className="scene">
        {/* Layer 0: Deep sheet */}
        <div className="sheet s0" />

        {/* Layer 1: Mid sheet */}
        <div className="sheet s1" />

        {/* Layer 2: Top active sheet with document scan */}
        <div className="sheet s2">
          <div className="beam" />
          <h4 className="font-mono text-xs uppercase tracking-wider text-mute">
            RENT AGREEMENT · PAGE 2
          </h4>
          <div className="ln" style={{ width: '92%' }} />
          <div className="ln" style={{ width: '70%' }} />
          <div className="hl r font-semibold">3% weekly penalty on late rent</div>
          <div className="ln" style={{ width: '85%' }} />
          <div className="hl a font-semibold">Auto-renews unless 60 days’ notice</div>
          <div className="ln" style={{ width: '78%' }} />
          <div className="ln" style={{ width: '55%' }} />
          <div className="hl c font-semibold">Deposit due back in 30 days</div>
          <div className="ln" style={{ width: '88%' }} />
        </div>

        {/* Floating 3D perspective chips */}
        <div className="chip r font-semibold">⚠ Potential concern</div>
        <div className="chip a font-semibold">🔁 Auto-renewal</div>
        <div className="chip c font-semibold">⏱ Deadline found</div>

        {/* Floating 3D Shield */}
        <div className="shield">🛡</div>
      </div>
    </div>
  );
};
export default DocumentPrism;
