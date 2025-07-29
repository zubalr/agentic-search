# LLM Judge Evaluation Metrics

## Primary Evaluation Criteria (Core Search Quality)

These are the only criteria that should influence the main scores and verdicts:

1. **Precision & Top Result Accuracy (Most Important)**

   - The #1 result must exactly match the query intent (e.g., "Al Mirqab Mall" should return "Al Mirqab Mall" as the top result).
   - Penalize heavily if the correct result is buried or absent.

2. **Query Understanding & Component Handling**

   - For multi-part queries (e.g., "Al Noor compound thumama"), the engine must use all components.
   - Results that ignore any part of the query (e.g., only "Thumama" results) are a complete failure.

3. **Result Set Relevance & Purity**
   - Are results directly relevant to the user's intent?
   - Penalize "noisy" results (e.g., "Gate Mall Parking" for a mall query).
   - The result set should be clean and focused on the requested entity type.

## Secondary Evaluation Criteria (Tie-Breaker Only)

Use these ONLY if both result sets are equal on all primary criteria:

4. **Result Completeness**
   - Only use to break ties between otherwise equal results.
   - Prefer results with full `formattedAddress` and `contact` information.
   - Extra fields like `websiteUri`, `rating`, etc., are a minor bonus and should NOT affect scores unless used as a tie-breaker.
   - Ignore internal metadata like `popularity` or `score`.

## Metrics Provided by the Evaluator

- **verdict**: One of `INTERNAL_SERVER_BETTER`, `GOOGLE_MAPS_BETTER`, `BOTH_ARE_GOOD`, `BOTH_ARE_BAD`, `INCONCLUSIVE`.
- **internal_server_score**: Integer (1-5) for the internal server's result, based ONLY on primary criteria.
- **google_maps_score**: Integer (1-5) for the Google Maps result, based ONLY on primary criteria.
- **reasoning**: Detailed, step-by-step explanation for the verdict, referencing the criteria above.

## Best Practices

- Always base scores and verdicts on the primary criteria.
- Use completeness only as a tie-breaker, never as a main scoring factor.
- Provide clear, objective reasoning for every verdict.
- Do not include any text outside the required JSON object in LLM responses.
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
