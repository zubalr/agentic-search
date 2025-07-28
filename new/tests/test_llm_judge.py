import pytest
from agent_judge.llm_judge import LLMManager, Comparison

def test_llm_manager_init():
    # Should raise ValueError if no valid configs
    with pytest.raises(ValueError):
        LLMManager([])

def test_comparison_schema():
    # Test pydantic validation
    valid = Comparison(
        verdict="INTERNAL_SERVER_BETTER",
        reasoning="Test reason",
        internal_server_score=5,
        google_maps_score=3
    )
    assert valid.verdict == "INTERNAL_SERVER_BETTER"
    assert valid.internal_server_score == 5
    assert valid.google_maps_score == 3
