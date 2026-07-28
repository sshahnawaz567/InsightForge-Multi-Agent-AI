import { createFileRoute } from "@tanstack/react-router";
import type {} from "@tanstack/react-start";

export const Route = createFileRoute("/api/query")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        let query = "";
        try {
          const body = (await request.json()) as { query?: string };
          query = typeof body.query === "string" ? body.query.trim() : "";
        } catch {
          query = "";
        }

        if (!query) {
          return new Response(JSON.stringify({ error: "query is required" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          });
        }

        const started = Date.now();
        await new Promise((r) => setTimeout(r, 900));

        const payload = {
          query_id: crypto.randomUUID(),
          status: "success" as const,
          executive_summary: `Analysis for "${query}": revenue reached $4.28M last period, up 6.4% versus the prior period, though growth decelerated in the final four weeks as enterprise renewals slipped and discounting deepened.`,
          key_findings: [
            "Total revenue of $4.28M, +6.4% period over period.",
            "Enterprise segment contributed 61% of revenue but only 28% of new logos.",
            "Average discount widened from 8.1% to 12.7%, compressing gross margin by 2.3 pts.",
            "Churn concentrated in accounts with fewer than 3 active seats.",
          ],
          root_causes: [
            {
              cause: "Renewal timing shift",
              impact: "High" as const,
              explanation:
                "14 enterprise renewals moved into the following quarter after a mid-period pricing update, deferring roughly $310K.",
            },
            {
              cause: "Deeper discounting",
              impact: "Medium" as const,
              explanation:
                "Field reps applied non-standard discounts on 31% of closed deals to hit quota in the final two weeks.",
            },
            {
              cause: "Low activation in small accounts",
              impact: "Low" as const,
              explanation:
                "Accounts under 3 seats reached first value 11 days later on average, correlating with a 2.4x churn rate.",
            },
          ],
          recommendations: [
            {
              action: "Lock discount approvals above 10%",
              detail: "Route them through deal desk to protect margin during end-of-period pushes.",
            },
            {
              action: "Rebalance renewal calendar",
              detail: "Stagger enterprise renewal dates to avoid concentrated period-end exposure.",
            },
            {
              action: "Ship a guided onboarding for small teams",
              detail: "Target time-to-first-value under 3 days for accounts with fewer than 3 seats.",
            },
          ],
          execution_time: Number(((Date.now() - started) / 1000).toFixed(1)),
          agents_executed: [
            "query_understanding",
            "planning",
            "sql",
            "calculation",
            "context",
            "synthesis",
          ],
          confidence: 0.92,
        };

        return new Response(JSON.stringify(payload), {
          headers: { "Content-Type": "application/json" },
        });
      },
    },
  },
});
