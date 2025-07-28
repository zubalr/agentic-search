# Agentic Search LLM Judge System

A modular, well-structured system for fetching, processing, and evaluating search results using LLM-based judges and various evaluation frameworks.

## 🏗️ Project Structure

```
src/
├── core/                   # Core business logic
│   ├── api_client.py      # API interaction (Solr, Google Places)
│   ├── data_processor.py  # Data processing operations
│   └── evaluator.py       # Evaluation coordinator
├── evaluation/            # Evaluation and comparison
│   ├── llm_judge.py      # LLM-based judging
│   ├── deepeval_runner.py # DeepEval integration
│   └── comparison.py     # Result comparison logic
├── data/                 # Data management
│   ├── io.py            # Data I/O operations
│   └── models.py        # Data models/schemas
└── utils/               # Utility functions
    ├── config.py        # Configuration management
    └── logger.py        # Logging utilities

scripts/                 # CLI entry points
├── main.py             # Main CLI interface
├── fetch_data.py       # Data fetching script
├── process_data.py     # Data processing script
└── evaluate.py         # Evaluation script

data/                   # Data files
├── Analytics.json      # Input analytics data
└── representative_keywords_with_location.csv

raw/                    # Raw API results
output/                 # Processed results and comparisons
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r config/requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```bash
# Required for LLM evaluation
CEREBRAS_API_KEY=your_cerebras_key
GROQ_API_KEY=your_groq_key

# Required for Google Places API
GOOGLE_PLACES_API_KEY=your_google_places_key
```

### 3. Complete Workflow

#### Step 1: Process Keywords

```bash
# Extract and process keywords from analytics data
python scripts/process_data.py --analytics-file data/Analytics.json --max-keywords 500
```

#### Step 2: Fetch API Data

```bash
# Fetch data from both Solr and Google Places APIs
python scripts/fetch_data.py --source both --keywords-file data/representative_keywords_with_location.csv
```

#### Step 3: Evaluate Results

```bash
# Compare results using LLM judge
python scripts/evaluate.py --mode batch --evaluator llm_judge
```

### 4. Using the Main CLI

```bash
# All-in-one interface
python scripts/main.py --help

# Process data
python scripts/main.py process --analytics-file data/Analytics.json

# Fetch data
python scripts/main.py fetch --source both

# Evaluate results
python scripts/main.py evaluate --mode batch --evaluator llm_judge
```

## 📖 Detailed Usage

### Data Processing

Process analytics data to extract and prepare keywords:

```bash
# Basic processing
python scripts/process_data.py

# Custom configuration
python scripts/process_data.py \
  --analytics-file custom/analytics.json \
  --max-keywords 1000 \
  --output-dir processed_data \
  --lat 25.2048 \
  --lng 55.2708  # Dubai coordinates
```

### Data Fetching

Fetch data from APIs using processed keywords:

```bash
# Fetch from both APIs
python scripts/fetch_data.py --source both

# Fetch specific range
python scripts/fetch_data.py --source solr --range 0 100

# Fetch specific keywords
python scripts/fetch_data.py --source google --keywords "restaurant,hotel,cafe"

# Custom keywords file
python scripts/fetch_data.py --source both --keywords-file custom/keywords.csv
```

### Evaluation

Compare search results using different evaluation methods:

```bash
# LLM Judge evaluation (batch mode)
python scripts/evaluate.py --mode batch --evaluator llm_judge

# Sequential processing (for rate limits)
python scripts/evaluate.py --mode sequential --evaluator llm_judge --delay 5

# DeepEval evaluation (requires existing comparisons)
python scripts/evaluate.py --evaluator deepeval --model cerebras/llama3-70b-instruct

# Custom model
python scripts/evaluate.py --evaluator llm_judge --model "groq/llama3-8b-8192"
```

## 🔧 Configuration

### Environment Variables

```bash
# API Keys
CEREBRAS_API_KEY=your_key
GROQ_API_KEY=your_key
GOOGLE_PLACES_API_KEY=your_key

# File Paths
INTERNAL_RESULTS_FILE=raw/api_results_solr.jsonl
GOOGLE_RESULTS_FILE=raw/google_places_results.jsonl
COMPARISON_MEMORY_FILE=output/comparison_memory.jsonl

# Processing Settings
BATCH_SIZE=5
DELAY_BETWEEN_BATCHES=10
```

### Custom Configuration

```python
from src.utils.config import get_config

