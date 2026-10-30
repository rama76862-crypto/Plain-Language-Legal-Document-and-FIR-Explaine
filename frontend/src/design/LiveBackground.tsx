/**
 * LiveBackground Component
 * Exact match to the preview HTML:
 * - 3 drifting blurred pastel blobs (.blob.b1, .blob.b2, .blob.b3)
 * - Canvas #bg with 34 drifting, rotating legal glyphs (§, ¶, ⚖, ਨ, न)
 * - Real-time horizontal parallax sway reacting to pointermove
 */

import React, { useEffect, useRef } from 'react';
import { useReducedMotion, usePageVisible } from './motion';

const GLYPHS = ['§', '¶', '⚖', 'ਨ', 'न', '§', '¶'];

interface GlyphParticle {
  x: number;
  y: number;
  s: number; // size
  v: number; // velocity
  g: string; // glyph
  a: number; // alpha
  r: number; // rotation phase
}

export const LiveBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const reduced = useReducedMotion();
  const isVisible = usePageVisible();

  useEffect(() => {
    if (reduced || !isVisible) return;

    const cv = canvasRef.current;
    if (!cv) return;
    const g = cv.getContext('2d');
    if (!g) return;

    let animId: number;
    let W = (cv.width = window.innerWidth);
    let H = (cv.height = window.innerHeight);
    let mx = 0;

    const rs = () => {
      W = cv.width = window.innerWidth;
      H = cv.height = window.innerHeight;
    };
    window.addEventListener('resize', rs);

    const onPointerMove = (e: PointerEvent) => {
      mx = (e.clientX / W - 0.5) * 30;
    };
    window.addEventListener('pointermove', onPointerMove, { passive: true });

    // Initialize 34 drifting particles
    const P: GlyphParticle[] = [];
    for (let i = 0; i < 34; i++) {
      P.push({
        x: Math.random() * W,
        y: Math.random() * H,
        s: 14 + Math.random() * 30,
        v: 0.15 + Math.random() * 0.4,
        g: GLYPHS[i % GLYPHS.length],
        a: 0.05 + Math.random() * 0.1,
        r: Math.random() * 6,
      });
    }

    const render = () => {
      g.clearRect(0, 0, W, H);
      for (const p of P) {
        p.y -= p.v;
        p.r += 0.003;
        if (p.y < -40) {
          p.y = H + 40;
          p.x = Math.random() * W;
        }

        g.save();
        g.translate(p.x + (mx * p.s) / 20, p.y);
        g.rotate(Math.sin(p.r) * 0.5);
        g.globalAlpha = p.a;
        g.fillStyle = '#2f6bff';
        g.font = `${p.s}px serif`;
        g.fillText(p.g, 0, 0);
        g.restore();
      }
      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', rs);
      window.removeEventListener('pointermove', onPointerMove);
    };
  }, [reduced, isVisible]);

  return (
    <>
      <canvas id="bg" ref={canvasRef} aria-hidden="true" />
      <div className="blob b1" aria-hidden="true" />
      <div className="blob b2" aria-hidden="true" />
      <div className="blob b3" aria-hidden="true" />
    </>
  );
};
export default LiveBackground;
