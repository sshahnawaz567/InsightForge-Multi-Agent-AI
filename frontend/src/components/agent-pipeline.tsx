import { Check, Brain, ListTree, Database, Calculator, Library, Sparkle } from "lucide-react";
import { cn } from "@/lib/utils";

// IDs match backend/agents/langgraph_workflow.py's state['agents_executed'] entries.
export const PIPELINE_AGENTS = [
  { id: "query_understanding", label: "Query Understanding", icon: Brain },
  { id: "planning", label: "Planning", icon: ListTree },
  { id: "sql_execution", label: "SQL", icon: Database },
  { id: "calculation", label: "Calculation", icon: Calculator },
  { id: "context_search", label: "Context / RAG", icon: Library },
  { id: "synthesis", label: "Synthesis", icon: Sparkle },
] as const;

export function AgentPipeline({ activeIndex }: { activeIndex: number }) {
  return (
    <div className="glass animate-rise-in rounded-2xl p-5">
      <div className="mb-4 flex items-center gap-2">
        <span className="relative flex size-2">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary opacity-70" />
          <span className="relative inline-flex size-2 rounded-full bg-primary" />
        </span>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
          Agent pipeline running
        </p>
      </div>

      <ol className="flex flex-col gap-1 md:flex-row md:items-start md:gap-0">
        {PIPELINE_AGENTS.map((agent, i) => {
          const done = i < activeIndex;
          const active = i === activeIndex;
          const Icon = agent.icon;
          return (
            <li key={agent.id} className="flex flex-1 gap-3 md:flex-col md:items-center md:gap-2">
              <div className="flex flex-col items-center md:w-full md:flex-row">
                <div
                  className={cn(
                    "hidden h-px flex-1 md:block",
                    i === 0 && "opacity-0",
                    done || active ? "bg-primary/60" : "bg-border",
                  )}
                />
                <div
                  className={cn(
                    "relative flex size-9 shrink-0 items-center justify-center rounded-full border transition-all duration-500",
                    done && "border-success/50 bg-success/15 text-success",
                    active && "border-primary/60 bg-primary/15 text-primary glow-primary scale-110",
                    !done && !active && "border-border bg-secondary/50 text-muted-foreground",
                  )}
                >
                  {done ? (
                    <Check className="size-4 animate-soft-pop" />
                  ) : (
                    <Icon className={cn("size-4", active && "animate-pulse")} />
                  )}
                </div>
                <div
                  className={cn(
                    "hidden h-px flex-1 md:block",
                    i === PIPELINE_AGENTS.length - 1 && "opacity-0",
                  )}
                  style={
                    done
                      ? { backgroundColor: "var(--primary)", opacity: 0.6 }
                      : active
                        ? {
                            backgroundImage:
                              "repeating-linear-gradient(90deg, var(--primary) 0 8px, transparent 8px 16px)",
                            animation: "flow-dash 0.6s linear infinite",
                          }
                        : { backgroundColor: "var(--border)" }
                  }
                />
                {/* vertical connector on mobile */}
                <div
                  className={cn(
                    "w-px flex-1 md:hidden",
                    i === PIPELINE_AGENTS.length - 1 && "hidden",
                    done ? "bg-primary/60" : "bg-border",
                  )}
                  style={{ minHeight: 14 }}
                />
              </div>
              <p
                className={cn(
                  "pb-2 text-xs font-medium transition-colors duration-300 md:pb-0 md:text-center",
                  done && "text-foreground",
                  active && "text-primary",
                  !done && !active && "text-muted-foreground/70",
                )}
              >
                {agent.label}
              </p>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
