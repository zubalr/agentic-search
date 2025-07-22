import json
import os
import logging
import asyncio
import time
from typing import Literal, List, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_cerebras import ChatCerebras
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
load_dotenv()

# --- File Paths ---
INTERNAL_RESULTS_FILE = "api_results_0_499.jsonl"
GOOGLE_RESULTS_FILE = "google_places_results_0_499.jsonl"
COMPARISON_MEMORY_FILE = "comparison_memory.jsonl"
FAILED_QUERIES_FILE = "failed_queries.txt"

# --- LLM & Concurrency Configuration ---
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ==============================================================================
#  --- CHOOSE YOUR MODE HERE ---
#  Comment out the mode you are NOT using.
# ==============================================================================

# --- SINGLE MODEL MODE (Cerebras @ 30 RPM) ---
# To respect 30 RPM (1 request every 2s), we process 5 requests then wait 10s.
BATCH_SIZE = 5
DELAY_BETWEEN_BATCHES_S = 10
LLM_MODELS = [
    {"provider": "cerebras", "model_name": "llama-3.3-70b"},
]

# --- MULTI-MODEL MODE (Groq + Cerebras) ---
# BATCH_SIZE = 5
# DELAY_BETWEEN_BATCHES_S = 7 # Groq is faster, so a smaller delay is fine.
# LLM_MODELS = [
#     {"provider": "groq", "model_name": "llama3-70b-8192"},
#     {"provider": "groq", "model_name": "llama3-8b-8192"},
#     {"provider": "cerebras", "model_name": "Cerebras-GPT-13B"},
# ]
# ==============================================================================

# --- Pydantic Data Structure ---
class Comparison(BaseModel):
    """Data model for the comparison between two search results."""
    verdict: Literal["INTERNAL_SERVER_BETTER", "GOOGLE_MAPS_BETTER", "BOTH_ARE_GOOD", "BOTH_ARE_BAD", "INCONCLUSIVE"] = Field(description="The verdict.")
    reasoning: str = Field(description="A detailed, step-by-step explanation for the verdict.")
    internal_server_score: int = Field(description="A score from 1-5 for the internal server's result.", ge=1, le=5)
    google_maps_score: int = Field(description="A score from 1-5 for the Google Maps' result.", ge=1, le=5)


# --- Helper Functions & Classes ---

def load_results(file_path: str) -> Dict[str, Dict]:
    """Loads a JSONL result file into a dictionary mapping query to result."""
    results = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if query := data.get("query"):
                        results[query] = data.get("result", {})
                except (json.JSONDecodeError, KeyError) as e:
                    logging.warning(f"Skipping malformed line in {file_path}: {line.strip()} - Error: {e}")
    except FileNotFoundError:
        logging.error(f"Input file not found: {file_path}")
    return results

def load_memory(file_path: str) -> Dict[str, Dict]:
    """Loads existing comparisons from the memory file to avoid re-processing."""
    memory = {}
    if not os.path.exists(file_path):
        return memory
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                if query := data.get("query"):
                    memory[query] = data.get("comparison")
            except (json.JSONDecodeError, KeyError):
                continue
    return memory

def save_comparison(file_path: str, query: str, comparison: Dict):
    """Saves a new comparison to the memory file."""
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            record = {"query": query, "comparison": comparison}
            f.write(json.dumps(record) + "\n")
    except IOError as e:
        logging.error(f"Could not write to memory file {file_path}: {e}")

class LLMManager:
    """A class to initialize and manage LLM clients for round-robin usage."""
    def __init__(self, model_configs: List[Dict]):
        self.clients = self._initialize_clients(model_configs)
        self.current_index = 0
        if not self.clients:
            raise ValueError("No LLM clients could be initialized. Check API keys and model configs.")

    def _initialize_clients(self, model_configs: List[Dict]) -> List:
        clients = []
        for config in model_configs:
            provider, model_name = config.get("provider"), config.get("model_name")
            if provider == "groq" and GROQ_API_KEY:
                clients.append(ChatGroq(temperature=0, model_name=model_name, groq_api_key=GROQ_API_KEY))
            elif provider == "cerebras" and CEREBRAS_API_KEY:
                clients.append(ChatCerebras(model=model_name, temperature=0, cerebras_api_key=CEREBRAS_API_KEY))
            else:
                logging.warning(f"Skipping model '{model_name}' due to missing API key or unknown provider.")
        return clients

    def get_next_client(self):
        client = self.clients[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.clients)
        return client

