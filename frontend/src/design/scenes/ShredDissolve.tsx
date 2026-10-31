/**
 * ShredDissolve Scene
 * Plays an ephemeral paper-particle dissolution animation with shockwave
 * when a user deletes their session, ensuring physical feedback of erasure.
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
  color: string;
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
    const count = 150;
    const cx = width / 2;
    const cy = height / 2;

    const colors = ['#FFFFFF', '#E0F2FE', '#BAE6FD', '#07B3D1', '#FFFFFF'];

    for (let i = 0; i < count; i++) {
      particles.push({
        x: cx + (Math.random() - 0.5) * 280,
        y: cy + (Math.random() - 0.5) * 340,
        vx: (Math.random() - 0.5) * 9,
        vy: -3 - Math.random() * 8,
        size: 5 + Math.random() * 14,
        alpha: 1.0,
        rot: Math.random() * Math.PI,
        vRot: (Math.random() - 0.5) * 0.25,
        color: colors[i % colors.length],
      });
    }

    let animId: number;
    const startTime = performance.now();

    const render = (time: number) => {
      const elapsed = Math.max(0, time - startTime);
      ctx.clearRect(0, 0, width, height);

      // Expanding cyan shockwave ring
      const ringRadius = (elapsed / 1200) * (Math.min(width, height) * 0.65);
      const ringAlpha = Math.max(0, 0.4 * (1 - elapsed / 900));
      if (ringAlpha > 0) {
        ctx.strokeStyle = `rgba(7, 179, 209, ${ringAlpha})`;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(cx, cy, ringRadius, 0, Math.PI * 2);
        ctx.stroke();
      }

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
          ctx.fillStyle = p.color;
          ctx.strokeStyle = '#14306B';
          ctx.lineWidth = 0.8;
          ctx.globalAlpha = p.alpha;
          ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 1.4);
          ctx.strokeRect(-p.size / 2, -p.size / 2, p.size, p.size * 1.4);
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
      className="fixed inset-0 z-[100] pointer-events-none bg-navy/40 backdrop-blur-md flex items-center justify-center transition-all duration-300"
      aria-hidden="true"
    >
      <canvas ref={canvasRef} className="absolute inset-0 block w-full h-full" />
    </div>
  );
};

export default ShredDissolve;
