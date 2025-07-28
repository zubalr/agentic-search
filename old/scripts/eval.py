"""
Unified CLI entry point for running evaluation runners (DeepEval, Ragas, etc.)
Usage:
    python scripts/eval.py deepeval --results ... --model ...
"""
import sys
import subprocess

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/eval.py <runner> [args...]")
        print("Example: python scripts/eval.py deepeval --results ... --model ...")
        sys.exit(1)
    runner = sys.argv[1]
    args = sys.argv[2:]
    if runner == "deepeval":
        # Forward to agent_judge/eval/deepeval_runner.py
        subprocess.run([sys.executable, "-m", "agent_judge.eval.deepeval_runner"] + args)
    else:
        print(f"Unknown runner: {runner}")
        sys.exit(1)
