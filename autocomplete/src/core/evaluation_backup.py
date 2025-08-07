# src/core/evaluation_backup.py
# Backup of the original full-featured evaluation module (pair-wise + holistic).
# This file was created to preserve the previous functionality before simplifying
# src/core/evaluation.py to holistic-only evaluation.

import os
from typing import Optional, Tuple, Any, Dict, List
from dotenv import load_dotenv

from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval
from deepeval.metrics.g_eval import Rubric
from deepeval.models.base_model import DeepEvalBaseLLM

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

# --- METRIC 1: Pair-Wise Semantic Match (Building Block) ---
# This metric is for scoring one Solr result against one Google result.
pair_wise_relevancy_metric = GEval(
    name="POI Pair-Wise Semantic Relevancy",
    criteria="Evaluate if the 'Actual Output' (Solr) and 'Expected Output' (Google) refer to the exact same real-world Point of Interest.",
    evaluation_steps=[
        "1. Compare the POI names and location context (street, city).",
        "2. Determine if they are the same physical place. Penalize heavily for same brand in different locations.",
    ],
    rubric=[
        Rubric(criteria="Unrelated POIs.", score_range=(0, 1), expected_outcome="Score 0-1"),
        Rubric(criteria="Similar name, different locations.", score_range=(2, 4), expected_outcome="Score 2-4"),
        Rubric(criteria="Likely the same but with ambiguous details.", score_range=(5, 7), expected_outcome="Score 5-7"),
        Rubric(criteria="Clearly the same POI with minor differences.", score_range=(8, 9), expected_outcome="Score 8-9"),
        Rubric(criteria="Perfect or near-perfect semantic match.", score_range=(10, 10), expected_outcome="Score 10"),
    ],
    model=judge_llm,
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT]
)

# --- METRIC 2: Holistic Set Evaluation (Final Judgment) ---
# This metric evaluates the ENTIRE list of results from Solr against the list from Google.
holistic_set_relevancy_metric = GEval(
    name="Holistic Search Result Quality",
    criteria="Evaluate the overall quality of the 'Actual Output' list of POIs (from our Solr API) compared to the 'Expected Output' list (the ground truth from Google's API) for the given 'Input' (the user's query).",
    evaluation_steps=[
        "1. **Coverage**: Does the Solr list contain the most important and relevant POIs shown in the Google list? Penalize heavily if key results are missing.",
        "2. **Precision**: How many irrelevant or noisy results are in the Solr list? A high amount of noise should significantly lower the score, even if the correct result is present.",
        "3. **Ranking**: Is the most relevant result ranked highly in the Solr list? Finding the right POI at position #1 is much better than at position #20.",
        "4. **Overall Impression**: Based on the above, provide a single score reflecting the overall quality of the search experience from the user's perspective."
    ],
    rubric=[
        Rubric(criteria="The Solr results are useless or completely irrelevant.", score_range=(0, 1), expected_outcome="Useless results."),
        Rubric(criteria="The results are noisy but contain a weakly relevant POI ranked very low.", score_range=(2, 4), expected_outcome="Very poor quality with some relevance."),
        Rubric(criteria="The correct POI is found, but the list is very noisy and/or the ranking is poor.", score_range=(5, 6), expected_outcome="Acceptable, but has significant flaws."),
        Rubric(criteria="The correct POI is ranked highly, with a moderate amount of noise.", score_range=(7, 8), expected_outcome="Good quality, useful to the user."),
        Rubric(criteria="The results are highly relevant, well-ranked, and contain minimal noise. The experience is comparable to or better than Google's.", score_range=(9, 10), expected_outcome="Excellent quality."),
    ],
    model=judge_llm,
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT]
)

def evaluate_single_pair(solr_poi: Dict, google_poi: Dict) -> Dict:
    """Uses the pair-wise metric to evaluate one Solr POI against one Google POI."""
    if not google_poi or not google_poi.get('main_text'):
        return {"score": 0, "reasoning": "Google POI was empty."}

    actual_output = f"Name: {solr_poi.get('poi_name', '')}, Context: {solr_poi.get('container', '')}"
    expected_output = f"Name: {google_poi.get('main_text', '')}, Context: {google_poi.get('secondary_text', '')}"
    
    test_case = LLMTestCase(input="N/A", actual_output=actual_output, expected_output=expected_output)
    pair_wise_relevancy_metric.measure(test_case)
    return {"score": pair_wise_relevancy_metric.score, "reasoning": pair_wise_relevancy_metric.reason}

def evaluate_holistic_set(query: str, solr_list: List[Dict], google_list: List[Dict]) -> Dict:
    """Uses the holistic metric to evaluate the entire set of results."""
    solr_formatted = "\n".join([f"- {r.get('poi_name', '')} ({r.get('container', '')})" for r in solr_list])
    google_formatted = "\n".join([f"- {r.get('main_text', '')} ({r.get('secondary_text', '')})" for r in google_list])

    test_case = LLMTestCase(input=f"User query: '{query}'", actual_output=solr_formatted, expected_output=google_formatted)
    holistic_set_relevancy_metric.measure(test_case)
    return {"score": holistic_set_relevancy_metric.score, "reasoning": holistic_set_relevancy_metric.reason}
