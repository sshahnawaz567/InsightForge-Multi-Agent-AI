import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { ArrowUp, Loader2, MessageSquare, PanelLeft, Plus } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { InsightCard, type AnalysisResponse } from "@/components/insight-card";
import { AgentPipeline, PIPELINE_AGENTS } from "@/components/agent-pipeline";
import { ThemeToggle } from "@/components/theme-toggle";
import { askInsightForge, checkHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "InsightForge — Multi-Agent Business Intelligence" },
      {
        name: "description",
        content:
          "Watch six specialized AI agents collaborate in real time to turn plain-English business questions into structured insight cards.",
      },
      { property: "og:title", content: "InsightForge — Multi-Agent Business Intelligence" },
      {
        property: "og:description",
        content: "A live multi-agent pipeline that answers business questions with structured analysis.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

const EXAMPLES = [
  "What was our revenue last month?",
  "Why did sales drop in December?",
  "Compare Q4 vs Q3 performance",
  "Which customer segment is churning fastest?",
];

type Message =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; data: AnalysisResponse }
  | { id: string; role: "error"; text: string };

type Thread = { id: string; title: string; messages: Message[]; sessionId?: string };

const newThread = (): Thread => ({
  id: crypto.randomUUID(),
  title: "New conversation",
  messages: [],
});

