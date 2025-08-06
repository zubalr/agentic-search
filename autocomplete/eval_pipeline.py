# eval_pipeline.py

from deepeval.test_case import LLMTestCase
from evaluation_metric import semantic_relevancy_metric  # Import our custom metric


def evaluate_poi_relevancy(solr_result: dict, google_result: dict):
    """
    Formats the API data and evaluates the semantic relevancy using our custom deepeval metric.

    Args:
        solr_result (dict): A dictionary containing the mapped fields from your Solr API.
            Expected keys: solr_name, solr_poiName, solr_containerName
        google_result (dict): A dictionary containing the mapped fields from the Google Places API.
            Expected keys: google_place_prediction_text, google_main_text, google_secondary_text

    Returns:
        A dictionary containing the evaluation score and the LLM's reasoning.
    """

    # Format the 'Actual Output' from your Solr API for the LLM judge
    actual_output = (
        f"POI Name: {solr_result.get('solr_poiName', 'N/A')}\n"
        f"Context/Area: {solr_result.get('solr_containerName', 'N/A')}\n"
        f"Full Label: {solr_result.get('solr_name', 'N/A')}"
    )

    # Format the 'Expected Output' (ground truth) from Google's API
    expected_output = (
        f"POI Name: {google_result.get('google_main_text', 'N/A')}\n"
        f"Context/Area: {google_result.get('google_secondary_text', 'N/A')}\n"
        f"Full Label: {google_result.get('google_place_prediction_text', 'N/A')}"
    )

    # Create a 'LLMTestCase' which is the standard input for a deepeval metric.
    test_case = LLMTestCase(
        input="User searched for a POI.",
        actual_output=actual_output,
        expected_output=expected_output,
    )

    # Run the measurement. This is where the LLM call happens via deepeval + litellm (Cerebras).
    metric = semantic_relevancy_metric
    metric.measure(test_case)

    return {
        "score": metric.score,
        "reasoning": metric.reason,
    }
