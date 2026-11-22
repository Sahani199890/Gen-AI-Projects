# Project 3: Multi-Agent Research Assistant

**Level:** Intermediate

## What we are building
A system where several specialized agents work together to research any topic and produce a structured, cited report.

## Why
It introduces the agent loop, tool use, and orchestration, and shows where multi-agent systems break.

## How it works
```
Topic -> Planner (sub-questions)
      -> Searcher (web search + page reading, per sub-question)
      -> Critic (checks gaps, weak sources, contradictions) -> loop back if needed
      -> Writer (final report with citations)
```

## What we will implement
1. **Tools:** web search, page fetch and extract, file read, note-saving.
2. **Planner agent:** breaks the topic into 3-6 sub-questions.
3. **Searcher agent:** calls tools, collects evidence with source URLs.
4. **Critic agent:** reviews evidence, flags gaps, and requests more research (limited to N rounds).
5. **Writer agent:** produces a Markdown report where every claim links to a source.
6. **Orchestration:** use LangGraph, CrewAI, or the Claude Agent SDK with a shared state object.
7. **Guardrails:** max steps, max tokens, timeouts, and graceful tool-failure handling.
8. **Tracing:** log every agent step and tool call to inspect decisions.
9. **Comparison:** run the same topic with a single agent and with multiple agents, then compare quality and cost.

## Concepts learned
The agent loop, tool schemas, orchestration, state passing, role design, error handling, agent failure modes (loops, hallucinated sources).

## Suggested tech stack
Python, LangGraph or the Claude Agent SDK, a search API (Tavily, Brave, or SerpAPI), httpx and a readability parser, Streamlit or CLI.

## Suggested structure
```
agents/           # planner.py, searcher.py, critic.py, writer.py
tools/            # search.py, fetch.py, files.py
graph.py          # orchestration and state
main.py
reports/          # generated output
```

## Milestones
- [ ] One agent with one working tool
- [ ] Add the planner and searcher
- [ ] Add the critic loop with a round limit
- [ ] Add the writer and citations
- [ ] Add tracing and logging
- [ ] Compare single-agent vs. multi-agent runs
- [ ] Document the failures you hit

## Stretch goals
Parallel searchers, human-in-the-loop approval of the plan, source credibility scoring.

## Done when
Given a topic, the system produces a cited report within a bounded cost and number of steps, and you can explain every step from the trace.
