
from dotenv import load_dotenv
load_dotenv()
from deepeval.models.base_model import DeepEvalBaseLLM
from pydantic import BaseModel

# Custom LiteLLM wrapper for Cerebras
class LiteLLMCerebras(DeepEvalBaseLLM):
    def get_model_name(self):
        return self.model

    async def a_generate(self, prompt: str, schema: BaseModel) -> BaseModel:
        import litellm
        import json
        import logging
        
        # Instruct model to return JSON
        prompt_with_json = f"{prompt}\nPlease format your response as a JSON object."
        messages = [{"content": prompt_with_json, "role": "user"}]
        
        try:
            response = await litellm.acompletion(
                model=self.model,
                api_key=self.api_key,
                messages=messages
            )
            
            response_content = response["choices"][0]["message"]["content"]
            logging.info(f"LiteLLMCerebras.a_generate: Raw response: {response_content}")
            
            # Try to parse JSON from the response
            try:
                response_json = json.loads(response_content)
            except json.JSONDecodeError:
                # Try to extract JSON from the response if it's wrapped in text
                import re
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if json_match:
                    response_json = json.loads(json_match.group())
                else:
                    raise ValueError("No valid JSON found in response")
            
            logging.info(f"LiteLLMCerebras.a_generate: Parsed response JSON: {response_json}")
            
            # Ensure required attributes exist in response_json
            required_attrs = getattr(schema, '__annotations__', {})
            for attr in required_attrs:
                if attr not in response_json:
                    logging.warning(f"LiteLLMCerebras.a_generate: Missing attribute '{attr}' in response, setting to default.")
                    # Set appropriate defaults based on attribute name
                    if attr == 'verdicts':
                        response_json[attr] = []
                    elif attr == 'score':
                        response_json[attr] = 0.0
                    elif attr == 'reason':
                        response_json[attr] = "No reason provided"
                    else:
                        response_json[attr] = None
            
            response = schema.model_validate(response_json)
            
        except Exception as e:
            logging.error(f"LiteLLMCerebras.a_generate: Exception: {e}")
            # Create a proper default response based on schema
            default_data = {}
            required_attrs = getattr(schema, '__annotations__', {})
            for attr in required_attrs:
                if attr == 'verdicts':
                    default_data[attr] = []
                elif attr == 'score':
                    default_data[attr] = 0.0
                elif attr == 'reason':
                    default_data[attr] = "Error generating response"
                else:
                    default_data[attr] = None
            
            response = schema.model_construct(**default_data)
            
        return response
    def __init__(self, model="cerebras/llama-3.3-70b", api_key=None):
        import litellm
        self.model = model
        self.api_key = api_key or os.environ.get("CEREBRAS_API_KEY")
    def load_model(self):
        return self.model
    def generate(self, prompt: str, schema: BaseModel) -> BaseModel:
        import logging
        import json
        import litellm
        
        # Instruct model to return JSON
        prompt_with_json = f"{prompt}\nPlease format your response as a JSON object."
        messages = [{"content": prompt_with_json, "role": "user"}]
        
        try:
            response = litellm.completion(
                model=self.model,
                api_key=self.api_key,
                messages=messages
            )
            
            response_content = response["choices"][0]["message"]["content"]
            logging.info(f"LiteLLMCerebras.generate: Raw response: {response_content}")
            
            # Try to parse JSON from the response
            try:
                response_json = json.loads(response_content)
            except json.JSONDecodeError:
                # Try to extract JSON from the response if it's wrapped in text
                import re
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if json_match:
                    response_json = json.loads(json_match.group())
                else:
                    raise ValueError("No valid JSON found in response")
            
            logging.info(f"LiteLLMCerebras.generate: Parsed response JSON: {response_json}")
            
            # Ensure required attributes exist in response_json
            required_attrs = getattr(schema, '__annotations__', {})
            for attr in required_attrs:
                if attr not in response_json:
                    logging.warning(f"LiteLLMCerebras.generate: Missing attribute '{attr}' in response, setting to default.")
                    # Set appropriate defaults based on attribute name
                    if attr == 'verdicts':
                        response_json[attr] = []
                    elif attr == 'score':
                        response_json[attr] = 0.0
                    elif attr == 'reason':
                        response_json[attr] = "No reason provided"
                    else:
                        response_json[attr] = None
            
            response = schema.model_validate(response_json)
            
        except Exception as e:
            logging.error(f"LiteLLMCerebras.generate: Exception: {e}")
            # Create a proper default response based on schema
            default_data = {}
            required_attrs = getattr(schema, '__annotations__', {})
            for attr in required_attrs:
                if attr == 'verdicts':
                    default_data[attr] = []
                elif attr == 'score':
                    default_data[attr] = 0.0
                elif attr == 'reason':
                    default_data[attr] = "Error generating response"
                else:
                    default_data[attr] = None
            
            response = schema.model_construct(**default_data)
            
        return response
