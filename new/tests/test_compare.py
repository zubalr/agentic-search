import pytest
from agent_judge.compare import process_queries_batch, process_queries_sequential

# These are integration tests; for now, just check that the functions exist

def test_batch_and_sequential_exist():
    assert callable(process_queries_batch)
    assert callable(process_queries_sequential)
