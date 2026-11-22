# Project 6: Capstone, Deployed GenAI Product with Guardrails and Observability

**Level:** Advanced

## What we are building
One production-style GenAI product for a niche you choose (legal, health, finance, education, etc.) that combines everything from Projects 1-5: RAG, agents, MCP tools, and evals. It adds security, monitoring, and a live deployment.

## Why
This is the portfolio piece. It shows you can take a GenAI idea from prototype to a safe, measured, deployed product.

## Architecture
```
Frontend (Streamlit / Next.js)
    -> FastAPI backend (auth, rate limits)
        -> Guardrails in:  PII redaction, prompt-injection check, input moderation
        -> Orchestrator: RAG (Project 5) + agents (Project 3) + MCP tools (Project 4)
        -> Guardrails out: output moderation, citation/grounding check
        -> Cache (semantic) + DB (users, chats, feedback)
    -> Observability: traces, cost, latency, user feedback (Langfuse / LangSmith)
```

## What we will implement
1. **Pick the niche and the use case**, and write a one-page product spec.
2. **Core features:** document Q&A with citations plus at least one agent workflow using tools.
3. **Backend:** FastAPI with streaming endpoints, authentication, and per-user rate limits.
4. **Input guardrails:** PII detection and redaction (e.g., Presidio), prompt-injection detection, off-topic filtering.
5. **Output guardrails:** moderation, grounding and citation checks, safe refusal messages.
6. **Caching:** semantic cache for repeated questions to cut cost and latency.
7. **Observability:** trace every request with tokens, cost, latency, and tool calls; add a thumbs up/down feedback button.
8. **Evaluation in CI:** run the Project 5 eval set on every pull request and fail on regressions.
9. **Security review:** test against the OWASP LLM Top 10 (injection, data leakage, excessive agency).
10. **Deployment:** Docker, docker-compose, GitHub Actions CI/CD, hosted on Render, Railway, Fly.io, or a cloud VM, with a live demo link.
11. **Documentation:** architecture diagram, tradeoff decisions, cost per query, known failure cases.

## Concepts learned
Architecture tradeoffs, LLM security, guardrails, monitoring, cost optimization, deployment, CI for LLM apps, and presenting your work.

## Suggested tech stack
Python, FastAPI, Docker, Postgres or SQLite, Redis (cache and rate limits), Langfuse, Presidio, GitHub Actions, a frontend of your choice.

## Suggested structure
```
backend/          # api, guardrails, orchestration, cache
frontend/
evals/            # reused from Project 5
infra/            # Dockerfile, docker-compose, CI workflows
docs/             # architecture, security notes, cost analysis
README.md
```

## Milestones
- [ ] Product spec and architecture diagram
- [ ] Core RAG and agent flow behind the API
- [ ] Frontend connected with streaming
- [ ] Input and output guardrails with tests
- [ ] Caching and rate limiting
- [ ] Tracing and feedback collection
- [ ] CI with eval regression checks
- [ ] Security test pass
- [ ] Deployed with a public demo
- [ ] Final write-up and 3-minute demo video

## Stretch goals
Multi-tenant document spaces, model routing for cost, an admin analytics page, an A/B test between two prompts.

## Done when
A stranger can open the live link, use the product, and you can show its traces, cost per query, eval scores, and the attacks it blocks.
