# evaluation_metric.py

import os
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams
from deepeval.metrics.g_eval import Rubric
from deepeval.models.base_model import DeepEvalBaseLLM
from typing import Optional, Tuple, Any

# Resolve model from env with default to requested Cerebras model
MODEL_NAME = os.getenv("LITELLM_MODEL", "cerebras/llama3.3-70b")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

class LiteLLMCerebrasModel(DeepEvalBaseLLM):
    """
    Adapter to let deepeval use litellm with Cerebras as the judge model.
    Implements required sync/async raw response interfaces returning an OpenAI-like object and cost.
    """

    def __init__(self, model_name: str, api_key: Optional[str] = None):
        super().__init__()
        # lazy imports to avoid hard deps during import time
        from litellm import completion, acompletion  # type: ignore
        self._completion = completion
        self._acompletion = acompletion
        self._model_name = model_name
        self._api_key = api_key

    def load_model(self):
        return

    def get_model_name(self) -> str:
        return self._model_name

    # DeepEval expects these "raw response" methods to return (text, cost)
    def generate_raw_response(self, prompt: str, **kwargs) -> Tuple[Any, float]:
        """
        Return an object compatible with OpenAI's ChatCompletion so deepeval can access:
        res.choices[0].message.content
        """
        resp = self._completion(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
            api_key=self._api_key,
        )
        # resp from litellm already mimics OpenAI format; return as-is so deepeval can read .choices[0].message.content
        return resp, 0.0

    async def a_generate_raw_response(self, prompt: str, **kwargs) -> Tuple[Any, float]:
        """
        Async variant returning an OpenAI-like response object.
        """
        resp = await self._acompletion(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
            api_key=self._api_key,
        )
        return resp, 0.0

    # Backwards-compatible helpers if DeepEval calls these
    def generate(self, prompt: str, **kwargs) -> str:
        text, _ = self.generate_raw_response(prompt, **kwargs)
        return text

    async def a_generate(self, prompt: str, **kwargs) -> str:
        text, _ = await self.a_generate_raw_response(prompt, **kwargs)
        return text

# Instantiate our adapter
_cerebras_model = LiteLLMCerebrasModel(model_name=MODEL_NAME, api_key=CEREBRAS_API_KEY)

# Define the semantic relevancy metric using GEval
# This metric will be used by an LLM (via litellm configured for Cerebras) to judge the results.
semantic_relevancy_metric = GEval(
    name="POI Semantic Relevancy",
    criteria="Evaluate whether the 'Actual Output' (your API) refers to the same real-world Point of Interest as the 'Expected Output' (Google's API).",
    evaluation_steps=[
        "1. Compare the primary POI names (`solr_poiName` vs. `google_main_text`). Are they identical or synonyms (e.g., 'Starbucks' vs. 'Starbucks Coffee')?",
        "2. Analyze the context/address information (`solr_containerName` vs. `google_secondary_text`). Do they specify the same location (street, city, etc.)?",
        "3. Based on both name and context, determine if a user would consider both results to be for the exact same physical place.",
        "4. Penalize heavily if the locations are different (e.g., same brand, but different branch in another part of the city)."
    ],
    rubric=[
        Rubric(
            score_range=(0, 1),
            expected_outcome="Completely different and unrelated POIs.",
            criteria="Names and locations do not match; no semantic overlap."
        ),
        Rubric(
            score_range=(2, 4),
            expected_outcome="Similar names but clearly different locations.",
            criteria="Same/similar brand but different city or distant neighborhood."
        ),
        Rubric(
            score_range=(5, 7),
            expected_outcome="Likely same brand/entity and geographically close but ambiguous details.",
            criteria="Address/context slightly mismatched; could cause confusion."
        ),
        Rubric(
            score_range=(8, 9),
            expected_outcome="Clearly the same POI with minor naming/formatting differences.",
            criteria="Only inconsequential variations (e.g., St vs Street, postal code)."
        ),
        Rubric(
            score_range=(10, 10),
            expected_outcome="Perfect or near-perfect semantic match for the exact same physical entity.",
            criteria="Name and location context fully align."
        ),
    ],
    # Plug in our litellm-based Cerebras adapter so deepeval does not enforce OpenAI model list
    model=_cerebras_model,
    evaluation_params=[
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT
    ],
)
