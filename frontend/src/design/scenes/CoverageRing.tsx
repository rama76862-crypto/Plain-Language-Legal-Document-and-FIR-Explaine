/** Lightweight coverage only; no WebGL context or continuous GPU render loop. */
import React from 'react';
interface CoverageRingProps { analysed:number; total:number; className?:string }
export const CoverageRing:React.FC<CoverageRingProps>=({analysed,total,className=''})=>{
 const count=Math.max(0,total);
 const completed=Math.max(0,Math.min(analysed,count));
 const circumference=2*Math.PI*62;
 const fraction=count?completed/count:0;
 return <div className={'relative w-44 h-44 flex items-center justify-center '+className} role="img" aria-label={completed+' of '+count+' clauses analysed. Coverage is not an accuracy or safety score.'}>
  <svg viewBox="0 0 160 160" className="absolute inset-0 w-full h-full" aria-hidden="true">
   <circle cx="80" cy="80" r="62" fill="none" stroke="#e2e8f0" strokeWidth="12"/>
   <circle cx="80" cy="80" r="62" fill="none" stroke="#12a26a" strokeWidth="12" strokeDasharray={fraction*circumference+' '+circumference} transform="rotate(-90 80 80)"/>
  </svg>
  <div className="text-center"><span className="font-mono text-xl font-bold text-navy">{completed}/{count}</span><p className="text-xs text-mute">Clauses analysed</p></div>
 </div>;
};
export default CoverageRing;
