"""
LLM Judge logic: LLMManager, prompt, judge function.

This module manages LLM client initialization, prompt construction, and the core judge_query async function.
"""
import traceback

import os
import logging
import json
from typing import List, Dict, Literal
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_cerebras import ChatCerebras
from langchain_groq import ChatGroq

# --- LLM & API Key Configuration ---
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- Pydantic Data Structure ---
class Comparison(BaseModel):
    """Data model for the comparison between two search results."""
    verdict: Literal["INTERNAL_SERVER_BETTER", "GOOGLE_MAPS_BETTER", "BOTH_ARE_GOOD", "BOTH_ARE_BAD", "INCONCLUSIVE"] = Field(description="The verdict.")
    reasoning: str = Field(description="A detailed, step-by-step explanation for the verdict.")
    internal_server_score: int = Field(description="A score from 1-5 for the internal server's result.", ge=1, le=5)
    google_maps_score: int = Field(description="A score from 1-5 for the Google Maps' result.", ge=1, le=5)


class LLMManager:
    """
    Initialize and manage LLM clients for round-robin usage.
    Handles both Groq and Cerebras providers.
    """
    def __init__(self, model_configs: List[Dict]):
        self.clients = self._initialize_clients(model_configs)
        self.current_index = 0
        if not self.clients:
            raise ValueError("No LLM clients could be initialized. Check API keys and model configs.")

    def _initialize_clients(self, model_configs: List[Dict]) -> List:
        clients = []
        for config in model_configs:
            provider, model_name = config.get("provider"), config.get("model_name")
            try:
                if provider == "groq" and GROQ_API_KEY:
                    clients.append(ChatGroq(temperature=0, model_name=model_name, groq_api_key=GROQ_API_KEY))
                elif provider == "cerebras" and CEREBRAS_API_KEY:
                    clients.append(ChatCerebras(model=model_name, temperature=0, cerebras_api_key=CEREBRAS_API_KEY))
                else:
                    logging.warning(f"Skipping model '{model_name}' due to missing API key or unknown provider.")
            except Exception as e:
                logging.error(f"Failed to initialize LLM client for {provider}:{model_name}: {e}")
        return clients

    def get_next_client(self):
        """Return the next LLM client in round-robin fashion."""
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

async def judge_query(query: str, internal_res: Dict, google_res: Dict, llm_manager: LLMManager):
    """
    Process a single query and return the LLM's comparison result.
    Returns None if an error occurs or results are missing.
    """
    if not internal_res or not google_res:
        logging.warning(f"One of the results for query '{query}' is empty. Skipping.")
        return None
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
        return comparison_result
    except Exception as e:
        logging.error(f"An error occurred while processing query '{query}': {e}\n{traceback.format_exc()}")
        return None
