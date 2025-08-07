
---

# Prompt for Coding Agent: Building a DeepEval POI Comparison Pipeline

## 1. Objective

Your task is to create a complete Python project that evaluates the **semantic relevancy** of our internal Solr-based POI (Point of Interest) search API against the Google Places Autocomplete API. You will use the `deepeval` framework to perform a pairwise comparison for each search query. The evaluation will be judged by an LLM (accessed via `litellm` with Cerebras), which will score how closely our API's suggestions match Google's, based on predefined criteria.

This project directly adapts the methodology presented in the provided article about comparing code generation models (Qwen vs. Sonnet).

## 2. Project Structure

Create the following file structure:

```
.
├── .env
├── evaluation_metric.py
├── eval_pipeline.py
└── run_evaluation.py
```

## 3. Step-by-Step Implementation

### Step 3.1: Environment Setup & Configuration

First, ensure your environment is set up correctly.

-   **Virtual Environment**: You are using `uv`. Make sure the following packages are installed:
    ```shell
    uv pip install deepeval litellm python-dotenv pandas
    ```
-   **.env File**: Create a file named `.env` to store your API keys securely. `deepeval` will automatically use the `CEREBRAS_API_KEY` for its LLM judge, and `litellm` should be configured to use any provider and CEREBRAS.

    ```dotenv
    # .env

    # Used by deepeval's G-Eval metric by default with configuring litellm for Cerebras
    CEREBRAS_API_KEY="your-cerebras-key"
    ```

### Step 3.2: Define the Custom Evaluation Metric (`evaluation_metric.py`)

This is the core of our evaluation. We will define the rules for the LLM judge. The criteria will focus on whether the two API responses refer to the same real-world location.

Create the file `evaluation_metric.py`:

```python
# evaluation_metric.py

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams
from deepeval.metrics.g_eval import Rubric

# Define the semantic relevancy metric using GEval
# This metric will be used by an LLM to "judge" the results.
semantic_relevancy_metric = GEval(
    name="POI Semantic Relevancy",
    criteria="Evaluate whether the 'Actual Output' (your API) refers to the same real-world Point of Interest as the 'Expected Output' (Google's API).",
    evaluation_steps=[
        "1. Compare the primary POI names (`solr_poiName` vs. `google_main_text`). Are they identical or synonyms (e.g., 'Starbucks' vs. 'Starbucks Coffee')?",
        "2. Analyze the context/address information (`solr_containerName` vs. `google_secondary_text`). Do they specify the same location (street, city, etc.)?",
        "3. Based on both name and context, determine if a user would consider both results to be for the exact same physical place.",
        "4. Penalize heavily if the locations are different (e.g., same brand, but different branch in another part of the city)."
    ],
    rubric=Rubric(
        score_range=(0, 10),
        # Define what each score means
        criteria={
            "(0-1)": "The POIs are completely different and unrelated.",
            "(2-4)": "The POIs share a similar name but are in clearly different locations (e.g., different cities or distant neighborhoods).",
            "(5-7)": "The POIs are for the same brand/entity and are geographically close, but the address details are ambiguous or slightly mismatched, potentially causing confusion.",
            "(8-9)": "The POIs are clearly the same, with only minor, inconsequential differences in naming or formatting (e.g., 'St' vs. 'Street', including/excluding postal code).",
            "(10)": "The POI name and location context are a perfect or near-perfect semantic match, referring to the exact same physical entity."
        }
    ),
    # The LLM that will perform the evaluation
    # Make sure your API key is set in the .env file
    # You can swap this with a litellm-compatible model like "cerebras/..."
    model="gpt-4o", 
    
    # We provide both our result and Google's result for comparison
    evaluation_params=[
        LLMTestCaseParams.ACTUAL_OUTPUT, 
        LLMTestCaseParams.EXPECTED_OUTPUT
    ]
)
```

### Step 3.3: Create the Evaluation Pipeline (`eval_pipeline.py`)

This file will contain the function that takes your data, formats it for `deepeval`, and runs the metric we just defined.

Create the file `eval_pipeline.py`:

