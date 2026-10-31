/**
 * PipelineStage 3D Scene
 * High-fidelity 5-stage interactive pipeline:
 * 1. Upload -> 2. Read & OCR -> 3. Review -> 4. Explain -> 5. Ask
 * Elevated frosted glass pedestals, traveling energy conduit,
 * animated neon aura rings, and interactive 3D picking.
 */

import React, { useRef, useState, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { RoundedBox } from '@react-three/drei';
import * as THREE from 'three';
import { isWebGLAvailable } from '../webglUtils';
import { useReducedMotion } from '../motion';
import { useT } from '../../lib/i18n';

interface PipelineStageProps {
  activeStep?: number; // 0 to 4
  onStepSelect?: (step: number) => void;
  className?: string;
}

const STAGES = [
  {
    id: 0,
    title: 'Upload',
    sub: 'PDF or DOCX',
    description: 'In-memory client ingestion with instant file type, size, and page validation.',
  },
  {
    id: 1,
    title: 'Read & OCR',
    sub: 'Local parsing',
    description: 'Local deterministic text extraction & offline Tesseract OCR for scanned copies.',
  },
  {
    id: 2,
    title: 'Review',
    sub: 'Human-in-the-loop',
    description: 'Compare extracted clauses with source view and correct misread words.',
  },
  {
    id: 3,
    title: 'Explain',
    sub: 'Clause by clause',
    description: 'Plain-language explanations in English, Hindi, or Punjabi with attention cues.',
  },
  {
    id: 4,
    title: 'Ask',
    sub: 'Grounded Q&A',
    description: 'Interactive questions backed by verbatim quotes and verified citations.',
  },
];

/**
 * Individual Interactive 3D Stage Pedestal
 */
function StagePedestal({
  index,
  isActive,
  isPast,
  isHovered,
  onSelect,
}: {
  index: number;
  isActive: boolean;
  isPast: boolean;
  isHovered: boolean;
  onSelect: () => void;
}) {
  const groupRef = useRef<THREE.Group | null>(null);
  const ringRef = useRef<THREE.Mesh | null>(null);
  const beaconRef = useRef<THREE.Mesh | null>(null);

  const xPos = (index - 2) * 1.02;

  useFrame((state) => {
    const t = state.clock.getElapsedTime();

    if (groupRef.current) {
      const targetY = isActive ? 0.22 : isHovered ? 0.1 : 0;
      groupRef.current.position.y = THREE.MathUtils.lerp(
        groupRef.current.position.y,
        targetY + (isActive ? Math.sin(t * 2 + index) * 0.03 : 0),
        0.1
      );
    }

    if (ringRef.current && isActive) {
      ringRef.current.rotation.z = t * 1.4;
    }

    if (beaconRef.current) {
      beaconRef.current.rotation.y = t * 0.8 + index;
    }
  });

  const baseColor = isActive ? '#07B3D1' : isPast ? '#2F6BFF' : '#586489';
  const emissiveColor = isActive ? '#00FFFF' : isPast ? '#2F6BFF' : '#0E1A3D';
  const emissiveIntensity = isActive ? 1.4 : isPast ? 0.5 : 0.05;

  return (
    <group
      ref={groupRef}
      position={[xPos, 0, 0]}
      onClick={(e) => {
        e.stopPropagation();
        onSelect();
      }}
    >
      {/* 1. Frosted Glass Pedestal Base */}
      <RoundedBox args={[0.72, 0.14, 0.72]} radius={0.05} smoothness={4}>
        <meshPhysicalMaterial
          color="#FFFFFF"
          roughness={0.12}
          metalness={0.1}
          transmission={0.7}
          thickness={0.4}
          transparent
          opacity={0.92}
        />
      </RoundedBox>

      {/* 2. Illuminated Inner Neon Ring */}
      <mesh position={[0, 0.072, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.18, 0.26, 32]} />
        <meshStandardMaterial
          color={baseColor}
          emissive={emissiveColor}
          emissiveIntensity={emissiveIntensity}
          roughness={0.1}
        />
      </mesh>

      {/* 3. Floating 3D Crystal Beacon */}
      <mesh
        ref={beaconRef}
        position={[0, isActive ? 0.42 : 0.28, 0]}
      >
        <octahedronGeometry args={[isActive ? 0.15 : 0.11, 0]} />
        <meshStandardMaterial
          color={baseColor}
          emissive={emissiveColor}
          emissiveIntensity={emissiveIntensity * 1.2}
          roughness={0.15}
          metalness={0.8}
        />
      </mesh>

      {/* 4. Active Rotating Energy Ring */}
      {isActive && (
        <mesh ref={ringRef} position={[0, 0.22, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <torusGeometry args={[0.38, 0.016, 16, 32]} />
          <meshBasicMaterial color="#00FFFF" transparent opacity={0.8} />
        </mesh>
      )}

      {/* Point light over active or hovered pedestal */}
      {(isActive || isHovered) && (
        <pointLight
          position={[0, 0.45, 0]}
          color={isActive ? '#00FFFF' : '#2F6BFF'}
          intensity={isActive ? 1.6 : 0.7}
          distance={1.6}
        />
      )}
    </group>
  );
}

/**
 * Connecting Glowing Laser Conduit Track
 */
function LaserConduitRail({ activeStep }: { activeStep: number }) {
  const pulseRef = useRef<THREE.Mesh | null>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (pulseRef.current) {
      const targetX = Math.max(-2.04, (activeStep - 2) * 1.02);
      const span = Math.max(0.5, targetX + 2.04);
      const progress = (t * 0.9) % 1;
      pulseRef.current.position.x = -2.04 + progress * span;
    }
  });

  return (
    <group position={[0, -0.04, 0]}>
      {/* Structural Metallic Track */}
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[4.4, 0.025, 0.04]} />
        <meshStandardMaterial color="#CBD5E1" roughness={0.3} metalness={0.6} />
      </mesh>

      {/* Illuminated Laser Guide Line */}
      <mesh position={[0, 0.018, 0]}>
        <boxGeometry args={[4.4, 0.012, 0.02]} />
        <meshStandardMaterial
          color="#07B3D1"
          emissive="#07B3D1"
          emissiveIntensity={0.8}
        />
      </mesh>

      {/* Traveling Energy Pulse Dot */}
      <mesh ref={pulseRef} position={[0, 0.025, 0]}>
        <sphereGeometry args={[0.06, 16, 16]} />
        <meshBasicMaterial color="#00FFFF" />
      </mesh>
    </group>
  );
}

