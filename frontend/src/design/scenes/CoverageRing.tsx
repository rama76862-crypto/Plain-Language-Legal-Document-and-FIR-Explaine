/**
 * CoverageRing Component
 * High-fidelity 3D perspective segmented gauge indicating document clause coverage.
 * Features separate depth layers, undistorted central typography,
 * illuminated neon arc, laser-cut segment tick marks, and pointer tilt.
 * Shows COVERAGE only, never danger or risk scores.
 */

import React, { useState } from 'react';
import { useReducedMotion } from '../motion';

interface CoverageRingProps {
  analysed: number;
  total: number;
  className?: string;
}

export const CoverageRing: React.FC<CoverageRingProps> = ({
  analysed,
  total,
  className = '',
}) => {
  const reduced = useReducedMotion();
  const [tilt, setTilt] = useState({ x: 0, y: 0 });

  const count = Math.max(0, total);
  const completed = Math.max(0, Math.min(analysed, count));
  const radius = 64;
  const strokeWidth = 10;
  const circumference = 2 * Math.PI * radius;
  const fraction = count > 0 ? completed / count : 0;
  const strokeDashoffset = circumference - fraction * circumference;

  // Segment markers count (capped at 32 for visual elegance)
  const segmentsCount = count > 0 ? Math.min(count, 32) : 12;
  const segmentAngle = 360 / segmentsCount;

  // Lead glowing dot position
  const leadAngle = fraction * 360 - 90;
  const leadRad = (leadAngle * Math.PI) / 180;
  const leadX = 85 + radius * Math.cos(leadRad);
  const leadY = 85 + radius * Math.sin(leadRad);

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (reduced) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    const y = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
    setTilt({ x: x * 8, y: y * 8 });
  };

  const handlePointerLeave = () => {
    setTilt({ x: 0, y: 0 });
  };

  return (
    <div
      className={`relative w-52 h-52 flex items-center justify-center select-none cursor-default ${className}`}
      role="img"
      aria-label={`${completed} of ${count} clauses analysed. Coverage is not an accuracy or safety score.`}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
    >
      {/* 3D Perspective Stage */}
      <div
        className="relative w-48 h-48 flex items-center justify-center [perspective:1000px]"
        style={{ transformStyle: 'preserve-3d' }}
      >
        {/* Depth Layer 1: Dial & Arc with 3D Tilt */}
        <div
          className="relative w-44 h-44 transition-transform duration-300 ease-out"
          style={{
            transform: reduced
              ? 'none'
              : `rotateX(${10 - tilt.y}deg) rotateY(${tilt.x}deg) translateZ(0px)`,
            transformStyle: 'preserve-3d',
          }}
        >
          {/* Subtle Outer Dial Shadow */}
          <div className="absolute inset-0 rounded-full bg-gradient-to-b from-transparent to-navy/5 shadow-card pointer-events-none" />

          <svg
            viewBox="0 0 170 170"
            className="w-full h-full drop-shadow-sm overflow-visible"
            aria-hidden="true"
          >
            <defs>
              <linearGradient id="coverage3dGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#07B3D1" />
                <stop offset="50%" stopColor="#2F6BFF" />
                <stop offset="100%" stopColor="#12A26A" />
              </linearGradient>
              <filter id="glow3d" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Background Track with Inner Bevel */}
            <circle
              cx="85"
              cy="85"
              r={radius}
              fill="none"
              stroke="#E2E8F0"
              strokeWidth={strokeWidth}
              className="opacity-60"
            />

            {/* Filled Active Arc with Smooth Dashoffset */}
            <circle
              cx="85"
              cy="85"
              r={radius}
              fill="none"
              stroke="url(#coverage3dGrad)"
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              transform="rotate(-90 85 85)"
              style={{
                transition: reduced ? 'none' : 'stroke-dashoffset 0.8s cubic-bezier(0.16, 1, 0.3, 1)',
              }}
            />

            {/* Segment Ticks */}
            {Array.from({ length: segmentsCount }).map((_, idx) => {
              const angle = idx * segmentAngle - 90;
              const rad = (angle * Math.PI) / 180;
              const x1 = 85 + (radius - strokeWidth / 2 - 1) * Math.cos(rad);
              const y1 = 85 + (radius - strokeWidth / 2 - 1) * Math.sin(rad);
              const x2 = 85 + (radius + strokeWidth / 2 + 1) * Math.cos(rad);
              const y2 = 85 + (radius + strokeWidth / 2 + 1) * Math.sin(rad);
              const isFilled = idx / segmentsCount < fraction;

              return (
                <line
                  key={idx}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke="#FFFFFF"
                  strokeWidth="2.5"
                  className={isFilled ? 'opacity-95' : 'opacity-40'}
                />
              );
            })}

            {/* Lead Glowing Energy Orb */}
            {fraction > 0.02 && fraction < 0.99 && (
              <g filter="url(#glow3d)">
                <circle cx={leadX} cy={leadY} r="4.5" fill="#00FFFF" />
                <circle cx={leadX} cy={leadY} r="7" fill="#07B3D1" opacity="0.4" />
              </g>
            )}
          </svg>
        </div>

        {/* Depth Layer 2: Undistorted Elevated Central Typography */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center text-center p-4 pointer-events-none transition-transform duration-300 ease-out"
          style={{
            transform: reduced
              ? 'none'
              : `rotateX(${-tilt.y * 0.4}deg) rotateY(${tilt.x * 0.4}deg) translateZ(28px)`,
          }}
        >
          <div className="w-24 h-24 rounded-full bg-paper/90 backdrop-blur-md border border-line shadow-card flex flex-col items-center justify-center p-2">
            <span className="font-mono text-2xl font-extrabold text-navy tracking-tight leading-none">
              {completed}
              <span className="text-mute text-sm font-normal">/{count}</span>
            </span>
            <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-navy mt-1">
              Clauses Analysed
            </span>
            <span className="text-[8px] font-mono text-mute">
              Coverage only
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CoverageRing;