```python
# eval_pipeline.py

from deepeval.test_case import LLMTestCase
from evaluation_metric import semantic_relevancy_metric # Import our custom metric

def evaluate_poi_relevancy(solr_result: dict, google_result: dict):
    """
    Formats the API data and evaluates the semantic relevancy using our custom deepeval metric.

    Args:
        solr_result (dict): A dictionary containing the mapped fields from your Solr API.
        google_result (dict): A dictionary containing the mapped fields from the Google Places API.
        
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
    # The 'input' field is a placeholder for context about the original user query.
    test_case = LLMTestCase(
        input=f"User searched for a POI.",
        actual_output=actual_output,
        expected_output=expected_output
    )
    
    # Run the measurement. This is where the LLM call happens.
    metric = semantic_relevancy_metric
    metric.measure(test_case)
    
    return {
        "score": metric.score,
        "reasoning": metric.reason
    }
```

### Step 3.4: Main Execution Script (`run_evaluation.py`)

This script ties everything together. It will load your collected data, loop through each row, call the evaluation pipeline, and print a final report.

Create the file `run_evaluation.py`:

```python
# run_evaluation.py

import pandas as pd
from dotenv import load_dotenv
from eval_pipeline import evaluate_poi_relevancy

# Load API keys from .env file
load_dotenv()

def main():
    """
    Main function to run the full evaluation pipeline.
    """
    # --- 1. Load Your Data ---
    # For this example, we will use a sample DataFrame.
    # In your real use case, you would load your CSV from `fetch_autocomplete_with_latlng.py`.
    # For example: df = pd.read_csv('your_api_comparison_data.csv')
    
    data = {
        'query': ['starbucks near park ave', 'museum of art', 'pizza hut 5th ave', 'library downtown'],
        'solr_name': ['Starbucks, 10 Park Ave, New York', 'Metropolitan Museum of Art', 'Pizza Hut', 'Central Library, 4th St'],
        'solr_poiName': ['Starbucks', 'Metropolitan Museum', 'Pizza Hut', 'Central Library'],
        'solr_containerName': ['10 Park Ave, New York', 'Art', '5th Avenue', 'Downtown'],
        'google_place_prediction_text': ['Starbucks, 10 Park Avenue, New York, NY, USA', 'The Metropolitan Museum of Art, 5th Avenue, New York, NY, USA', 'Pizza Hut, 456 5th Ave, New York, NY, USA', 'New York Public Library, Main Branch, 5th Ave, New York, NY, USA'] ,
        'google_main_text': ['Starbucks', 'The Metropolitan Museum of Art', 'Pizza Hut', 'New York Public Library, Main Branch'],
        'google_secondary_text': ['10 Park Avenue, New York, NY, USA', '5th Avenue, New York, NY, USA', '456 5th Ave, New York, NY, USA', '5th Ave, New York, NY, USA']
    }
    df = pd.DataFrame(data)

    # --- 2. Run Evaluation Loop ---
    results = []
    for index, row in df.iterrows():
        print(f"Evaluating query: '{row['query']}'...")

        solr_result = {
            'solr_name': row['solr_name'],
            'solr_poiName': row['solr_poiName'],
            'solr_containerName': row['solr_containerName']
        }
        
        google_result = {
            'google_place_prediction_text': row['google_place_prediction_text'],
            'google_main_text': row['google_main_text'],
            'google_secondary_text': row['google_secondary_text']
        }

        # Call the evaluation function
        eval_result = evaluate_poi_relevancy(solr_result, google_result)
        
        # Store results
        results.append({
            'query': row['query'],
            'score': eval_result['score'],
            'reasoning': eval_result['reasoning']
        })

    # --- 3. Aggregate and Display Results ---
    results_df = pd.DataFrame(results)
    average_score = results_df['score'].mean()
    
    print("\n--- Evaluation Complete ---")
    print(f"\nOverall Average Score: {average_score:.2f} / 10")
    
    print("\n--- Detailed Results ---")
    print(results_df.to_string())


if __name__ == "__main__":
    main()

```

## 4. How to Run the Evaluation

1.  **Activate Environment**: Open your terminal and activate your `uv` environment.
2.  **Run the Script**: Execute the main evaluation script from your terminal.

    ```shell
    python run_evaluation.py
    ```

3.  **Analyze Output**: The script will print the evaluation progress and finish with a summary table containing the score and reasoning for each query, along with the overall average score. This gives you both a high-level performance metric and detailed insights for debugging specific mismatches.