config = get_config()
config.batch_size = 10
config.delay_between_batches = 5.0
```

## 📊 Output Files

### Processed Keywords

- `data/sorted_keywords.txt` - All keywords sorted alphabetically
- `data/unique_sorted_keywords.txt` - Deduplicated keywords
- `data/representative_keywords.txt` - Top N representative keywords
- `data/representative_keywords_with_location.csv` - Keywords with location data

### API Results

- `raw/api_results_solr.jsonl` - Solr API results
- `raw/google_places_results.jsonl` - Google Places API results
- `raw/*_failed.jsonl` - Failed API requests

### Evaluation Results

- `output/comparison_memory.jsonl` - LLM judge comparisons
- `output/comparison_memory_summary.json` - Evaluation summary
- `output/*_deepeval.json` - DeepEval results

## 🔍 Key Features

### Modular Architecture

- **Separation of Concerns**: Core logic, evaluation, data management, and utilities are clearly separated
- **Pluggable Evaluators**: Easy to add new evaluation methods
- **Configurable**: Extensive configuration options via environment variables and files

### Robust API Handling

- **Retry Logic**: Automatic retry with exponential backoff
- **Rate Limiting**: Configurable delays and batch sizes
- **Error Handling**: Comprehensive error logging and recovery

### Flexible Evaluation

- **Multiple Strategies**: LLM Judge, DeepEval, and extensible for more
- **Batch and Sequential Modes**: Choose based on rate limits and requirements
- **Resume Capability**: Skip already processed queries

### Data Processing Pipeline

- **Keyword Extraction**: From analytics data
- **Deduplication**: Remove duplicate keywords
- **Representative Selection**: Choose most important keywords
- **Location Enhancement**: Add geographical context

## 🛠️ Development

### Adding New API Clients

```python
from src.core.api_client import APIClient, APIResponse, APIQuery

class CustomAPIClient(APIClient):
    def search(self, query: APIQuery) -> APIResponse:
        # Implement your API logic
        pass
```

### Adding New Evaluators

```python
from src.core.evaluator import BaseEvaluatorInterface, EvaluationMode

class CustomEvaluator(BaseEvaluatorInterface):
    def evaluate(self, internal_results, google_results, mode, **kwargs):
        # Implement your evaluation logic
        pass

    def get_metrics(self):
        return ["custom_metric_1", "custom_metric_2"]
```

### Running Tests

```bash
# Run existing tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_data_io.py -v
```

## 🚨 Important Notes

### Removed Files

The following scripts have been **removed** as they're no longer needed:

- All scripts without location support (fetch_api_data.py, etc.)
- Individual keyword processing scripts
- Redundant evaluation scripts

### API Rate Limits

- **Solr API**: 30 requests per minute (default: 5 requests every 10 seconds)
- **Google Places API**: Varies by plan (configure delays accordingly)
- **LLM APIs**: Varies by provider (Cerebras, Groq have different limits)

### Required Files

Ensure these files exist before running:

- `data/Analytics.json` - Source analytics data
- Environment variables or `.env` file with API keys

## 🤝 Contributing

1. Follow the modular structure
2. Add comprehensive logging
3. Include error handling
4. Update documentation
5. Add tests for new features

## 📝 License

See `config/LICENSE` for license information.

```
CEREBRAS_API_KEY=your-cerebras-key
GROQ_API_KEY=your-groq-key
OPENAI_API_KEY=sk-...
```

## Usage

Run the system in batch or sequential mode:

```bash
python scripts/main.py --mode batch
python scripts/main.py --mode sequential
```

## Evaluation (DeepEval + LiteLLM: Plug-and-Play Any Provider/Model)

1. Set your API key for the provider you want to use (Cerebras, Groq, OpenAI, etc.):
   ```bash
   # For Cerebras
   export CEREBRAS_API_KEY=your-cerebras-key
   # For Groq
   export GROQ_API_KEY=your-groq-key
   # For OpenAI
   export OPENAI_API_KEY=sk-...
   # ...and so on for any LiteLLM-supported provider
   ```
2. Run the evaluation runner via the unified CLI:
   ```bash
   # For Cerebras
   python scripts/eval.py deepeval --results comparison_memory.jsonl --model cerebras/llama3-70b-instruct
   # For Groq
   python scripts/eval.py deepeval --results comparison_memory.jsonl --model groq/llama3-8b-8192
   # For OpenAI
   python scripts/eval.py deepeval --results comparison_memory.jsonl --model openai/gpt-3.5-turbo
   # Optionally add --references human_labels.jsonl if you have human gold labels
   ```

You can swap providers/models by just changing the `--model` argument and setting the right API key. See [LiteLLM docs](https://github.com/BerriAI/litellm) for all supported providers/models.

## Configuration

You can override file paths and model configs via environment variables or by editing `agent_judge/config.py`.

## Extending

- Add new LLM providers by extending `LLMManager` in `llm_judge.py`.
- Add new evaluation criteria by editing the prompt in `llm_judge.py`.
- Add more CLI options in `scripts/main.py`.

## Best Practices for LLM as Judge

- Use clear, structured prompts and schemas.
- Aggregate judgments from multiple LLMs for robustness.
- Log all LLM responses for audit and reproducibility.

## License

See `config/LICENSE`.