/**
 * 3D Scene Container
 */
function PipelineRailScene({
  activeStep,
  onStepSelect,
  hoveredStep,
  setHoveredStep,
}: {
  activeStep: number;
  onStepSelect?: (s: number) => void;
  hoveredStep: number | null;
  setHoveredStep: (s: number | null) => void;
}) {
  const groupRef = useRef<THREE.Group | null>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (groupRef.current) {
      groupRef.current.rotation.x = 0.28 + Math.sin(t * 0.35) * 0.02;
    }
  });

  return (
    <group ref={groupRef} position={[0, -0.06, 0]}>
      {/* Ground Shadow */}
      <mesh position={[0, -0.32, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[4.8, 1.6]} />
        <meshBasicMaterial color="#14306B" transparent opacity={0.05} />
      </mesh>

      {/* Connecting Laser Conduit */}
      <LaserConduitRail activeStep={activeStep} />

      {/* 5 Illuminated Stage Pedestals */}
      {STAGES.map((s, idx) => (
        <group
          key={s.id}
          onPointerOver={() => setHoveredStep(idx)}
          onPointerOut={() => setHoveredStep(null)}
        >
          <StagePedestal
            index={idx}
            isActive={idx === activeStep}
            isPast={idx < activeStep}
            isHovered={hoveredStep === idx}
            onSelect={() => onStepSelect?.(idx)}
          />
        </group>
      ))}
    </group>
  );
}

/**
 * Accessible CSS Fallback
 */
