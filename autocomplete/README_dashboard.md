# POI Evaluation Dashboard

A comprehensive Streamlit dashboard for visualizing and analyzing POI (Point of Interest) evaluation results.

## Features

- 📊 **Interactive Visualizations**: Score distribution, category breakdowns, and detailed metrics
- 🔍 **Search & Filter**: Find specific queries and filter by score categories
- 📋 **Detailed Results Table**: View all evaluation results with formatted scores
- 🎯 **Performance Metrics**: Average score, success rate, and match statistics
- 💾 **Export Functionality**: Download filtered results as CSV or JSON
- 📱 **Responsive Design**: Works well on desktop and mobile devices

## Quick Start

1. **Install Dependencies**:
   ```bash
   uv add streamlit pandas plotly numpy
   ```

2. **Run the Dashboard**:
   ```bash
   python run_dashboard.py
   ```

3. **Open in Browser**: Navigate to `http://localhost:8501`

## Manual Run

Alternatively, you can run the dashboard directly with Streamlit:

```bash
streamlit run src/dashboard.py
```

## Data Requirements

The dashboard expects a CSV file at `data/results/evaluation_results.csv` with the following columns:
- `query`: The search query
- `score`: The evaluation score (0.0 to 1.0)
- `reasoning`: The LLM's reasoning for the score

## Dashboard Sections

### 1. Overview Metrics
- Average Score
- Perfect Matches (score = 1.0)
- No Matches (score = 0.0)
- Success Rate

### 2. Visualizations
- **Score Distribution**: Histogram showing the distribution of scores
- **Score Categories**: Pie chart breaking down results into categories

### 3. Detailed Results
- Searchable and filterable table of all evaluation results
- Color-coded scores (green for high, orange for medium, red for low)
- Export functionality for filtered results

### 4. Detailed Analysis
- Expandable sections for queries with low scores
- Shows query, score, and reasoning for problematic cases

## Customization

### Styling
The dashboard uses custom CSS for a polished look. You can modify the styles in `src/dashboard.py` by editing the `st.markdown()` CSS section.

### Data Source
By default, the dashboard looks for `data/results/evaluation_results.csv`. You can change this by modifying the `csv_path` variable in the `load_data()` function.

### Visualizations
The dashboard uses Plotly for interactive charts. You can customize the charts by modifying the Plotly code in the main function.

## Troubleshooting

### Common Issues

1. **Data file not found**: Make sure `data/results/evaluation_results.csv` exists and is in the correct location.
2. **Dependencies not installed**: Run `uv add streamlit pandas plotly numpy` to install required packages.
3. **Port already in use**: Change the port in `run_dashboard.py` or stop the existing Streamlit server.

### Error Messages

- "Data file not found at data/results/evaluation_results.csv": Check that the CSV file exists at the specified path.
- "Error loading data": Verify that the CSV file has the correct format with columns for query, score, and reasoning.

## Contributing

To add new features or modify existing ones:

1. Edit `src/dashboard.py`
2. Test your changes by running the dashboard
3. Update this README if you add new features

## License

This project is part of the agentic-search project.