"""
DeepEval integration for evaluation of LLM judge outputs.
Refactored for better modularity and integration.
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

try:
    from deepeval.metrics import GEval, AnswerRelevancyMetric
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    from deepeval import assert_test
    import litellm
    DEEPEVAL_AVAILABLE = True
except ImportError as e:
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.error(f"DeepEval import failed: {e}")
    DEEPEVAL_AVAILABLE = False

from src.core.evaluator import BaseEvaluatorInterface, EvaluationMode

logger = logging.getLogger(__name__)

class DeepEvalEvaluator(BaseEvaluatorInterface):
    """DeepEval-based evaluator for LLM judge outputs."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if not DEEPEVAL_AVAILABLE:
            raise ImportError("DeepEval is not available. Please install: pip install deepeval")

        self.config = config or {}
        # Always use Cerebras model string
        self.model_str = self.config.get('model', 'cerebras/llama-3.3-70b')
        self.threshold = self.config.get('threshold', 0.7)

        # Enforce Cerebras model string
        if not self.model_str.startswith('cerebras/'):
            logger.error(f"Model string '{self.model_str}' is not a valid Cerebras model. Please use a model string starting with 'cerebras/'.")
            raise ValueError(f"Model string '{self.model_str}' is not a valid Cerebras model. Please use a model string starting with 'cerebras/'.")

        # Ensure CEREBRAS_API_KEY is set
        self.cerebras_api_key = os.environ.get('CEREBRAS_API_KEY')
        if not self.cerebras_api_key:
            logger.error("CEREBRAS_API_KEY environment variable not set. Please set it before running.")
        logger.info(f"Initialized DeepEval evaluator for Cerebras model: {self.model_str}")
        self.model = self.model_str
    
    def _create_metrics(self) -> List:
        """Create DeepEval metrics for evaluation."""
        cerebras_llm = LiteLLMCerebras(model=self.model_str, api_key=self.cerebras_api_key)
        return [
            GEval(
                name="LLM-as-a-Judge",
                criteria="Is the verdict and reasoning correct and well-justified?",
                evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
                evaluation_steps=[
                    "Check if the verdict is one of the valid options",
                    "Evaluate if the reasoning is logical and well-supported",
                    "Assess if the scores are appropriate for the given reasoning"
                ],
                threshold=self.threshold,
                model=cerebras_llm
            ),
            AnswerRelevancyMetric(threshold=self.threshold, model=cerebras_llm)
        ]
    
    def load_comparisons_from_file(self, results_file: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Load LLM judge outputs from JSONL file."""
        comparisons = []
        
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if 'query' in data and 'comparison' in data:
                            query = data['query']
                            comp = data['comparison']
                            comparisons.append((query, comp))
                        elif 'query' in data:
                            # Handle direct format
                            query = data['query']
                            comp = {k: v for k, v in data.items() if k != 'query'}
                            comparisons.append((query, comp))
                            
        except Exception as e:
            logger.error(f"Error loading comparisons from {results_file}: {e}")
        
        logger.info(f"Loaded {len(comparisons)} comparisons from {results_file}")
        return comparisons
    
    def load_references_from_file(self, reference_file: str) -> Dict[str, str]:
        """Load human reference labels from JSONL file."""
        references = {}
        
        try:
            with open(reference_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if 'query' in data and 'label' in data:
                            references[data['query']] = data['label']
                            
        except Exception as e:
            logger.error(f"Error loading references from {reference_file}: {e}")
        
        logger.info(f"Loaded {len(references)} references from {reference_file}")
        return references
    
    def create_test_cases_per_metric(self, comparisons: List[Tuple[str, Dict[str, Any]]], references: Optional[Dict[str, str]] = None) -> Dict[str, List[LLMTestCase]]:
        """
        Create DeepEval test cases for each metric with appropriate actual_output.
        Returns a dict: {metric_name: [LLMTestCase, ...]}
        """
        test_cases_per_metric = {
            "LLM-as-a-Judge": [],
            "AnswerRelevancyMetric": []
        }
        for query, comp in comparisons:
            verdict = comp.get('verdict', '')
            reasoning = comp.get('reasoning', '')
            # For LLM-as-a-Judge: verdict + reasoning
            actual_output_judge = f"Verdict: {verdict}\nReasoning: {reasoning}"
            # For AnswerRelevancyMetric: reasoning only
            actual_output_relevancy = reasoning
            expected_output = None
            if references and query in references:
                expected_output = references[query]
            test_cases_per_metric["LLM-as-a-Judge"].append(
                LLMTestCase(
                    input=query,
                    actual_output=actual_output_judge,
                    expected_output=expected_output
                )
            )
            test_cases_per_metric["AnswerRelevancyMetric"].append(
                LLMTestCase(
                    input=query,
                    actual_output=actual_output_relevancy,
                    expected_output=expected_output
                )
            )
        return test_cases_per_metric
    
    def run_evaluation(self, test_cases_per_metric: Dict[str, List[LLMTestCase]]) -> Dict[str, Any]:
        """Run DeepEval evaluation on test cases, per metric."""
        metrics = self._create_metrics()
        logger.info(f"Running DeepEval on {len(test_cases_per_metric['LLM-as-a-Judge'])} test cases...")
        results = []
        metric_scores = {}
        try:
            # Evaluate each metric with its own test cases
            for metric in metrics:
                metric_name = getattr(metric, 'name', metric.__class__.__name__)
                cases = test_cases_per_metric[metric_name]
                metric_results = []
                scores = []
                successes = []
                for i, test_case in enumerate(cases):
                    logger.debug(f"Evaluating {metric_name} test case {i+1}/{len(cases)}: {test_case.input}")
                    try:
                        metric.measure(test_case)
                        metric_results.append({
                            'test_case': test_case.input,
                            'metrics': {
                                metric_name: {
                                    'score': getattr(metric, 'score', None),
                                    'success': getattr(metric, 'success', None),
                                    'reason': getattr(metric, 'reason', None)
                                }
                            }
                        })
                        score = getattr(metric, 'score', None)
                        success = getattr(metric, 'success', None)
                        if score is not None:
                            scores.append(score)
                        if success is not None:
                            successes.append(success)
                    except Exception as metric_error:
                        logger.warning(f"Error evaluating metric {metric_name}: {metric_error}")
                        metric_results.append({
                            'test_case': test_case.input,
                            'metrics': {
                                metric_name: {
                                    'score': None,
                                    'success': False,
                                    'reason': f"Error: {metric_error}"
                                }
                            }
                        })
                metric_scores[metric_name] = {
                    'average_score': sum(scores) / len(scores) if scores else None,
                    'success_rate': sum(successes) / len(successes) if successes else None,
                    'total_evaluations': len(cases)
                }
                results.extend(metric_results)
        except Exception as e:
            logger.error(f"Error running DeepEval evaluation: {e}")
            import traceback
            traceback.print_exc()
        return {
            'total_test_cases': len(test_cases_per_metric['LLM-as-a-Judge']),
            'metric_scores': metric_scores,
            'detailed_results': results
        }
    
    def evaluate_from_files(self, results_file: str, references_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate LLM judge outputs from files.
        Args:
            results_file: Path to JSONL file with comparison results
            references_file: Optional path to human reference labels
        Returns:
            Evaluation results
        """
        comparisons = self.load_comparisons_from_file(results_file)
        references = None
        if references_file:
            references = self.load_references_from_file(references_file)
        test_cases_per_metric = self.create_test_cases_per_metric(comparisons, references)
        return self.run_evaluation(test_cases_per_metric)

    def evaluate(self, 
            internal_results: Dict[str, Any],
            google_results: Dict[str, Any],
            mode: EvaluationMode,
            **kwargs) -> Dict[str, Any]:
        """
        Main evaluation method implementing BaseEvaluatorInterface.
        Note: This expects comparison results, not raw API results.
        """
        # For DeepEval, we expect comparison_results in kwargs
        comparison_results = kwargs.get('comparison_results', [])
        references = kwargs.get('references', None)

        if not comparison_results:
            raise ValueError("DeepEval evaluator requires 'comparison_results' in kwargs")

        # Convert comparison results to the expected format
        comparisons = []
        for result in comparison_results:
            if 'query' in result:
                query = result['query']
                comp = {k: v for k, v in result.items() if k != 'query'}
                comparisons.append((query, comp))

        # Create test cases per metric
        test_cases_per_metric = self.create_test_cases_per_metric(comparisons, references)

        # Run evaluation
        eval_results = self.run_evaluation(test_cases_per_metric)

        return {
            "evaluation_method": "deepeval",
            "mode": mode.value,
            "model": self.model_str,
            **eval_results
        }
    
    def get_metrics(self) -> List[str]:
        """
        Get list of metrics this evaluator provides.
        """
        return [
            "LLM-as-a-Judge",
            "AnswerRelevancy"
        ]


def create_deepeval_evaluator(model_str: str = "cerebras/llama-3.3-70b",
                            threshold: float = 0.7) -> DeepEvalEvaluator:
    """
    Factory function to create a DeepEval evaluator.
    Args:
        model_str: LiteLLM model string
        threshold: Evaluation threshold
    Returns:
        Configured DeepEvalEvaluator instance
    """
    config = {
        'model': model_str,
        'threshold': threshold
    }
    return DeepEvalEvaluator(config)
