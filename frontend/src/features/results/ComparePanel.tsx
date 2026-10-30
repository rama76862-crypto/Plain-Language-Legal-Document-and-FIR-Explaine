import {useEffect,useRef,useState} from 'react';
import { useSession } from '../../lib/session';
import { createDocument,getDocument,getExtraction,patchExtraction,deleteDocument } from '../../lib/api';
import { config } from '../../lib/config';
import type { Clause,DocumentCreateResponse } from '../../lib/types';
import { GlassCard,Button } from '../../design/primitives';

type Evidence={document_id:string;clause_id:string;quote:string;source_ref:{page_number:number|null;paragraph_index:number|null}};
type Comparison={unchanged_passages:number;changes:Array<{change_id:string;change_type:string;before:Evidence|null;after:Evidence|null;why_review:string}>;limitations:string[]};
export function ComparePanel({onNavigateEvidence}:{onNavigateEvidence:(id:string)=>void}) {
  const {documentId,sessionToken,revision,inputLanguage,documentType}=useSession();
  const [file,setFile]=useState<File|null>(null);const [consent,setConsent]=useState(false);const [reviewed,setReviewed]=useState(false);const [clauses,setClauses]=useState<Clause[]>([]);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [comparison,setComparison]=useState<Comparison|null>(null);
  const second=useRef<DocumentCreateResponse|null>(null);const abort=useRef<AbortController|null>(null);
  useEffect(()=>()=>{abort.current?.abort();const doc=second.current;if(doc)void deleteDocument(doc.document_id,doc.session_token).catch(()=>{});},[documentId]);
  async function extract() {
    if(!file||!consent)return;setBusy(true);setError('');setComparison(null);setReviewed(false);const controller=new AbortController();abort.current=controller;
    try {
      if(second.current){await deleteDocument(second.current.document_id,second.current.session_token);second.current=null;}
      const uploaded=await createDocument(file,inputLanguage==='unknown'?'auto':inputLanguage,documentType,controller.signal);second.current=uploaded;
      const deadline=Date.now()+120000;let ready=false;
      while(Date.now()<deadline){const meta=await getDocument(uploaded.document_id,uploaded.session_token,controller.signal);if(meta.extraction_ready){ready=true;break;}if(meta.status==='failed')throw new Error('Revised document extraction failed.');await new Promise(resolve=>setTimeout(resolve,700));if(controller.signal.aborted)return;}
      if(!ready)throw new Error('Extraction is not ready. Try again later.');
      const extracted=await getExtraction(uploaded.document_id,uploaded.session_token,controller.signal);if(!controller.signal.aborted)setClauses(extracted.clauses);
    }catch(e){if(!controller.signal.aborted)setError(e instanceof Error?e.message:'Extraction unavailable.');}finally{if(!controller.signal.aborted)setBusy(false);}
  }
  async function compare() {
    const b=second.current;if(!b||!reviewed||!documentId||!sessionToken)return;setBusy(true);setError('');
    try {
      const corrected=await patchExtraction(b.document_id,b.session_token,{expected_revision:b.revision,corrections:clauses.map(c=>({clause_id:c.clause_id,text:c.reviewed_text})),input_language:inputLanguage,document_type:documentType});b.revision=corrected.revision;
      const response=await fetch(`${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}/compare`,{method:'POST',headers:{'Content-Type':'application/json','X-Session-Token':sessionToken,'X-Compare-Session-Token':b.session_token},body:JSON.stringify({document_b_id:b.document_id,expected_revision_a:revision,expected_revision_b:corrected.revision})});const data=await response.json();if(!response.ok)throw new Error(data.error?.message??'Comparison unavailable.');setComparison(data);
    }catch(e){setError(e instanceof Error?e.message:'Comparison failed.');}finally{setBusy(false);}
  }
  return <div className="space-y-4"><GlassCard className="p-5 space-y-4"><h3 className="text-lg font-bold">Compare document versions</h3><p className="text-xs text-mute">The current reviewed document is version A. Upload and review version B to compare exact before/after passages. This detects wording differences; a human must assess their legal meaning.</p><input aria-label="Revised document" type="file" accept=".pdf,.docx" disabled={busy} onChange={e=>{setFile(e.target.files?.[0]??null);setComparison(null);setClauses([]);setReviewed(false);}}/><label className="flex gap-2 text-sm"><input type="checkbox" checked={consent} disabled={busy} onChange={e=>setConsent(e.target.checked)}/>I consent to temporary processing/storage of the revised document under this server's disclosed processing mode.</label><Button disabled={busy||!file||!consent} onClick={extract}>Extract revised document</Button>{error&&<p role="alert" className="text-error">{error}</p>}{busy&&<p role="status">Processing the actual request…</p>}{clauses.length>0&&<><div className="max-h-96 overflow-auto space-y-3">{clauses.map((c,i)=><label key={c.clause_id} className="block text-xs">Revised clause {i+1}<textarea className="block w-full p-3 rounded border border-line bg-paper text-ink" rows={4} maxLength={10000} disabled={busy} value={c.reviewed_text} onChange={e=>{setReviewed(false);setComparison(null);setClauses(all=>all.map(x=>x.clause_id===c.clause_id?{...x,reviewed_text:e.target.value}:x));}}/></label>)}</div><label className="flex gap-2 text-sm"><input type="checkbox" checked={reviewed} disabled={busy} onChange={e=>setReviewed(e.target.checked)}/>I checked the revised extraction against its original file.</label><Button disabled={busy||!reviewed} onClick={compare}>Compare reviewed versions</Button></>}</GlassCard>{comparison&&<GlassCard className="p-5 space-y-4"><h3 className="font-bold">{comparison.changes.length} source changes · {comparison.unchanged_passages} unchanged passages</h3>{comparison.changes.map(change=><div key={change.change_id} className="p-4 border border-line rounded space-y-3"><h4 className="font-semibold capitalize">{change.change_type}</h4><div className="grid md:grid-cols-2 gap-3">{(['before','after'] as const).map(side=><div key={side} className="p-3 bg-bg2 rounded"><strong>{side==='before'?'Before · A':'After · B'}</strong><blockquote className="text-sm whitespace-pre-wrap mt-2">{change[side]?.quote??'No matching source passage'}</blockquote>{change[side]&&<p className="text-xs mt-2">{change[side]!.clause_id} · {change[side]!.source_ref.page_number?`Page ${change[side]!.source_ref.page_number}`:`Paragraph ${change[side]!.source_ref.paragraph_index}`}</p>}{side==='before'&&change.before&&<Button size="sm" variant="secondary" onClick={()=>onNavigateEvidence(change.before!.clause_id)}>Open source A</Button>}</div>)}</div><p className="text-xs text-mute">{change.why_review}</p></div>)}{comparison.limitations.map(text=><p key={text} className="text-xs text-mute">{text}</p>)}</GlassCard>}</div>;
}
