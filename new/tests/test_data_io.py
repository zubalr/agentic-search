from agent_judge.data_io import load_results, load_memory, save_comparison
import tempfile
import os

def test_load_and_save_comparison():
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        save_comparison(tf.name, "q1", {"verdict": "BOTH_ARE_GOOD"})
        mem = load_memory(tf.name)
        assert "q1" in mem
    os.remove(tf.name)
