/**
 * DotGridField ("FractalDotGrid")
 * Interactive canvas dot field for landing hero:
 * - Dots swell and glow based on mouse proximity
 * - Click triggers a soft outward ripple
 * - Automatically degrades resolution if frame duration > 24ms for 2 consecutive seconds
 */

import React, { useEffect, useRef } from 'react';
import { useReducedMotion, usePageVisible } from './motion';

interface DotGridFieldProps {
  dotSize?: number;
  spacing?: number;
  glow?: boolean;
  performanceTier?: 'low' | 'medium' | 'high';
  className?: string;
}

interface Ripple {
  x: number;
  y: number;
  radius: number;
  maxRadius: number;
  alpha: number;
}

export const DotGridField: React.FC<DotGridFieldProps> = ({
  dotSize = 1.5,
  spacing = 28,
  glow = true,
  performanceTier = 'high',
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const reduced = useReducedMotion();
  const isVisible = usePageVisible();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || window.innerWidth);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 600);

    const onResize = () => {
      if (!canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
    };
    window.addEventListener('resize', onResize);

    let mouseX = -9999;
    let mouseY = -9999;
    const ripples: Ripple[] = [];

    const onPointerMove = (e: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouseX = e.clientX - rect.left;
      mouseY = e.clientY - rect.top;
    };

    const onClick = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      ripples.push({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        radius: 0,
        maxRadius: 220,
        alpha: 0.8,
      });
    };

    const targetEl = canvas.parentElement || canvas;
    targetEl.addEventListener('pointermove', onPointerMove as EventListener);
    targetEl.addEventListener('click', onClick as EventListener);

    // Frame budget performance auto-downgrade monitor
    let currentSpacing = performanceTier === 'low' ? spacing * 1.5 : spacing;
    let slowFramesDuration = 0;
    let lastTimestamp = window.performance.now();

    const render = (now: number) => {
      const delta = now - lastTimestamp;
      lastTimestamp = now;

      if (delta > 24) {
        slowFramesDuration += delta;
        if (slowFramesDuration > 2000 && currentSpacing === spacing) {
          currentSpacing = spacing * 1.4; // Auto-downgrade density
        }
      } else {
        slowFramesDuration = Math.max(0, slowFramesDuration - delta * 0.5);
      }

      ctx.clearRect(0, 0, width, height);

      // Update and prune ripples
      for (let i = ripples.length - 1; i >= 0; i--) {
        const r = ripples[i];
        r.radius += 5.5;
        r.alpha -= 0.02;
        if (r.alpha <= 0 || r.radius >= r.maxRadius) {
          ripples.splice(i, 1);
        }
      }

      // Draw dots
      const cols = Math.floor(width / currentSpacing);
      const rows = Math.floor(height / currentSpacing);
      const startX = (width - cols * currentSpacing) / 2;
      const startY = (height - rows * currentSpacing) / 2;

      for (let c = 0; c <= cols; c++) {
        for (let r = 0; r <= rows; r++) {
          const px = startX + c * currentSpacing;
          const py = startY + r * currentSpacing;

          // Distance from mouse
          const dx = px - mouseX;
          const dy = py - mouseY;
          const dist = Math.sqrt(dx * dx + dy * dy);

          let currentSize = dotSize;
          let currentAlpha = 0.22;
          let dotColor = '#14306B';

          // Proximity swell & glow
          if (!reduced && dist < 120) {
            const factor = 1 - dist / 120;
            currentSize = dotSize + factor * 2.8;
            currentAlpha = 0.22 + factor * 0.65;
            dotColor = glow ? '#07B3D1' : '#2F6BFF';
          }

          // Ripple effect
          if (!reduced) {
            for (const rip of ripples) {
              const rDist = Math.abs(Math.sqrt((px - rip.x) ** 2 + (py - rip.y) ** 2) - rip.radius);
              if (rDist < 30) {
                const rFactor = (1 - rDist / 30) * rip.alpha;
                currentSize += rFactor * 2.2;
                currentAlpha = Math.min(1.0, currentAlpha + rFactor * 0.5);
                dotColor = '#2F6BFF';
              }
            }
          }

          ctx.fillStyle = dotColor;
          ctx.globalAlpha = currentAlpha;
          ctx.beginPath();
          ctx.arc(px, py, currentSize, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      ctx.globalAlpha = 1.0;

      if (!reduced && isVisible) {
        animId = requestAnimationFrame(render);
      }
    };

    if (reduced || !isVisible) {
      render(window.performance.now());
    } else {
      animId = requestAnimationFrame(render);
    }

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', onResize);
      targetEl.removeEventListener('pointermove', onPointerMove as EventListener);
      targetEl.removeEventListener('click', onClick as EventListener);
    };
  }, [dotSize, spacing, glow, performanceTier, reduced, isVisible]);

  return (
    <canvas
      ref={canvasRef}
      className={`absolute inset-0 pointer-events-auto ${className}`}
      aria-hidden="true"
    />
  );
};
