"""
Evaluation coordinator for managing different evaluation strategies.
"""

import logging
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class EvaluationMode(Enum):
    """Supported evaluation modes."""
    BATCH = "batch"
    SEQUENTIAL = "sequential"

class EvaluationStrategy(Enum):
    """Supported evaluation strategies."""
    LLM_JUDGE = "llm_judge"
    DEEPEVAL = "deepeval"
    RAGAS = "ragas"

class Evaluator:
    """
    Main evaluator that coordinates different evaluation strategies.
    """
    
    def __init__(self, strategy: EvaluationStrategy = EvaluationStrategy.LLM_JUDGE):
        self.strategy = strategy
        self._evaluators = {}
    
    def register_evaluator(self, strategy: EvaluationStrategy, evaluator_instance):
        """Register an evaluator for a specific strategy."""
        self._evaluators[strategy] = evaluator_instance
    
    def evaluate(self, 
                internal_results: Dict[str, Any],
                google_results: Dict[str, Any],
                mode: EvaluationMode = EvaluationMode.BATCH,
                **kwargs) -> Dict[str, Any]:
        """
        Evaluate search results using the configured strategy.
        
        Args:
            internal_results: Results from internal API
            google_results: Results from Google Places API
            mode: Evaluation mode (batch or sequential)
            **kwargs: Additional arguments for specific evaluators
        
        Returns:
            Evaluation results
        """
        if self.strategy not in self._evaluators:
            raise ValueError(f"No evaluator registered for strategy: {self.strategy}")
        
        evaluator = self._evaluators[self.strategy]
        
        logger.info(f"Starting evaluation with strategy: {self.strategy.value}, mode: {mode.value}")
        
        if hasattr(evaluator, 'evaluate'):
            return evaluator.evaluate(internal_results, google_results, mode, **kwargs)
        else:
            raise AttributeError(f"Evaluator {self.strategy} does not implement 'evaluate' method")
    
    def get_available_strategies(self) -> List[EvaluationStrategy]:
        """Get list of available evaluation strategies."""
        return list(self._evaluators.keys())
    
    def set_strategy(self, strategy: EvaluationStrategy):
        """Change the evaluation strategy."""
        if strategy not in self._evaluators:
            raise ValueError(f"Strategy {strategy} not registered")
        self.strategy = strategy
        logger.info(f"Evaluation strategy changed to: {strategy.value}")


class BaseEvaluatorInterface:
    """Base interface that all evaluators should implement."""
    
    def evaluate(self, 
                internal_results: Dict[str, Any],
                google_results: Dict[str, Any],
                mode: EvaluationMode,
                **kwargs) -> Dict[str, Any]:
        """
        Evaluate the provided results.
        
        Args:
            internal_results: Results from internal API
            google_results: Results from Google Places API
            mode: Evaluation mode
            **kwargs: Additional arguments
        
        Returns:
            Evaluation results
        """
        raise NotImplementedError("Subclasses must implement evaluate method")
    
    def get_metrics(self) -> List[str]:
        """Get list of metrics this evaluator provides."""
        raise NotImplementedError("Subclasses must implement get_metrics method")


def create_evaluator(strategy: EvaluationStrategy, 
                    config: Optional[Dict[str, Any]] = None) -> Evaluator:
    """
    Factory function to create evaluator with proper strategy registration.
    
    Args:
        strategy: Primary evaluation strategy
        config: Configuration for evaluators
    
    Returns:
        Configured Evaluator instance
    """
    evaluator = Evaluator(strategy)
    
    # Import and register evaluators based on availability
    try:
        from src.evaluation.llm_judge import LLMJudgeEvaluator
        evaluator.register_evaluator(EvaluationStrategy.LLM_JUDGE, LLMJudgeEvaluator(config))
        logger.info("Registered LLM Judge evaluator")
    except ImportError:
        logger.warning("LLM Judge evaluator not available")
    
    try:
        from src.evaluation.deepeval_runner import DeepEvalEvaluator
        evaluator.register_evaluator(EvaluationStrategy.DEEPEVAL, DeepEvalEvaluator(config))
        logger.info("Registered DeepEval evaluator")
    except ImportError:
        logger.warning("DeepEval evaluator not available")
    
    return evaluator
