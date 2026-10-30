/**
 * PipelineStage 3D Rail Scene
 * 5 Stops: 1. Upload -> 2. Read & OCR -> 3. Review -> 4. Explain -> 5. Ask
 * Displays glowing node track with interactive selection and CSS fallback.
 */

import React, { useRef, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { isWebGLAvailable } from '../webglUtils';
import { useReducedMotion } from '../motion';

interface PipelineStageProps {
  activeStep?: number; // 0 to 4
  onStepSelect?: (step: number) => void;
  className?: string;
}

const STAGES = [
  { id: 0, title: 'Upload', sub: 'PDF or DOCX' },
  { id: 1, title: 'Read & OCR', sub: 'Local parsing' },
  { id: 2, title: 'Review', sub: 'Human-in-the-loop' },
  { id: 3, title: 'Explain', sub: 'Clause by clause' },
  { id: 4, title: 'Ask', sub: 'Grounded Q&A' },
];

function Rail3D({ activeStep = 0 }: { activeStep: number }) {
  const groupRef = useRef<THREE.Group | null>(null);

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.8) * 0.05;
    }
  });

  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      {/* Connecting guide rail */}
      <mesh position={[0, 0, -0.05]}>
        <boxGeometry args={[4.4, 0.06, 0.04]} />
        <meshStandardMaterial color="#586489" roughness={0.3} metalness={0.5} />
      </mesh>

      {/* 5 Stage Node Orbs */}
      {[-2, -1, 0, 1, 2].map((x, idx) => {
        const isActive = idx === activeStep;
        const isPast = idx < activeStep;
        return (
          <group key={idx} position={[x * 1.0, 0, 0]}>
            <mesh>
              <sphereGeometry args={[isActive ? 0.22 : 0.14, 24, 24]} />
              <meshStandardMaterial
                color={isActive ? '#07B3D1' : isPast ? '#2F6BFF' : '#586489'}
                emissive={isActive ? '#07B3D1' : isPast ? '#2F6BFF' : '#000000'}
                emissiveIntensity={isActive ? 0.8 : isPast ? 0.3 : 0}
                roughness={0.2}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

function CssFallback({ activeStep, onStepSelect }: { activeStep: number; onStepSelect?: (s: number) => void }) {
  return (
    <div className="w-full flex items-center justify-between relative px-6 py-4" aria-hidden="true">
      <div className="absolute left-10 right-10 top-1/2 -translate-y-1/2 h-[3px] bg-line z-0" />
      {STAGES.map((s, idx) => {
        const isActive = idx === activeStep;
        const isPast = idx < activeStep;
        return (
          <button
            key={s.id}
            type="button"
            onClick={() => onStepSelect?.(idx)}
            className="relative z-10 flex flex-col items-center group cursor-pointer focus:outline-none"
          >
            <div
              className={`w-9 h-9 rounded-full flex items-center justify-center font-mono text-xs font-bold transition-all shadow-sm ${
                isActive
                  ? 'bg-cyan text-navy ring-4 ring-cyan/30 scale-110'
                  : isPast
                  ? 'bg-blue text-white'
                  : 'bg-paper text-mute border border-line'
              }`}
            >
              {idx + 1}
            </div>
            <div
              className={`mt-2 text-xs font-semibold ${
                isActive ? 'text-navy font-bold' : isPast ? 'text-blue' : 'text-mute'
              }`}
            >
              {s.title}
            </div>
            <div className="text-[10px] text-mute font-mono">{s.sub}</div>
          </button>
        );
      })}
    </div>
  );
}

export const PipelineStage: React.FC<PipelineStageProps> = ({
  activeStep = 0,
  onStepSelect,
  className = '',
}) => {
  const reduced = useReducedMotion();
  const webglOk = isWebGLAvailable();

  if (reduced || !webglOk) {
    return <CssFallback activeStep={activeStep} onStepSelect={onStepSelect} />;
  }

  return (
    <div className={`relative w-full ${className}`}>
      <div className="h-[140px] w-full" aria-hidden="true">
        <Suspense fallback={<div className="h-full" />}>
          <Canvas
            camera={{ position: [0, 0, 3.8], fov: 45 }}
            dpr={[1, 1.5]}
            gl={{ antialias: true, alpha: true }}
          >
            <ambientLight intensity={0.9} />
            <directionalLight position={[2, 3, 2]} intensity={1.2} />
            <Rail3D activeStep={activeStep} />
          </Canvas>
        </Suspense>
      </div>
      <div className="flex justify-between px-6 -mt-2">
        {STAGES.map((s, idx) => (
          <button
            key={s.id}
            type="button"
            onClick={() => onStepSelect?.(idx)}
            className="flex flex-col items-center text-center cursor-pointer hover:opacity-80 transition-opacity"
          >
            <span
              className={`text-xs font-bold ${
                idx === activeStep ? 'text-cyan' : idx < activeStep ? 'text-blue' : 'text-mute'
              }`}
            >
              {s.title}
            </span>
            <span className="text-[10px] text-mute font-mono">{s.sub}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
export default PipelineStage;
