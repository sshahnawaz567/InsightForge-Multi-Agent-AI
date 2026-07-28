import { CheckCircle2, Clock, Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";

export type Impact = "high" | "medium" | "low";

export interface AnalysisResponse {
  query_id: string;
  session_id?: string;
  status: "success" | "partial";
  executive_summary: string;
  key_findings?: string[];
  root_causes?: { cause: string; explanation: string; impact?: string }[];
  recommendations?: { action: string; detail?: string; rationale?: string; priority?: string }[];
  execution_time?: number;
  agents_executed?: string[];
  confidence?: number;
}

// Real agent IDs come from backend/agents/langgraph_workflow.py's
// state['agents_executed'] entries.
const AGENT_LABELS: Record<string, string> = {
  query_understanding: "Query Understanding",
  planning: "Planning",
  sql_execution: "SQL",
  calculation: "Calculation",
  context_search: "Context / RAG",
  synthesis: "Synthesis",
};

const IMPACT_STYLES: Record<Impact, string> = {
  high: "border-destructive/40 bg-destructive/15 text-destructive",
  medium: "border-warning/40 bg-warning/15 text-warning",
  low: "border-info/40 bg-info/15 text-info",
};

function normalizeImpact(impact?: string): Impact | undefined {
  const lower = impact?.toLowerCase();
  return lower === "high" || lower === "medium" || lower === "low" ? lower : undefined;
}

function ConfidenceRing({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const r = 13;
  const c = 2 * Math.PI * r;
  return (
    <div className="flex items-center gap-2">
      <svg viewBox="0 0 32 32" className="size-8 -rotate-90">
        <circle cx="16" cy="16" r={r} fill="none" stroke="var(--border)" strokeWidth="3" />
        <circle
          cx="16"
          cy="16"
          r={r}
          fill="none"
          stroke="var(--primary)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - value)}
          style={{ transition: "stroke-dashoffset 1s ease-out" }}
        />
      </svg>
      <span className="text-xs text-muted-foreground">
        <span className="font-semibold text-foreground">{pct}%</span> confidence
      </span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-glass-border px-5 py-5 first:border-t-0">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        {title}
      </h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

export function InsightCard({ data }: { data: AnalysisResponse }) {
  return (
    <article className="glass animate-rise-in overflow-hidden rounded-2xl">
      <div className="h-px w-full bg-gradient-brand" />
      <Section title="Executive Summary">
        <p className="text-[15px] leading-relaxed text-foreground">{data.executive_summary}</p>
      </Section>

      {data.key_findings?.length ? (
        <Section title="Key Findings">
          <ul className="space-y-2.5">
            {data.key_findings.map((f, i) => (
              <li key={i} className="flex gap-3 text-sm leading-relaxed text-foreground/90">
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-cyan" />
                <span>{f}</span>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}

      {data.root_causes?.length ? (
        <Section title="Root Causes">
          <div className="space-y-2.5">
            {data.root_causes.map((rc, i) => {
              const impact = normalizeImpact(rc.impact);
              return (
                <div key={i} className="rounded-xl border border-glass-border bg-secondary/40 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-semibold text-foreground">{rc.cause}</p>
                    {impact && (
                      <span
                        className={cn(
                          "shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-semibold capitalize",
                          IMPACT_STYLES[impact],
                        )}
                      >
                        {impact}
                      </span>
                    )}
                  </div>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                    {rc.explanation}
                  </p>
                </div>
              );
            })}
          </div>
        </Section>
      ) : null}

      {data.recommendations?.length ? (
        <Section title="Recommendations">
          <ol className="space-y-3">
            {data.recommendations.map((r, i) => (
              <li key={i} className="flex gap-3">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">
                  {i + 1}
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-foreground">{r.action}</p>
                    {r.priority && (
                      <span className="rounded-full border border-glass-border px-2 py-0.5 text-[10px] font-semibold capitalize text-muted-foreground">
                        {r.priority}
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">
                    {r.rationale ?? r.detail}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </Section>
      ) : null}

      <footer className="flex flex-wrap items-center gap-x-5 gap-y-3 border-t border-glass-border bg-secondary/30 px-5 py-3">
        {typeof data.execution_time === "number" && (
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="size-3.5" />
            {data.execution_time}s
          </span>
        )}
        {typeof data.confidence === "number" && <ConfidenceRing value={data.confidence} />}
        <div className="flex flex-wrap items-center gap-1.5">
          <Lightbulb className="size-3.5 text-muted-foreground" />
          {data.agents_executed?.map((a) => (
            <span
              key={a}
              className="rounded-full border border-glass-border bg-card/60 px-2 py-0.5 text-[11px] text-muted-foreground"
            >
              {AGENT_LABELS[a] ?? a}
            </span>
          ))}
        </div>
      </footer>
    </article>
  );
}
