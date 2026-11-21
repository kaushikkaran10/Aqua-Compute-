import pytest
from router import route

LONG_LOREM = "lorem ipsum " * 250
LONG_ANALYZE_COMPARE = "Analyze and compare the following detailed systems: " + ("data metric evaluation " * 200)

TEST_PROMPTS = [
    # Small tier (score 0-2)
    ("Hello world!", "small"),
    ("What is the capital of France?", "small"),
    ("Can you write a poem about the ocean?", "small"),
    ("Tell me a funny joke about cats.", "small"),
    ("Why is the sky blue? Is it due to Rayleigh scattering?", "small"),
    ("Can you debug this short sentence?", "small"),
    # Medium tier (score 3-5)
    (LONG_LOREM, "medium"),
    ("Can you compare and optimize this high level architecture?", "medium"),
    ("Please analyze and compare these two product roadmaps.", "medium"),
    ("Show me an algorithm using def solve(nums): to find duplicates.", "medium"),
    ("What is the legal definition of negligence? Can you explain its elements?", "medium"),
    ("Can you derive this formula? Is it valid for all positive integers?", "medium"),
    # Large tier (score 6+)
    (LONG_ANALYZE_COMPARE, "large"),
    ("Prove step by step that x^2 = 2 has no rational solution.", "large"),
    ("Please debug this algorithm: def solve(x): return x^2 if x > 0 else 2+2", "large"),
    ("Analyze, compare, and optimize this implementation: ```import math```", "large"),
]


@pytest.mark.parametrize("prompt,expected_tier", TEST_PROMPTS)
def test_route_tiers(prompt: str, expected_tier: str):
    """Verify that diverse prompts are categorized into their expected tiers."""
    result = route(prompt)
    assert result["tier"] == expected_tier


def test_route_output_format():
    """Verify the exact dictionary structure and tier validity of the router output."""
    result = route("Explain how photosynthesis works.")
    assert isinstance(result, dict)
    assert set(result.keys()) == {"tier", "tokens", "score", "reason"}
    assert result["tier"] in {"small", "medium", "large"}
    assert isinstance(result["tokens"], int)
    assert isinstance(result["score"], int)
    assert isinstance(result["reason"], str)
    assert result["tokens"] > 0
    assert result["score"] >= 0


@pytest.mark.parametrize("invalid_input", ["", "   ", "\n\t  ", None, 123, []])
def test_route_invalid_inputs(invalid_input):
    """Verify that empty, whitespace, None, and non-string inputs raise ValueError."""
    with pytest.raises(ValueError):
        route(invalid_input)