function CssPipelineFallback({
  stages,
  activeStep,
  onStepSelect,
}: {
  stages: { id: number; title: string; sub: string; description: string }[];
  activeStep: number;
  onStepSelect?: (s: number) => void;
}) {
  return (
    <div className="w-full flex items-center justify-between relative px-4 py-5" aria-hidden="true">
      <div className="absolute left-8 right-8 top-1/2 -translate-y-1/2 h-[3px] bg-line z-0" />
      {stages.map((s, idx) => {
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
              className={`w-9 h-9 rounded-full flex items-center justify-center font-mono text-xs font-bold transition-all shadow-md ${
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
  activeStep: controlledStep,
  onStepSelect,
  className = '',
}) => {
  const { t } = useT();
  const reduced = useReducedMotion();
  const webglOk = isWebGLAvailable();
  const [internalStep, setInternalStep] = useState(0);
  const [hoveredStep, setHoveredStep] = useState<number | null>(null);

  const activeStep = controlledStep !== undefined ? controlledStep : internalStep;
  const handleSelect = (idx: number) => {
    if (controlledStep === undefined) {
      setInternalStep(idx);
    }
    onStepSelect?.(idx);
  };

  const localizedStages = [
    {
      id: 0,
      title: t('pipelineStage.step1Title'),
      sub: t('pipelineStage.step1Sub'),
      description: t('pipelineStage.step1Desc'),
    },
    {
      id: 1,
      title: t('pipelineStage.step2Title'),
      sub: t('pipelineStage.step2Sub'),
      description: t('pipelineStage.step2Desc'),
    },
    {
      id: 2,
      title: t('pipelineStage.step3Title'),
      sub: t('pipelineStage.step3Sub'),
      description: t('pipelineStage.step3Desc'),
    },
    {
      id: 3,
      title: t('pipelineStage.step4Title'),
      sub: t('pipelineStage.step4Sub'),
      description: t('pipelineStage.step4Desc'),
    },
    {
      id: 4,
      title: t('pipelineStage.step5Title'),
      sub: t('pipelineStage.step5Sub'),
      description: t('pipelineStage.step5Desc'),
    },
  ];

  const selectedStage = localizedStages[activeStep] || localizedStages[0];

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 3D Rail Canvas */}
      <div className="h-[180px] w-full select-none cursor-pointer" aria-hidden="true">
        {reduced || !webglOk ? (
          <CssPipelineFallback stages={localizedStages} activeStep={activeStep} onStepSelect={handleSelect} />
        ) : (
          <Suspense fallback={<CssPipelineFallback stages={localizedStages} activeStep={activeStep} onStepSelect={handleSelect} />}>
            <Canvas
              camera={{ position: [0, 0.9, 3.8], fov: 36 }}
              dpr={[1, 1.5]}
              gl={{ antialias: true, alpha: true }}
            >
              <ambientLight intensity={0.95} />
              <directionalLight position={[4, 5, 4]} intensity={1.5} />
              <directionalLight position={[-4, -2, 2]} intensity={0.8} color="#07B3D1" />
              <PipelineRailScene
                activeStep={activeStep}
                onStepSelect={handleSelect}
                hoveredStep={hoveredStep}
                setHoveredStep={setHoveredStep}
              />
            </Canvas>
          </Suspense>
        )}
      </div>

      {/* Unified Stage Control Strip & Description */}
      <div className="p-4 rounded-xl bg-paper/95 border border-line shadow-sm space-y-3">
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {localizedStages.map((s, idx) => {
            const isActive = idx === activeStep;
            const isPast = idx < activeStep;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => handleSelect(idx)}
                className={`p-2.5 rounded-lg border text-left transition-all ${
                  isActive
                    ? 'bg-cyan/10 border-cyan text-navy font-bold ring-2 ring-cyan/20'
                    : isPast
                    ? 'bg-bg2/40 border-line text-navy/80 hover:border-blue/40'
                    : 'bg-transparent border-transparent text-mute hover:bg-bg2/20'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] font-bold text-mute">
                    0{idx + 1}
                  </span>
                  <span
                    className={`w-2 h-2 rounded-full ${
                      isActive ? 'bg-cyan animate-pulse' : isPast ? 'bg-blue' : 'bg-line'
                    }`}
                  />
                </div>
                <div className="text-xs font-semibold mt-0.5 truncate">{s.title}</div>
                <div className="text-[10px] text-mute font-mono truncate">{s.sub}</div>
              </button>
            );
          })}
        </div>

        {/* Selected Stage Detail */}
        <div className="pt-2 border-t border-line/60 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan/15 text-cyan uppercase shrink-0">
              {t('pipelineStage.stageBadge', { num: activeStep + 1 })}
            </span>
            <span className="text-xs text-navy font-medium leading-relaxed">
              {selectedStage.description}
            </span>
          </div>
          <span className="text-[10px] font-mono text-mute shrink-0">
            {t('pipelineStage.interactiveStages')}
          </span>
        </div>
      </div>
    </div>
  );
};

export default PipelineStage;
