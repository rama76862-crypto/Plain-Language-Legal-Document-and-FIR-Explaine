import { useEffect, useState } from "react";
import { useSession } from "../../lib/session";
import { useResult } from "./ResultContext";
import { config } from "../../lib/config";
import { GlassCard, Button } from "../../design/primitives";

type Pack = {
  checklist: Array<{
    id: string;
    statement: string;
    party: string;
    due_or_trigger: string[];
    clause_id: string;
  }>;
  lawyer_questions: Array<{ question: string; clause_ids: string[] }>;
  limitations: string[];
};
export function ActionPackPanel({
  onNavigateEvidence,
}: {
  onNavigateEvidence: (id: string) => void;
}) {
  const { documentId, sessionToken } = useSession();
  const { result } = useResult();
  const [pack, setPack] = useState<Pack | null>(null);
  const [error, setError] = useState("");
  const [checked, setChecked] = useState<Set<string>>(new Set());
  useEffect(() => {
    const controller = new AbortController();
    setPack(null);
    setError("");
    setChecked(new Set());
    if (documentId && sessionToken && result)
      fetch(
        `${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}/analyses/${encodeURIComponent(result.analysis_id)}/action-pack`,
        {
          headers: { "X-Session-Token": sessionToken },
          signal: controller.signal,
          cache: "no-store",
        },
      )
        .then(async (r) => {
          const data = await r.json();
          if (!r.ok)
            throw new Error(data.error?.message ?? "Action Pack unavailable.");
          return data;
        })
        .then((data) => {
          if (!controller.signal.aborted) setPack(data);
        })
        .catch((e) => {
          if (!controller.signal.aborted) setError(e.message);
        });
    return () => controller.abort();
  }, [documentId, sessionToken, result?.analysis_id]);
  return (
    <div className="space-y-4">
      <GlassCard className="p-5 space-y-3">
        <h3 className="text-lg font-bold">Action Pack</h3>
        <p className="text-xs text-mute">
          A source obligation checklist and questions to discuss with legal aid.
          Checking a box records your review, not legal compliance.
        </p>
        {error && <p role="alert">{error}</p>}
        {!pack && !error && (
          <p role="status">Loading source-linked checklist…</p>
        )}
        {pack?.checklist.length === 0 && (
          <p>
            No explicit obligation wording was found by this check. Read every
            clause.
          </p>
        )}
        {pack?.checklist.map((item) => (
          <div
            key={item.id}
            className="p-4 border border-line rounded-lg space-y-2"
          >
            <label className="flex gap-3 text-sm">
              <input
                type="checkbox"
                checked={checked.has(item.id)}
                onChange={(e) =>
                  setChecked((previous) => {
                    const next = new Set(previous);
                    if (e.target.checked) next.add(item.id);
                    else next.delete(item.id);
                    return next;
                  })
                }
              />
              <span>{item.statement}</span>
            </label>
            <p className="text-xs text-mute">
              Role words detected:{" "}
              {item.party === "not_detected"
                ? "No role identified by the rule check"
                : item.party}
            </p>
            {item.due_or_trigger.map((text) => (
              <p key={text} className="text-xs">
                Stated period / trigger: {text}
              </p>
            ))}
            <Button
              size="sm"
              variant="secondary"
              onClick={() => onNavigateEvidence(item.clause_id)}
            >
              View original evidence
            </Button>
          </div>
        ))}
      </GlassCard>
      <GlassCard className="p-5 space-y-3">
        <h3 className="font-bold">Questions for a legal professional</h3>
        {pack?.lawyer_questions.map((item, i) => (
          <div key={i} className="space-y-2 border-b border-line pb-3">
            <p className="text-sm">{item.question}</p>
            {item.clause_ids.map((id) => (
              <Button
                key={id}
                size="sm"
                variant="secondary"
                onClick={() => onNavigateEvidence(id)}
              >
                Show {id}
              </Button>
            ))}
          </div>
        ))}
        {pack?.limitations.map((text) => (
          <p key={text} className="text-xs text-mute">
            {text}
          </p>
        ))}
      </GlassCard>
    </div>
  );
}
