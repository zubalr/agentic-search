# Simple Configuration Runner

This directory contains a simplified configuration-based runner for the agentic search system.

## Quick Start

1. **Edit the configuration file** (`config.json`) to set your parameters:

   ```json
   {
     "keywords": {
       "file": "data/representative_keywords_with_location.csv",
       "start_index": 0,
       "end_index": 100,
       "use_range": true,
       "batch_size": 50
     },
     "apis": {
       "fetch_from": "both" // "solr", "google", or "both"
     }
   }
   ```

2. **Run the system**:
   ```bash
   python run.py
   ```

## Configuration Options

### Keywords Settings

- `file`: Path to your keywords CSV file
- `start_index`: Starting index for keyword processing (0-based)
- `end_index`: Ending index for keyword processing
- `use_range`: Whether to process only a range of keywords

### Processing Settings (Sequential by Default)

- `mode`: Processing mode ("sequential" or "batch") - sequential is default
- `delay_between_requests`: Delay in seconds between each API request (default: 2.0)
- `delay_between_apis`: Delay between different APIs when using both (default: 1.0)

### Batch Processing (Commented Out)

Batch processing options are available but commented out with `_` prefix:

- `_batch_size`: Number of keywords to process in each batch
- `_delay_between_batches`: Delay between batches
- `_max_concurrent`: Maximum concurrent requests

To enable batch processing, uncomment the options and set `"mode": "batch"`

### API Settings

- `fetch_from`: Which APIs to use ("solr", "google", or "both")
- Individual API configurations for timeouts and retries

### Output Settings

- `raw_dir`: Directory for raw API results
- `output_dir`: Directory for processed results
- `include_range_in_filename`: Add range suffix to output files

### Evaluation Settings

- `run_evaluation`: Whether to run LLM evaluation after fetching
- `llm_provider`: LLM provider ("cerebras" or "groq")
- `model`: Model name to use

## Example Workflows

### Test with Small Range

```bash
# Use the test config for quick testing
python run.py --config config_test.json
```

### Full Processing

```bash
# Edit config.json to set full range
# Set "use_range": false or adjust start_index/end_index
python run.py
```

### Dry Run (Check Configuration)

```bash
python run.py --dry-run
```

## File Outputs

Based on your configuration, files will be saved as:

- `raw/api_results_solr_0_100.jsonl` (if range is 0-100)
- `raw/google_places_results_0_100.jsonl`
- `output/comparison_results_0_100.jsonl` (if evaluation is enabled)

## Environment Variables

Make sure you have these environment variables set:

```bash
export GOOGLE_PLACES_API_KEY="your_api_key"
export CEREBRAS_API_KEY="your_api_key"  # if using evaluation
export GROQ_API_KEY="your_api_key"      # if using evaluation
```

## Quick Configuration Examples

### Only Solr API, First 50 Keywords (Sequential)

```json
{
  "keywords": { "start_index": 0, "end_index": 50, "use_range": true },
  "apis": { "fetch_from": "solr" },
  "processing": { "mode": "sequential", "delay_between_requests": 1.5 },
  "evaluation": { "run_evaluation": false }
}
```

### Both APIs, Keywords 100-200 with Evaluation (Sequential)

```json
{
  "keywords": { "start_index": 100, "end_index": 200, "use_range": true },
  "apis": { "fetch_from": "both" },
  "processing": {
    "mode": "sequential",
    "delay_between_requests": 2.0,
    "delay_between_apis": 1.0
  },
  "evaluation": { "run_evaluation": true }
}
```

### Fast Processing with Batch Mode

```json
{
  "processing": {
    "mode": "batch"
  },
  "_batch_processing_options": {
    "batch_size": 25,
    "delay_between_batches": 3.0,
    "max_concurrent": 5
  }
}
```
