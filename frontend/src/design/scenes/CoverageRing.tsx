/**
 * CoverageRing 3D Scene
 * Segmented ring visualizing clause analysis coverage:
 * - One segment per clause: filled = analysed; open/dimmed = skipped or needs review
 * - Visualizes COVERAGE ONLY (analysed / total), NEVER danger or risk score.
 */

import React, { useRef, useMemo, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { isWebGLAvailable } from '../webglUtils';
import { useReducedMotion } from '../motion';

interface CoverageRingProps {
  analysed: number;
  total: number;
  className?: string;
}

function Ring3D({ analysed, total }: { analysed: number; total: number }) {
  const groupRef = useRef<THREE.Group | null>(null);

  const segments = useMemo(() => {
    const count = Math.max(1, total);
    const segs = [];
    const radius = 1.6;
    const gap = 0.08;
    const segAngle = (Math.PI * 2) / count - gap;

    for (let i = 0; i < count; i++) {
      const isAnalysed = i < analysed;
      const startAngle = i * ((Math.PI * 2) / count) + gap / 2;

      // Arc geometry
      const shape = new THREE.Shape();
      shape.absarc(0, 0, radius + 0.18, startAngle, startAngle + segAngle, false);
      shape.absarc(0, 0, radius - 0.18, startAngle + segAngle, startAngle, true);

      const geom = new THREE.ExtrudeGeometry(shape, {
        depth: 0.12,
        bevelEnabled: false,
      });

      segs.push({
        geom,
        color: isAnalysed ? '#12A26A' : '#EAF0FC',
        emissive: isAnalysed ? '#12A26A' : '#000000',
      });
    }
    return segs;
  }, [analysed, total]);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.z += delta * 0.2;
    }
  });

  return (
    <group ref={groupRef} rotation={[0.4, 0.2, 0]}>
      {segments.map((s, idx) => (
        <mesh key={idx} geometry={s.geom}>
          <meshStandardMaterial
            color={s.color}
            emissive={s.emissive}
            emissiveIntensity={0.3}
            roughness={0.3}
            metalness={0.2}
          />
        </mesh>
      ))}
    </group>
  );
}

function CssFallback({ analysed, total }: { analysed: number; total: number }) {
  const pct = Math.round((analysed / Math.max(1, total)) * 100);
  return (
    <div
      className="relative w-40 h-40 flex flex-col items-center justify-center rounded-full border-8 border-ok/20 bg-paper shadow-card"
      aria-hidden="true"
    >
      <div className="font-mono text-2xl font-bold text-navy">{pct}%</div>
      <div className="text-[11px] font-mono text-mute uppercase tracking-wider">Coverage</div>
    </div>
  );
}

export const CoverageRing: React.FC<CoverageRingProps> = ({
  analysed,
  total,
  className = '',
}) => {
  const reduced = useReducedMotion();
  const webglOk = isWebGLAvailable();

  if (reduced || !webglOk) {
    return <CssFallback analysed={analysed} total={total} />;
  }

  return (
    <div className={`relative w-44 h-44 flex items-center justify-center ${className}`} aria-hidden="true">
      <Suspense fallback={<CssFallback analysed={analysed} total={total} />}>
        <Canvas
          camera={{ position: [0, 0, 4.2], fov: 45 }}
          dpr={[1, 1.5]}
          gl={{ antialias: true, alpha: true }}
        >
          <ambientLight intensity={0.9} />
          <directionalLight position={[2, 3, 2]} intensity={1.2} />
          <Ring3D analysed={analysed} total={total} />
        </Canvas>
      </Suspense>
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span className="font-mono text-xl font-bold text-navy">
          {analysed}/{total}
        </span>
        <span className="text-[10px] font-mono uppercase text-mute tracking-wider">
          Clauses
        </span>
      </div>
    </div>
  );
};
export default CoverageRing;
