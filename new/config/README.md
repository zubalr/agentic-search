# agentic-search

Agentic Search is a Python-based toolkit for running and comparing search queries using both internal Solr APIs and the Google Places API. It is designed for batch processing, result comparison, and robust error handling, making it ideal for analytics and data validation tasks.

## Features

- Batch querying of Solr and Google Places APIs
- Automatic retry and exponential backoff for failed requests
- Logging and error tracking
- Result and failure output in JSONL format for easy analysis
- Environment variable support for API keys

## Requirements

Install dependencies using pip:

```bash
pip install -r requirements.txt
```

## Setup

1. Clone the repository.
2. Create a `.env` file in the root directory and add your Google Places API key:
   ```
   GOOGLE_PLACES_API_KEY=your_api_key_here
   ```
3. Place your input queries in `analytics.json` (see example structure below).

## Usage

### Fetch data from Solr API

```bash
python fetch_api_data.py
```

### Fetch data from Google Places API

```bash
python fetch_google_places_data.py
```

### Compare results

Use `compare_search_results.py` to analyze and compare outputs from both APIs.

## Input File Format

Your `analytics.json` should contain:

```json
{
  "SEARCH KEYWORDS": [
    {"payload": "{\"searchKeyword\": \"example\", \"originLat\": 0.0, \"originLng\": 0.0}"},
    ...
  ]
}
```

## Output

- Results and failures are saved in JSONL files for each batch.

## License

This project is licensed under the MIT License.
