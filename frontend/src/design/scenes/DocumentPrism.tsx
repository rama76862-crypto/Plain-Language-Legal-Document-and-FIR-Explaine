import React, { useRef } from 'react';

interface DocumentPrismProps {
  className?: string;
}

export const DocumentPrism: React.FC<DocumentPrismProps> = ({ className = '' }) => {
  const stageRef = useRef<HTMLDivElement | null>(null);
  const sceneRef = useRef<HTMLDivElement | null>(null);

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!stageRef.current || !sceneRef.current) return;
    const r = stageRef.current.getBoundingClientRect();
    const ry = ((e.clientX - r.left) / r.width - 0.5) * 40;
    const rx = (0.5 - (e.clientY - r.top) / r.height) * 26;
    sceneRef.current.style.setProperty('--ry', `${ry}deg`);
    sceneRef.current.style.setProperty('--rx', `${rx}deg`);
  };

  const handlePointerLeave = () => {
    if (!sceneRef.current) return;
    sceneRef.current.style.setProperty('--ry', '-16deg');
    sceneRef.current.style.setProperty('--rx', '8deg');
  };

  return (
    <div
      ref={stageRef}
      className={`stage ${className}`}
      id="stage"
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      aria-hidden="true"
    >
      <div ref={sceneRef} className="scene" id="scene">
        <div className="sheet s0" />
        <div className="sheet s1" />
        <div className="sheet s2">
          <div className="beam" />
          <h4>RENT AGREEMENT · PAGE 2</h4>
          <div className="ln" style={{ width: '92%' }} />
          <div className="ln" style={{ width: '70%' }} />
          <div className="hl r">3% weekly penalty on late rent</div>
          <div className="ln" style={{ width: '85%' }} />
          <div className="hl a">Auto-renews unless 60 days’ notice</div>
          <div className="ln" style={{ width: '78%' }} />
          <div className="ln" style={{ width: '55%' }} />
          <div className="hl c">Deposit due back in 30 days</div>
          <div className="ln" style={{ width: '88%' }} />
        </div>
        <div className="chip r">⚠ Potential concern</div>
        <div className="chip a">🔁 Auto-renewal</div>
        <div className="chip c">⏱ Deadline found</div>
        <div className="shield">🛡</div>
      </div>
    </div>
  );
};

export default DocumentPrism;
