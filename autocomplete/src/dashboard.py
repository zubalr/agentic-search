import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import json
import os

# Set page configuration
st.set_page_config(
    page_title="POI Evaluation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .score-high {
        color: #4CAF50;
        font-weight: bold;
    }
    .score-medium {
        color: #FF9800;
        font-weight: bold;
    }
    .score-low {
        color: #F44336;
        font-weight: bold;
    }
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    .stExpander {
        border-radius: 10px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def load_data():
    """
    Load the advanced evaluation results JSONL file and normalize into DataFrames.

    Returns:
        dict with:
            - df_queries: per-query records with top-level fields and flattened metrics
            - df_poi_coverage: per-query-per-POI coverage rows
            - summary: computed aggregates
    """
    jsonl_path = "data/results/advanced_evaluation_report.jsonl"
    if not os.path.exists(jsonl_path):
        st.error(f"Data file not found at {jsonl_path}")
        return None

    records = []
    poi_rows = []

    try:
        # Reader that supports both JSONL (one JSON per line) and pretty-printed multi-line JSON objects.
        def iter_json_objects(stream):
            buffer = ""
            depth = 0
            in_string = False
            escape = False

            def try_yield_from_buffer():
                nonlocal buffer, depth, in_string, escape
                if buffer.strip():
                    try:
                        obj = json.loads(buffer)
                        yield obj
                        buffer = ""
                        depth = 0
                        in_string = False
                        escape = False
                    except Exception:
                        # Keep accumulating if not yet valid JSON
                        pass

            for raw in stream:
                stripped = raw.strip()
                if not buffer:
                    # Fast path: attempt to parse single-line JSON
                    if stripped:
                        try:
                            yield json.loads(stripped)
                            continue
                        except Exception:
                            # fall through to accumulation mode
                            pass

                # Accumulate characters while tracking JSON string and brace depth
                for ch in raw:
                    buffer += ch
                    if in_string:
                        if escape:
                            escape = False
                        elif ch == "\\":
                            escape = True
                        elif ch == '"':
                            in_string = False
                        continue
                    else:
                        if ch == '"':
                            in_string = True
                        elif ch in "{[":
                            depth += 1
                        elif ch in "}]":
                            depth = max(0, depth - 1)

                # If depth is balanced and buffer contains something, try to parse
                if depth == 0:
                    yield from try_yield_from_buffer()

            # Flush remaining buffer
            if depth == 0 and buffer.strip():
                try:
                    yield json.loads(buffer)
                except Exception:
                    pass

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for obj in iter_json_objects(f):
                if not isinstance(obj, dict):
                    continue

                query = obj.get("query")
                holistic_ai_score = obj.get("holistic_ai_score")
                holistic_ai_reasoning = obj.get("holistic_ai_reasoning")

                quantitative = obj.get("quantitative_metrics", {}) or {}
                precision_ratio = quantitative.get("precision_ratio")
                mrr = quantitative.get("mean_reciprocal_rank")
                coverage_per_google_poi = quantitative.get("coverage_per_google_poi", {}) or {}

                raw = obj.get("raw_results", {}) or {}
                solr_count = raw.get("solr_count")
                google_count = raw.get("google_count")

                # Append per-query record
                records.append({
                    "query": query,
                    "holistic_ai_score": holistic_ai_score,
                    "holistic_ai_reasoning": holistic_ai_reasoning,
                    "precision_ratio": precision_ratio,
                    "mean_reciprocal_rank": mrr,
                    "solr_count": solr_count,
                    "google_count": google_count,
                    "num_google_pois": len(coverage_per_google_poi)
                })

                # Flatten POI coverage as separate rows
                for poi_name, metrics in coverage_per_google_poi.items():
                    poi_rows.append({
                        "query": query,
                        "poi_name": poi_name,
                        "poi_score": metrics.get("score"),
                        "poi_rank": metrics.get("rank")
                    })

        df_queries = pd.DataFrame(records)
        df_poi_coverage = pd.DataFrame(poi_rows) if poi_rows else pd.DataFrame(columns=["query", "poi_name", "poi_score", "poi_rank"])

        # Summary stats
        summary = {}
        if not df_queries.empty:
            summary = {
                "total_queries": len(df_queries),
                "avg_holistic_score": float(df_queries["holistic_ai_score"].mean()),
                "avg_precision": float(df_queries["precision_ratio"].mean()),
                "avg_mrr": float(df_queries["mean_reciprocal_rank"].mean()),
                "total_solr_results": int(df_queries["solr_count"].fillna(0).sum()),
                "total_google_pois": int(df_queries["google_count"].fillna(0).sum()),
                "low_quality_count": int((df_queries["holistic_ai_score"] < 0.5).sum()),
                "perfect_solr_precision": int((df_queries["precision_ratio"] == 1.0).sum()),
            }

        return {
            "df_queries": df_queries,
            "df_poi_coverage": df_poi_coverage,
            "summary": summary
        }
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def main():
    st.markdown('<h1 class="main-header">📊 POI Evaluation Dashboard</h1>', unsafe_allow_html=True)

    # Load data
    data = load_data()
    if data is None:
        return
    df = data["df_queries"]
    df_poi = data["df_poi_coverage"]
    summary = data["summary"]
    
    # Display basic info
    st.sidebar.markdown("### 📈 Data Overview")
    st.sidebar.metric("Total Queries", summary.get("total_queries", len(df)))
    st.sidebar.metric("Avg Holistic Score", f"{summary.get('avg_holistic_score', float('nan')):.2f}")
    st.sidebar.metric("Avg Precision", f"{summary.get('avg_precision', float('nan')):.3f}")
    st.sidebar.metric("Avg MRR", f"{summary.get('avg_mrr', float('nan')):.3f}")

    # Holistic score distribution
    if not df.empty:
        score_counts = df['holistic_ai_score'].round(2).value_counts().sort_index()
        st.sidebar.bar_chart(score_counts)
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("### 🎯 Avg Holistic Score")
        avg_score = df['holistic_ai_score'].mean()
        if avg_score >= 0.8:
            score_class = "score-high"
        elif avg_score >= 0.5:
            score_class = "score-medium"
        else:
            score_class = "score-low"
        st.markdown(f'<div class="metric-card"><span class="{score_class}">{avg_score:.2f}</span></div>', unsafe_allow_html=True)

    with col2:
        st.markdown("### 🧮 Total Solr Results")
        st.markdown(f'<div class="metric-card"><span class="score-medium">{summary.get("total_solr_results", 0)}</span></div>', unsafe_allow_html=True)

    with col3:
        st.markdown("### 🧭 Perfect Precision (1.0)")
        st.markdown(f'<div class="metric-card"><span class="score-high">{summary.get("perfect_solr_precision", 0)}</span></div>', unsafe_allow_html=True)

    with col4:
        st.markdown("### ⚠️ Low-quality Queries (< 0.5)")
        st.markdown(f'<div class="metric-card"><span class="score-low">{summary.get("low_quality_count", 0)}</span></div>', unsafe_allow_html=True)
    
    # Score distribution visualization
    st.markdown("### 📊 Holistic Score Distribution")

    # Histogram for holistic score
    if not df.empty:
        fig_hist = px.histogram(
            df, x='holistic_ai_score', nbins=20, title='Holistic AI Score Distribution',
            labels={'holistic_ai_score': 'Holistic AI Score', 'count': 'Number of Queries'},
            color_discrete_sequence=['#1E88E5']
        )
        fig_hist.update_layout(
            xaxis_title="Holistic AI Score",
            yaxis_title="Count",
            bargap=0.1
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    # Pie charts for precision and MRR buckets
    st.markdown("### 🎯 Metric Buckets (Precision, MRR)")

    def bucketize(series, bins, labels):
        return pd.cut(series, bins=bins, labels=labels, include_lowest=True)

    if not df.empty:
        bins = [0.0, 0.2, 0.5, 0.8, 1.0]
        labels = ["0-0.2", "0.2-0.5", "0.5-0.8", "0.8-1.0"]

        df["precision_bucket"] = bucketize(df["precision_ratio"].fillna(0.0), [0.0, 0.2, 0.5, 0.8, 1.0], labels)
        df["mrr_bucket"] = bucketize(df["mean_reciprocal_rank"].fillna(0.0), [0.0, 0.2, 0.5, 0.8, 1.0], labels)

        colA, colB = st.columns(2)
        with colA:
            prec_counts = df["precision_bucket"].value_counts().sort_index()
            fig_prec = px.pie(values=prec_counts.values, names=prec_counts.index, title="Precision Ratio Buckets")
            st.plotly_chart(fig_prec, use_container_width=True)
        with colB:
            mrr_counts = df["mrr_bucket"].value_counts().sort_index()
            fig_mrr = px.pie(values=mrr_counts.values, names=mrr_counts.index, title="MRR Buckets")
            st.plotly_chart(fig_mrr, use_container_width=True)
    
    # Detailed results table
    st.markdown("### 📋 Detailed Results")

    # Add search and filter functionality
    col1, col2, col3 = st.columns(3)

    with col1:
        search_query = st.text_input("🔍 Search queries", placeholder="Enter search term...")

    with col2:
        score_filter = st.selectbox(
            "🎯 Filter by holistic score",
            ["All", "< 0.2", "0.2 - 0.5", "0.5 - 0.8", ">= 0.8"]
        )

    with col3:
        metric_filter = st.selectbox(
            "📐 Sort by metric",
            ["Holistic Score", "Precision", "MRR", "Solr Count", "Google Count"]
        )

    # Apply filters
    filtered_df = df.copy()

    if search_query:
        filtered_df = filtered_df[filtered_df['query'].str.contains(search_query, case=False, na=False)]

    if score_filter != "All":
        if score_filter == "< 0.2":
            filtered_df = filtered_df[filtered_df['holistic_ai_score'] < 0.2]
        elif score_filter == "0.2 - 0.5":
            filtered_df = filtered_df[(filtered_df['holistic_ai_score'] >= 0.2) & (filtered_df['holistic_ai_score'] < 0.5)]
        elif score_filter == "0.5 - 0.8":
            filtered_df = filtered_df[(filtered_df['holistic_ai_score'] >= 0.5) & (filtered_df['holistic_ai_score'] < 0.8)]
        else:
            filtered_df = filtered_df[filtered_df['holistic_ai_score'] >= 0.8]

    # Sorting
    sort_map = {
        "Holistic Score": ("holistic_ai_score", False),
        "Precision": ("precision_ratio", False),
        "MRR": ("mean_reciprocal_rank", False),
        "Solr Count": ("solr_count", False),
        "Google Count": ("google_count", False),
    }
    sort_col, ascending = sort_map[metric_filter][0], sort_map[metric_filter][1]
    filtered_df = filtered_df.sort_values(by=sort_col, ascending=ascending, na_position='last')

    st.write(f"Showing {len(filtered_df)} of {len(df)} total results")

    # Format some columns
    def fmt_score(v):
        if pd.isna(v):
            return "-"
        if v >= 0.8:
            cls = "score-high"
        elif v >= 0.5:
            cls = "score-medium"
        else:
            cls = "score-low"
        return f'<span class="{cls}">{v:.2f}</span>'

    display_df = filtered_df.copy()
    for col in ["holistic_ai_score", "precision_ratio", "mean_reciprocal_rank"]:
        display_df[col] = display_df[col].apply(fmt_score)

    st.write(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
    
    # Expandable reasoning and POI coverage per query
    st.markdown("### 🔍 Detailed Analysis")

    low_score_df = df.sort_values('holistic_ai_score').head(10)

    if not low_score_df.empty:
        st.subheader("Lowest Holistic Score Queries")

        for _, row in low_score_df.iterrows():
            with st.expander(f"🔍 {row['query']} (Holistic: {row['holistic_ai_score']:.2f}, Precision: {row['precision_ratio']:.3f}, MRR: {row['mean_reciprocal_rank']:.3f})"):
                colL, colR = st.columns(2)

                with colL:
                    st.markdown("**Query:**")
                    st.write(row['query'])
                    st.markdown("**Raw Counts:**")
                    st.write({
                        "solr_count": int(row.get("solr_count") or 0),
                        "google_count": int(row.get("google_count") or 0),
                        "num_google_pois": int(row.get("num_google_pois") or 0)
                    })

                with colR:
                    st.markdown("**Holistic Reasoning:**")
                    st.write(row['holistic_ai_reasoning'])

                # POI coverage table for this query
                poi_subset = df_poi[df_poi["query"] == row["query"]].copy()
                if not poi_subset.empty:
                    poi_subset = poi_subset.sort_values("poi_rank").reset_index(drop=True)
                    st.markdown("**Coverage per Google POI:**")
                    st.dataframe(poi_subset, use_container_width=True)
                else:
                    st.info("No POI coverage details for this query.")
    
    # Export functionality
    st.markdown("### 💾 Export Data")

    col1, col2, col3 = st.columns(3)

    with col1:
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download filtered queries as CSV",
            data=csv,
            file_name='filtered_advanced_evaluation_queries.csv',
            mime='text/csv'
        )

    with col2:
        json_data = filtered_df.to_json(orient='records', indent=2)
        st.download_button(
            label="📥 Download filtered queries as JSON",
            data=json_data,
            file_name='filtered_advanced_evaluation_queries.json',
            mime='application/json'
        )

    with col3:
        if not df_poi.empty:
            csv_poi = df_poi.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download POI coverage as CSV",
                data=csv_poi,
                file_name='poi_coverage.csv',
                mime='text/csv'
            )

if __name__ == "__main__":
    main()