PROMPT_TEMPLATE = ChatPromptTemplate.from_template(
    """
    You are an expert Search Quality Rater. Your task is to analyze and compare two sets of search results for a given user query. Your evaluation must be objective, detailed, and based SOLELY on the data provided.
    **EVALUATION CRITERIA:**
    1.  **Relevance:** How well do the results match the user's query intent? For "Qatar nat", results like "Qatar National Library" or "National Museum of Qatar" are highly relevant.
    2.  **Completeness & Quality:** How rich is the data? Does it include useful information like ratings, user counts, full addresses, and contact numbers? Missing data lowers quality.
    3.  **Diversity:** Does the result set offer a good variety of relevant places, or is it repetitive?
    **TASK:**
    Based on the criteria, compare the 'Internal Server Result' and the 'Google Maps Result'. Provide a verdict, reasoning, and a 1-5 score for each. Your entire response MUST be a single JSON object that conforms to the provided schema. Do not include any text outside the JSON object.
    **JSON SCHEMA:**
    {schema}
    **QUERY:**
    "{query}"
    **INTERNAL SERVER RESULT (JSON):**
    {internal_results}
    **GOOGLE MAPS RESULT (JSON):**
    {google_results}
    """
)
PARSER = JsonOutputParser(pydantic_object=Comparison)

async def process_query(query: str, internal_res: Dict, google_res: Dict, llm_manager: LLMManager):
    """Processes a single query asynchronously."""
    if not internal_res or not google_res:
        logging.warning(f"One of the results for query '{query}' is empty. Skipping.")
        return
    llm_client = llm_manager.get_next_client()
    model_identifier = getattr(llm_client, "model_name", getattr(llm_client, "model", "Unknown"))
    logging.info(f"Processing '{query}' using model '{model_identifier}'")
    try:
        chain = PROMPT_TEMPLATE | llm_client | PARSER
        comparison_result = await chain.ainvoke({
            "query": query,
            "internal_results": json.dumps(internal_res, indent=2),
            "google_results": json.dumps(google_res, indent=2),
            "schema": Comparison.schema_json(indent=2),
        })
        logging.info(f"Verdict for '{query}': {comparison_result.get('verdict', 'N/A')}")
        save_comparison(COMPARISON_MEMORY_FILE, query, comparison_result)
    except Exception as e:
        logging.error(f"An error occurred while processing query '{query}': {e}")
        with open(FAILED_QUERIES_FILE, "a", encoding="utf-8") as f:
            f.write(f"{query}\n")

async def main():
    """Main function to orchestrate the asynchronous comparison process."""
    logging.info("Starting search result comparison process...")
    start_time = time.time()
    internal_results = load_results(INTERNAL_RESULTS_FILE)
    google_results = load_results(GOOGLE_RESULTS_FILE)
    comparison_memory = load_memory(COMPARISON_MEMORY_FILE)
    if not internal_results or not google_results:
        return
    try:
        llm_manager = LLMManager(LLM_MODELS)
        logging.info(f"Initialized {len(llm_manager.clients)} LLM clients.")
    except ValueError as e:
        logging.error(f"{e} Exiting.")
        return
    queries_to_process = [q for q in internal_results if q not in comparison_memory]
    logging.info(f"Found {len(internal_results)} total queries. Processing {len(queries_to_process)} new queries.")
    for i in range(0, len(queries_to_process), BATCH_SIZE):
        batch = queries_to_process[i:i + BATCH_SIZE]
        tasks = []
        for query in batch:
            if query in google_results:
                tasks.append(process_query(query, internal_results[query], google_results[query], llm_manager))
            else:
                logging.warning(f"Query '{query}' not in Google results. Skipping.")
        await asyncio.gather(*tasks)
        if (i + BATCH_SIZE) < len(queries_to_process):
            logging.info(f"--- Batch {i//BATCH_SIZE + 1} finished. Waiting for {DELAY_BETWEEN_BATCHES_S} seconds... ---")
            await asyncio.sleep(DELAY_BETWEEN_BATCHES_S)
    end_time = time.time()
    logging.info(f"Comparison process finished in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    asyncio.run(main())