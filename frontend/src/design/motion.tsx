/**
 * Motion utilities, hooks, and reveal components
 * Honoring accessibility (prefers-reduced-motion) and performance (tab visibility).
 */

import React, { useState, useEffect, useRef, useSyncExternalStore } from 'react';
import { motion, useReducedMotion as framerReducedMotion } from 'framer-motion';

export function useReducedMotion(): boolean {
  const isReduced = framerReducedMotion();
  return Boolean(isReduced);
}

export function usePageVisible(): boolean {
  return useSyncExternalStore(
    (callback) => {
      document.addEventListener('visibilitychange', callback);
      return () => document.removeEventListener('visibilitychange', callback);
    },
    () => !document.hidden,
    () => true
  );
}

export function usePointerParallax(intensity = 0.05) {
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const reduced = useReducedMotion();

  useEffect(() => {
    if (reduced) return;

    let rafId: number;
    const handlePointerMove = (e: PointerEvent) => {
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        const cx = window.innerWidth / 2;
        const cy = window.innerHeight / 2;
        const dx = (e.clientX - cx) * intensity;
        const dy = (e.clientY - cy) * intensity;
        setOffset({ x: dx, y: dy });
      });
    };

    window.addEventListener('pointermove', handlePointerMove, { passive: true });
    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      cancelAnimationFrame(rafId);
    };
  }, [intensity, reduced]);

  return offset;
}

export function useInViewOnce(threshold = 0.1) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [isInView, setIsInView] = useState(false);

  useEffect(() => {
    if (!ref.current || isInView) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      { threshold }
    );

    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [isInView, threshold]);

  return { ref, isInView };
}

interface RevealProps {
  children: React.ReactNode;
  delay?: number;
  direction?: 'up' | 'down' | 'left' | 'right' | 'none';
  className?: string;
}

export const Reveal: React.FC<RevealProps> = ({
  children,
  delay = 0,
  direction = 'up',
  className = '',
}) => {
  const reduced = useReducedMotion();
  const { ref, isInView } = useInViewOnce(0.15);

  if (reduced) {
    return <div className={className}>{children}</div>;
  }

  const offset = 28;
  const initialVariants = {
    up: { opacity: 0, y: offset },
    down: { opacity: 0, y: -offset },
    left: { opacity: 0, x: offset },
    right: { opacity: 0, x: -offset },
    none: { opacity: 0 },
  };

  return (
    <div ref={ref} className={className}>
      <motion.div
        initial={initialVariants[direction]}
        animate={isInView ? { opacity: 1, x: 0, y: 0 } : initialVariants[direction]}
        transition={{ duration: 0.65, ease: [0.16, 1, 0.3, 1], delay }}
      >
        {children}
      </motion.div>
    </div>
  );
};
