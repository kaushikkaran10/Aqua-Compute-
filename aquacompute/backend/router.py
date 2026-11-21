import re

try:
    import tiktoken
    _TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    _TIKTOKEN_ENCODER = None

# Named constants for thresholds, point values, and keywords
TOKEN_THRESHOLD_MED = 150
TOKEN_POINTS_MED = 2
TOKEN_THRESHOLD_HIGH = 400
TOKEN_POINTS_HIGH = 3

KEYWORD_POINTS_EACH = 2
KEYWORD_MAX_POINTS = 4
HARD_KEYWORDS = (
    "code",
    "debug",
    "prove",
    "proof",
    "analyze",
    "analyse",
    "compare",
    "step by step",
    "legal",
    "math",
    "optimize",
    "algorithm",
    "derive",
)

QUESTION_MARK_THRESHOLD = 1
QUESTION_MARK_POINTS = 1
CODE_MATH_POINTS = 2

TIER_SMALL_MAX_SCORE = 2
TIER_MEDIUM_MAX_SCORE = 5

TIER_SMALL = "small"
TIER_MEDIUM = "medium"
TIER_LARGE = "large"

CODE_MATH_PATTERNS = (
    r"```",
    r"\bdef\s+[a-zA-Z_]\w*\s*\(",
    r"\b(?:import\s+[a-zA-Z_]|from\s+[a-zA-Z_]\w*\s+import\b)",
    r"[\{\}]",
    r"\d+\s*[\+\-\*/%=]\s*\d+",
    r"[∑∫√\^]",
)


def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken (cl100k_base) or estimate as words * 1.3."""
    if _TIKTOKEN_ENCODER is not None:
        return len(_TIKTOKEN_ENCODER.encode(text))
    return int(len(text.split()) * 1.3)


def route(prompt: str) -> dict:
    """Route a prompt to a small, medium, or large tier based on heuristic scoring."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string.")

    tokens = _count_tokens(prompt)
    score = 0
    reasons: list[str] = []

    # Token length scoring (higher one only)
    if tokens > TOKEN_THRESHOLD_HIGH:
        score += TOKEN_POINTS_HIGH
        reasons.append(f">{TOKEN_THRESHOLD_HIGH} tokens")
    elif tokens > TOKEN_THRESHOLD_MED:
        score += TOKEN_POINTS_MED
        reasons.append(f">{TOKEN_THRESHOLD_MED} tokens")

    # Distinct hard keywords (whole-word, case-insensitive, capped)
    matched_keywords: list[str] = []
    for kw in HARD_KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, prompt, re.IGNORECASE):
            matched_keywords.append(kw)

    if matched_keywords:
        kw_points = min(len(matched_keywords) * KEYWORD_POINTS_EACH, KEYWORD_MAX_POINTS)
        score += kw_points
        reasons.append(f"keywords: {', '.join(matched_keywords)}")

    # Multiple question marks
    if prompt.count("?") > QUESTION_MARK_THRESHOLD:
        score += QUESTION_MARK_POINTS
        reasons.append("multiple questions")

    # Code or equations
    has_code_or_math = any(re.search(pat, prompt) for pat in CODE_MATH_PATTERNS)
    if has_code_or_math:
        score += CODE_MATH_POINTS
        reasons.append("code or math syntax")

    # Tier assignment
    if score <= TIER_SMALL_MAX_SCORE:
        tier = TIER_SMALL
    elif score <= TIER_MEDIUM_MAX_SCORE:
        tier = TIER_MEDIUM
    else:
        tier = TIER_LARGE

    reason = ", ".join(reasons) if reasons else "short prompt, no hard keywords"

    return {
        "tier": tier,
        "tokens": tokens,
        "score": score,
        "reason": reason,
    }
