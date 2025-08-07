# src/core/evaluation.py

import os
from typing import Optional, Tuple, Any, Dict, List
from dotenv import load_dotenv

from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval
from deepeval.metrics.g_eval import Rubric
from deepeval.models.base_model import DeepEvalBaseLLM

# NOTE:
# This file has been simplified to only perform holistic evaluation (top-5 from each list).
# The original, full-featured version has been backed up at: src/core/evaluation_backup.py

load_dotenv()
MODEL_NAME = os.getenv("LITELLM_MODEL", "cerebras/llama3.3-70b")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

class LiteLLMCerebrasModel(DeepEvalBaseLLM):
    """Robust adapter for using any litellm-supported model with deepeval."""
    def __init__(self, model_name: str, api_key: Optional[str] = None):
        from litellm import completion, acompletion
        self._model_name = model_name
        self._api_key = api_key
        self._completion = completion
        self._acompletion = acompletion
        super().__init__()

    def load_model(self) -> str: return self.get_model_name()
    def get_model_name(self) -> str: return self._model_name
    def generate_raw_response(self, prompt: str, **kwargs) -> Tuple[Any, float]:
        resp = self._completion(model=self._model_name, messages=[{"role": "user", "content": prompt}], api_key=self._api_key)
        return resp, 0.0
    async def a_generate_raw_response(self, prompt: str, **kwargs) -> Tuple[Any, float]:
        resp = await self._acompletion(model=self._model_name, messages=[{"role": "user", "content": prompt}], api_key=self._api_key)
        return resp, 0.0
    def generate(self, prompt: str) -> str:
        return self._completion(model=self.get_model_name(), messages=[{"role": "user", "content": prompt}]).choices[0].message.content
    async def a_generate(self, prompt: str) -> str:
        return (await self._acompletion(model=self.get_model_name(), messages=[{"role": "user", "content": prompt}])).choices[0].message.content

judge_llm = LiteLLMCerebrasModel(model_name=MODEL_NAME, api_key=CEREBRAS_API_KEY)

# --- METRIC: Holistic Set Evaluation (Top-5) ---
holistic_set_relevancy_metric = GEval(
    name="Holistic Search Result Quality",
    criteria="Evaluate the overall quality of the 'Actual Output' list of POIs (from our Solr API) compared to the 'Expected Output' list (the ground truth from Google's API) for the given 'Input' (the user's query). Consider coverage, precision (noise), and ranking.",
    evaluation_steps=[
        "1. Coverage: Do the Solr top results include the most important POIs shown in the Google list?",
        "2. Precision: How many irrelevant results are in the Solr list?",
        "3. Ranking: Are the best matches ranked near the top?",
        "4. Provide a single score summarizing the search experience.",
    ],
    rubric=[
        Rubric(criteria="The Solr results are useless or completely irrelevant.", score_range=(0, 1), expected_outcome="Useless results."),
        Rubric(criteria="The results are noisy but contain a weakly relevant POI ranked very low.", score_range=(2, 4), expected_outcome="Very poor quality with some relevance."),
        Rubric(criteria="The correct POI is found, but the list is very noisy and/or the ranking is poor.", score_range=(5, 6), expected_outcome="Acceptable, but has significant flaws."),
        Rubric(criteria="The correct POI is ranked highly, with a moderate amount of noise.", score_range=(7, 8), expected_outcome="Good quality, useful to the user."),
        Rubric(criteria="The results are highly relevant, well-ranked, and contain minimal noise.", score_range=(9, 10), expected_outcome="Excellent quality."),
    ],
    model=judge_llm,
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT]
)

def evaluate_holistic_set(query: str, solr_list: List[Dict], google_list: List[Dict]) -> Dict:
    """Evaluate only the top-5 results from each list using the holistic metric."""
    top_k = 5
    solr_top = solr_list[:top_k] if solr_list else []
    google_top = google_list[:top_k] if google_list else []

    solr_formatted = "\n".join([f"- {r.get('poi_name', '')} ({r.get('container', '')})" for r in solr_top])
    google_formatted = "\n".join([f"- {r.get('main_text', '')} ({r.get('secondary_text', '')})" for r in google_top])

    test_case = LLMTestCase(input=f"User query: '{query}'", actual_output=solr_formatted, expected_output=google_formatted)
    holistic_set_relevancy_metric.measure(test_case)
    return {"score": holistic_set_relevancy_metric.score, "reasoning": holistic_set_relevancy_metric.reason}
