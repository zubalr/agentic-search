"""
Run DeepEval on LLM judge outputs (comparison_memory.jsonl) and optional human references.
Usage:
    python scripts/eval.py deepeval --results comparison_memory.jsonl --model cerebras/llama3-70b-instruct
"""
import argparse
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

def run_deepeval(results, references, model_str):
    # Set up LiteLLMModel for DeepEval (plug-and-play any provider/model)
    model = LiteLLMModel(model=model_str)
    # Choose metric(s) with LiteLLMModel
    metrics = [
        GEval(
            name="LLM-as-a-Judge",
            criteria="Is the verdict and reasoning correct and well-justified?",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5
        ),
        AnswerRelevancyMetric(threshold=0.7)
    ]
    # Prepare test cases
    test_cases = []
    for query, comp in results:
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
    # Run evaluation
    results = [assert_test(tc, model=model, metrics=metrics) for tc in test_cases]
    print("\nDeepEval Results:")
    for metric in metrics:
        print(f"{metric.name}: {getattr(metric, 'score', 'N/A')}")
        if hasattr(metric, 'reason'):
            print(f"Reason: {metric.reason}")

def main():
    parser = argparse.ArgumentParser(description="Run DeepEval on LLM judge outputs.")
    parser.add_argument('--results', required=True, help='Path to comparison_memory.jsonl')
    parser.add_argument('--references', help='Path to human reference labels (optional)')
    parser.add_argument('--model', required=True, help='LiteLLM model string (e.g. cerebras/llama3-70b-instruct, groq/llama3-8b-8192, openai/gpt-3.5-turbo)')
    args = parser.parse_args()
    results = list(load_comparisons(args.results))
    references = load_references(args.references) if args.references else None
    run_deepeval(results, references, args.model)

if __name__ == "__main__":
    main()
