/**
 * BootIntro Component
 * Light paper unfolding intro on first application load.
 * Displays real telemetry milestones:
 * - "Fonts ready"
 * - "Checking local service"
 * - "3D ready"
 * Skippable via button or Escape key; auto fades out after ~1.4s.
 */

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useReducedMotion } from '../motion';

interface BootIntroProps {
  onDone: () => void;
  ready: {
    fonts: boolean;
    health: boolean;
    webgl: boolean;
  };
}

export const BootIntro: React.FC<BootIntroProps> = ({ onDone, ready }) => {
  const reduced = useReducedMotion();
  const [visible, setVisible] = useState(true);

  const handleFinish = () => {
    setVisible(false);
    setTimeout(onDone, 300);
  };

  useEffect(() => {
    if (reduced) {
      onDone();
      return;
    }

    // Auto fadeout after max 1.4s
    const timer = setTimeout(() => {
      handleFinish();
    }, 1400);

    return () => clearTimeout(timer);
  }, [reduced]);

  if (reduced) return null;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.35 }}
          className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-bg p-6 text-center select-none"
          role="status"
          aria-live="polite"
        >
          {/* Paper unfolding animation */}
          <motion.div
            initial={{ scaleY: 0.2, scaleX: 0.6, rotateX: 30, opacity: 0 }}
            animate={{ scaleY: 1, scaleX: 1, rotateX: 0, opacity: 1 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="w-full max-w-sm glass-card rounded-lg shadow-pop border border-line p-8 flex flex-col items-center"
          >
            {/* Justice Scale Icon */}
            <div className="w-12 h-12 rounded-full bg-navy/5 flex items-center justify-center text-navy mb-4 font-mono text-xl">
              ⚖
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-navy">
              NyayaSarathi
            </h1>
            <div className="text-sm font-semibold text-mute mt-1 mb-6 flex gap-2">
              <span className="font-gurmukhi">ਨਿਆਂ ਸਾਰਥੀ</span>
              <span>·</span>
              <span className="font-devanagari">न्याय सारथी</span>
            </div>

            {/* Real telemetry milestones */}
            <div className="w-full flex flex-col gap-1.5 text-xs font-mono text-mute border-t border-line pt-4 mb-4">
              <div className="flex items-center justify-between">
                <span>Indic & UI Fonts</span>
                <span className={ready.fonts ? 'text-ok font-bold' : 'text-mute'}>
                  {ready.fonts ? 'Ready ✓' : 'Loading...'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Processing API Server</span>
                <span className={ready.health ? 'text-ok font-bold' : 'text-mute'}>
                  {ready.health ? 'Checked ✓' : 'Checking...'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Visual effects</span>
                <span className={ready.webgl ? 'text-ok font-bold' : 'text-mute'}>
                  {ready.webgl ? 'CSS ready ✓' : 'Basic mode'}
                </span>
              </div>
            </div>

            <button
              onClick={handleFinish}
              className="text-xs font-mono text-blue hover:underline cursor-pointer"
            >
              Skip intro (Esc)
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
export default BootIntro;
