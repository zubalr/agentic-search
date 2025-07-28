# Agentic Search LLM Judge System

## Structure

- `agent_judge/`: Core logic (LLM judge, data IO, config, orchestration)
- `scripts/`: Entry points
- `tests/`: Unit tests

## Usage

Run the system in batch or sequential mode:

```bash
python scripts/main.py --mode batch
python scripts/main.py --mode sequential
```

## Configuration

You can override file paths and model configs via environment variables or by editing `agent_judge/config.py`.

## Setup (venv + uv)

1. Create a virtual environment and activate it:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install [uv](https://github.com/astral-sh/uv) if you don't have it:
   ```bash
   pip install uv
   ```
3. Install all dependencies (from `config/requirements.txt`) with uv:
   ```bash
   uv pip install -r config/requirements.txt
   ```

**To add new dependencies:**

```bash
uv add <package-name>
```

This will update your lockfile and ensure reproducibility.

# Agentic Search LLM Judge System

## API Keys

Copy `.env.example` to `.env` and fill in your API keys for any providers you want to use (Cerebras, Groq, OpenAI, etc.).

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