function Index() {
  const [threads, setThreads] = useState<Thread[]>(() => [newThread()]);
  const [activeId, setActiveId] = useState(() => threads[0].id);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [query, setQuery] = useState("");
  const [step, setStep] = useState(-1);
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const active = threads.find((t) => t.id === activeId) ?? threads[0];
  const loading = step >= 0;

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const ok = await checkHealth();
      if (!cancelled) setHealthy(ok);
    };
    poll();
    const interval = setInterval(poll, 30_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [active.messages.length, step]);

  useEffect(() => {
    if (!loading) inputRef.current?.focus();
  }, [loading, activeId]);

  function push(threadId: string, msg: Message, title?: string) {
    setThreads((prev) =>
      prev.map((t) =>
        t.id === threadId
          ? {
              ...t,
              title: title && t.messages.length === 0 ? title : t.title,
              messages: [...t.messages, msg],
            }
          : t,
      ),
    );
  }

  async function ask() {
    const q = query.trim();
    if (!q || loading) return;
    const threadId = active.id;
    push(threadId, { id: crypto.randomUUID(), role: "user", text: q }, q.slice(0, 48));
    setQuery("");
    setStep(0);

    // Roughly weighted by how long each agent actually tends to take
    // (LLM calls like Synthesis/Query Understanding run longer than pure
    // Python steps like Calculation). Cumulative offsets, in ms.
    const STEP_DELAYS = [0, 1800, 3200, 5200, 6600, 8200];
    const startedAt = Date.now();
    const timers = STEP_DELAYS.map((delay, i) => setTimeout(() => setStep(i), delay));
    const minAnimationMs = STEP_DELAYS[STEP_DELAYS.length - 1];

    try {
      const currentThread = threads.find((t) => t.id === threadId);
      const data = await askInsightForge(q, currentThread?.sessionId);

      // Only top up to the minimum animation length if the real response
      // came back faster than that - never add extra wait on top of a slow one.
      const elapsed = Date.now() - startedAt;
      if (elapsed < minAnimationMs) {
        await new Promise((r) => setTimeout(r, minAnimationMs - elapsed));
      }

      // Persist the session_id so follow-up questions in this thread carry context
      if (data.session_id) {
        setThreads((prev) =>
          prev.map((t) => (t.id === threadId ? { ...t, sessionId: data.session_id } : t)),
        );
      }

      push(threadId, { id: crypto.randomUUID(), role: "assistant", data });
    } catch (e) {
      push(threadId, {
        id: crypto.randomUUID(),
        role: "error",
        text: e instanceof Error ? e.message : "Something went wrong",
      });
    } finally {
      timers.forEach(clearTimeout);
      setStep(-1);
    }
  }

  const empty = active.messages.length === 0 && !loading;

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside
        className={cn(
          "sticky top-0 hidden h-screen shrink-0 flex-col border-r border-sidebar-border bg-sidebar/70 backdrop-blur-xl transition-all duration-300 md:flex",
          sidebarOpen ? "w-64" : "w-0 overflow-hidden border-r-0",
        )}
      >
        <div className="flex items-center justify-between px-4 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Sessions
          </p>
        </div>
        <div className="flex-1 space-y-1 overflow-y-auto px-2 pb-4">
          {threads.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setActiveId(t.id)}
              className={cn(
                "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                t.id === activeId
                  ? "bg-primary/15 text-foreground"
                  : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground",
              )}
            >
              <MessageSquare className="size-3.5 shrink-0" />
              <span className="truncate">{t.title}</span>
            </button>
          ))}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-20 border-b border-glass-border bg-background/70 backdrop-blur-xl">
          <div className="flex items-center justify-between gap-3 px-4 py-3">
            <div className="flex items-center gap-3">
              <button
                type="button"
                aria-label="Toggle sidebar"
                onClick={() => setSidebarOpen((v) => !v)}
                className="hidden size-9 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground md:flex"
              >
                <PanelLeft className="size-4" />
              </button>
              <span className="text-lg font-semibold tracking-tight text-gradient-brand">
                InsightForge
              </span>
              <span className="flex items-center gap-1.5 rounded-full border border-glass-border px-2.5 py-1">
                <span className="relative flex size-1.5">
                  {healthy && (
                    <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-70" />
                  )}
                  <span
                    className={cn(
                      "relative inline-flex size-1.5 rounded-full",
                      healthy === null && "bg-muted-foreground",
                      healthy === true && "bg-success",
                      healthy === false && "bg-destructive",
                    )}
                  />
                </span>
                <span className="text-[11px] font-medium text-muted-foreground">
                  {healthy === null ? "Checking..." : healthy ? "Healthy" : "Offline"}
                </span>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <button
                type="button"
                onClick={() => {
                  const t = newThread();
                  setThreads((prev) => [t, ...prev]);
                  setActiveId(t.id);
                  setQuery("");
                }}
                className="glass flex items-center gap-1.5 rounded-full px-3.5 py-2 text-sm font-medium text-foreground transition-transform hover:scale-[1.03]"
              >
                <Plus className="size-4" />
                <span className="hidden sm:inline">New conversation</span>
              </button>
            </div>
          </div>
        </header>

        {/* Thread */}
        <main className="flex-1">
          <div className="mx-auto max-w-3xl px-4 py-8">
            {empty ? (
              <div className="animate-rise-in py-12 text-center">
                <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                  Ask anything about your <span className="text-gradient-brand">business</span>
                </h1>
                <p className="mx-auto mt-3 max-w-lg text-sm leading-relaxed text-muted-foreground">
                  Six specialized agents — understanding, planning, SQL, calculation, context and
                  synthesis — collaborate to turn plain-English questions into structured insight.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {active.messages.map((m) =>
                  m.role === "user" ? (
                    <div key={m.id} className="flex justify-end">
                      <p className="animate-rise-in max-w-[80%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground">
                        {m.text}
                      </p>
                    </div>
                  ) : m.role === "assistant" ? (
                    <InsightCard key={m.id} data={m.data} />
                  ) : (
                    <div
                      key={m.id}
                      className="glass animate-rise-in rounded-2xl border-destructive/40 px-5 py-4 text-sm text-destructive"
                    >
                      {m.text}
                    </div>
                  ),
                )}
              </div>
            )}

            {loading && (
              <div className="mt-6">
                <AgentPipeline activeIndex={step} />
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </main>

        {/* Composer */}
        <div className="sticky bottom-0 z-20 bg-gradient-to-t from-background via-background/90 to-transparent pb-5 pt-6">
          <div className="mx-auto max-w-3xl px-4">
            <div className="glass rounded-2xl p-2.5">
              <div className="flex items-end gap-2">
                <Textarea
                  ref={inputRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      ask();
                    }
                  }}
                  placeholder="Ask a follow-up, e.g. why did that happen?"
                  className="min-h-11 resize-none border-0 bg-transparent text-[15px] shadow-none focus-visible:ring-0"
                />
                <button
                  type="button"
                  onClick={ask}
                  disabled={loading || !query.trim()}
                  aria-label="Ask"
                  className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-gradient-brand text-primary-foreground transition-opacity disabled:opacity-40"
                >
                  {loading ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <ArrowUp className="size-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap justify-center gap-2">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  type="button"
                  onClick={() => {
                    setQuery(ex);
                    inputRef.current?.focus();
                  }}
                  className="rounded-full border border-glass-border bg-card/40 px-3 py-1.5 text-xs text-muted-foreground backdrop-blur transition-colors hover:border-primary/50 hover:text-foreground"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
