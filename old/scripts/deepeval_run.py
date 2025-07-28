"""
Run DeepEval on LLM judge outputs (comparison_memory.jsonl) and optional human references.
Usage:
    python scripts/deepeval_run.py --results comparison_memory.jsonl [--references human_labels.jsonl]
"""

import json
from deepeval.metrics import GEval, AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.models.litellm_model import LiteLLMModel
from deepeval.evaluator import assert_test
import os


def load_comparisons(results_file):
    """Load LLM judge outputs from JSONL file."""
    with open(results_file, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            query = data['query']
            comp = data['comparison']
            yield query, comp

def load_references(reference_file):
    """Load human reference labels from JSONL file (query -> label)."""
    refs = {}
    with open(reference_file, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            refs[data['query']] = data['label']
    return refs


# --- USER CONFIGURABLE PARAMETERS ---
RESULTS_FILE = "comparison_memory.jsonl"  # Path to LLM judge outputs
REFERENCES_FILE = None  # e.g. "human_labels.jsonl" or None
MODEL = "cerebras/llama3-70b-instruct"  # e.g. cerebras/llama3-70b-instruct, groq/llama3-8b-8192, openai/gpt-3.5-turbo

def run_deepeval(results_file, references_file, model_str):
    comparisons = list(load_comparisons(results_file))
    references = load_references(references_file) if references_file else None
    model = LiteLLMModel(model=model_str)
    metrics = [
        GEval(
            name="LLM-as-a-Judge",
            criteria="Is the verdict and reasoning correct and well-justified?",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5
        ),
        AnswerRelevancyMetric(threshold=0.7)
    ]
    test_cases = []
    for query, comp in comparisons:
        verdict = comp.get('verdict', '')
        reasoning = comp.get('reasoning', '')
        actual_output = f"Verdict: {verdict}\nReasoning: {reasoning}"
        expected_output = references[query] if references and query in references else None
        test_case = LLMTestCase(
            input=query,
            actual_output=actual_output,
            expected_output=expected_output
        )
        test_cases.append(test_case)
    results = [assert_test(tc, model=model, metrics=metrics) for tc in test_cases]
    print("\nDeepEval Results:")
    for metric in metrics:
        print(f"{metric.name}: {getattr(metric, 'score', 'N/A')}")
        if hasattr(metric, 'reason'):
            print(f"Reason: {metric.reason}")

if __name__ == "__main__":
    run_deepeval(RESULTS_FILE, REFERENCES_FILE, MODEL)
