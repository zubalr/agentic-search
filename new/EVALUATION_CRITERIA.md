# Evaluation Criteria for Raw File Comparison

This document defines the criteria and process for comparing and evaluating search results from two sources (e.g., internal API vs. Google Maps) using both automated metrics and LLM-based judgment.

---

## 1. Primary Evaluation Criteria (Core Search Quality)

1. **Precision & Top Result Accuracy (Most Important)**

   - The top result for a specific query (e.g., "Al Mirqab Mall") must be an exact match.
   - Penalize heavily if the correct result is buried or missing.
   - Score highly for exact top-result matches.

2. **Query Understanding & Component Handling**

   - For multi-part queries (e.g., "Al Noor compound thumama"), all components must be understood and matched.
   - Penalize if only part of the query is matched (e.g., only "Thumama" results).

3. **Result Set Relevance & Purity**
   - Results must be directly relevant to the user's intent.
   - Penalize noisy or irrelevant results (e.g., parking lots, streets for a mall query).
   - The result set should be clean and focused on the requested entity type.

---

## 2. Secondary Evaluation Criteria (Result Usefulness)

4. **Information Completeness for User Action**
   - Results should provide actionable information: full address, contact info, website, ratings, opening hours.
   - Sets with richer, user-facing data are considered higher quality.
   - Internal-only metadata (e.g., `popularity`, `score`) is ignored.

---

## 3. Automated Metrics

For each query, the following metrics are computed using POI identifiers:

- **Exact Match**: Are the result sets identical?
- **Jaccard Similarity**: Overlap between result sets.
- **Top-N Overlap**: How many of the top results match?
- **Missing/Extra Results**: Items present in one set but not the other.
- **Field-Level Differences**: Differences in key fields for matched POIs.
- **Precision, Recall, F1 Score**: Standard IR metrics for POI matches.

---

## 4. LLM Judging

The LLM is prompted with:

- Both result sets (full JSON).
- The query.
- Automated metrics summary.
- The evaluation criteria above (with strong emphasis on precision and relevance).

The LLM must return:

- **Verdict**: Which result set is better (or if both are good/bad/inconclusive).
- **Reasoning**: Step-by-step explanation.
- **Score (1-5)**: For each result set.

---

## 5. Evaluation Pipeline

1. **Load and preprocess both raw files.**
2. **For each query:**
   - Compute automated metrics.
   - Pass both result sets and metrics to the LLM for judgment.
   - Save verdicts, scores, and reasoning.
3. **Aggregate and analyze results.**
   - Summarize verdict distribution, average scores, and common failure modes.

---

## 6. How to Use

- Run the evaluation script (`scripts/evaluate.py`) with both files.
- Review the output and summary files in `output/`.
- Use the results to identify strengths, weaknesses, and actionable improvements for your search engine.

---

## 7. References

- [LLM Judging Prompt](src/evaluation/llm_judge.py)
- [Automated Metrics Logic](src/evaluation/comparison.py)
