"""
DeepEval integration for evaluation of LLM judge outputs.
Refactored for better modularity and integration.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

try:
    from deepeval.metrics import GEval, AnswerRelevancyMetric
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    from deepeval.models.litellm_model import LiteLLMModel
    from deepeval.evaluator import assert_test
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False

from src.core.evaluator import BaseEvaluatorInterface, EvaluationMode

logger = logging.getLogger(__name__)

class DeepEvalEvaluator(BaseEvaluatorInterface):
    """DeepEval-based evaluator for LLM judge outputs."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if not DEEPEVAL_AVAILABLE:
            raise ImportError("DeepEval is not available. Please install: pip install deepeval")
        
        self.config = config or {}
        self.model_str = self.config.get('model', 'cerebras/llama-3.3-70b')
        self.threshold = self.config.get('threshold', 0.7)
        
        # Initialize LiteLLM model
        self.model = LiteLLMModel(model=self.model_str)
        
        logger.info(f"Initialized DeepEval evaluator with model: {self.model_str}")
    
    def _create_metrics(self) -> List:
        """Create DeepEval metrics for evaluation."""
        return [
            GEval(
                name="LLM-as-a-Judge",
                criteria="Is the verdict and reasoning correct and well-justified?",
                evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
                threshold=self.threshold
            ),
            AnswerRelevancyMetric(threshold=self.threshold)
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
    
    def create_test_cases(self, 
                         comparisons: List[Tuple[str, Dict[str, Any]]],
                         references: Optional[Dict[str, str]] = None) -> List[LLMTestCase]:
        """Create DeepEval test cases from comparisons."""
        test_cases = []
        
        for query, comp in comparisons:
            verdict = comp.get('verdict', '')
            reasoning = comp.get('reasoning', '')
            actual_output = f"Verdict: {verdict}\nReasoning: {reasoning}"
            
            expected_output = None
            if references and query in references:
                expected_output = references[query]
            
            test_case = LLMTestCase(
                input=query,
                actual_output=actual_output,
                expected_output=expected_output
            )
            test_cases.append(test_case)
        
        return test_cases
    
    def run_evaluation(self, 
                      test_cases: List[LLMTestCase]) -> Dict[str, Any]:
        """Run DeepEval evaluation on test cases."""
        metrics = self._create_metrics()
        
        logger.info(f"Running DeepEval on {len(test_cases)} test cases...")
        
        results = []
        metric_scores = {}
        
        try:
            # Run evaluation for each test case
            for i, test_case in enumerate(test_cases):
                logger.debug(f"Evaluating test case {i+1}/{len(test_cases)}: {test_case.input}")
                
                case_result = assert_test(test_case, model=self.model, metrics=metrics)
                results.append(case_result)
            
            # Aggregate metric scores
            for metric in metrics:
                metric_name = metric.name
                if hasattr(metric, 'score'):
                    metric_scores[metric_name] = {
                        'score': getattr(metric, 'score', None),
                        'reason': getattr(metric, 'reason', None)
                    }
        
        except Exception as e:
            logger.error(f"Error running DeepEval evaluation: {e}")
        
        return {
            'total_test_cases': len(test_cases),
            'metric_scores': metric_scores,
            'detailed_results': results
        }
    
    def evaluate_from_files(self, 
                          results_file: str,
                          references_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate LLM judge outputs from files.
        
        Args:
            results_file: Path to JSONL file with comparison results
            references_file: Optional path to human reference labels
        
        Returns:
            Evaluation results
        """
        # Load data
        comparisons = self.load_comparisons_from_file(results_file)
        references = None
        if references_file:
            references = self.load_references_from_file(references_file)
        
        # Create test cases
        test_cases = self.create_test_cases(comparisons, references)
        
        # Run evaluation
        return self.run_evaluation(test_cases)
    
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
        
        # Create test cases
        test_cases = self.create_test_cases(comparisons, references)
        
        # Run evaluation
        eval_results = self.run_evaluation(test_cases)
        
        return {
            "evaluation_method": "deepeval",
            "mode": mode.value,
            "model": self.model_str,
            **eval_results
        }
    
    def get_metrics(self) -> List[str]:
        """Get list of metrics this evaluator provides."""
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
