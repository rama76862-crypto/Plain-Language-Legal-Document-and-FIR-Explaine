/**
 * ShredDissolve Scene
 * Plays an ephemeral particle dissolution animation when session is deleted.
 * Calls onDone() when animation finishes (~1.2s).
 */

import React, { useEffect, useRef } from 'react';
import { useReducedMotion } from '../motion';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  rot: number;
  vRot: number;
}

export const ShredDissolve: React.FC<{ onDone?: () => void }> = ({ onDone }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    if (reduced) {
      onDone?.();
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = (canvas.width = window.innerWidth);
    const height = (canvas.height = window.innerHeight);

    const particles: Particle[] = [];
    const count = 120;
    const cx = width / 2;
    const cy = height / 2;

    for (let i = 0; i < count; i++) {
      particles.push({
        x: cx + (Math.random() - 0.5) * 260,
        y: cy + (Math.random() - 0.5) * 320,
        vx: (Math.random() - 0.5) * 8,
        vy: -2 - Math.random() * 6,
        size: 6 + Math.random() * 12,
        alpha: 1.0,
        rot: Math.random() * Math.PI,
        vRot: (Math.random() - 0.5) * 0.2,
      });
    }

    let animId: number;
    const startTime = performance.now();

    const render = (time: number) => {
      const elapsed = time - startTime;
      ctx.clearRect(0, 0, width, height);

      let alive = false;
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        p.rot += p.vRot;
        p.alpha = Math.max(0, 1 - elapsed / 1100);

        if (p.alpha > 0) {
          alive = true;
          ctx.save();
          ctx.translate(p.x, p.y);
          ctx.rotate(p.rot);
          ctx.fillStyle = '#FFFFFF';
          ctx.strokeStyle = '#14306B';
          ctx.lineWidth = 1;
          ctx.globalAlpha = p.alpha;
          ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 1.5);
          ctx.strokeRect(-p.size / 2, -p.size / 2, p.size, p.size * 1.5);
          ctx.restore();
        }
      }

      if (alive && elapsed < 1200) {
        animId = requestAnimationFrame(render);
      } else {
        onDone?.();
      }
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [reduced, onDone]);

  if (reduced) return null;

  return (
    <div
      className="fixed inset-0 z-[100] pointer-events-none bg-navy/30 backdrop-blur-sm flex items-center justify-center"
      aria-hidden="true"
    >
      <canvas ref={canvasRef} className="absolute inset-0 block w-full h-full" />
    </div>
  );
};
export default ShredDissolve;
