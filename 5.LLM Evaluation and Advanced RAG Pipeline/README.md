# Project 5: LLM Evaluation and Advanced RAG Pipeline

**Level:** Advanced

## What we are building
An upgrade of Project 1's RAG system, plus an evaluation harness that measures whether each improvement actually helps. The result is a before/after report with numbers.

## Why
Most teams ship RAG without measuring it. Knowing how to build evals and improve retrieval based on data is one of the most valuable GenAI skills.

## How it works
```
Golden dataset (question, expected answer, source chunks)
    -> run pipeline variants (baseline, +hybrid, +rerank, +query rewrite)
    -> score retrieval + generation -> dashboard / comparison report
```

## What we will implement
1. **Golden dataset:** 50-100 question/answer pairs over a document set, partly hand-written and partly LLM-generated then reviewed.
2. **Baseline:** the basic vector-only RAG from Project 1.
3. **Improvements** (added one at a time):
   - hybrid search (BM25 plus vectors, merged with reciprocal rank fusion)
   - reranking with a cross-encoder or rerank API
   - query rewriting or expansion
   - parent-child or sentence-window chunking
4. **Retrieval metrics:** recall@k, precision@k, MRR.
5. **Generation metrics:** faithfulness, answer relevance, and context precision using RAGAS, plus a custom LLM-as-judge with a rubric.
6. **Judge reliability:** check the judge against human labels on a sample and test for position and verbosity bias.
7. **Regression tracking:** store every run, compare versions, and flag drops.
8. **Dashboard:** Streamlit page with a results table and charts per variant.
9. **Report:** record the accuracy, cost, and latency of every variant.

## Concepts learned
Why basic RAG fails, retrieval metrics, faithfulness scoring, LLM-as-judge and its biases, test set design, A/B comparison, cost-quality tradeoffs.

## Suggested tech stack
Python, Chroma or Qdrant, rank_bm25, sentence-transformers (cross-encoder), RAGAS, pandas, Streamlit, an LLM API.

## Suggested structure
```
pipeline/         # baseline.py, hybrid.py, rerank.py, rewrite.py
evals/            # dataset.json, metrics.py, judge.py, run_eval.py
results/          # one file per run
dashboard.py
REPORT.md
```

## Milestones
- [ ] Build the golden dataset
- [ ] Score the baseline
- [ ] Add each improvement and re-score
- [ ] Validate the judge against human labels
- [ ] Build the dashboard
- [ ] Write REPORT.md with the numbers and conclusions

## Stretch goals
CI job that runs evals on every change, synthetic test generation, GraphRAG comparison.

## Done when
You can show a table such as "baseline 62% -> final 81% answer accuracy" with the cost and latency tradeoff of each step, and explain why each change helped or didn't.
