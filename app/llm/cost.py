# Model pricing table per 1 Million tokens (USD)
# Kept in config/module to avoid hardcoding prices in business logic
MODEL_PRICING: dict[str, dict[str, float]] = {
    # Google Gemini Models (Free tier available, standard paid rates)
    "gemini-flash-lite-latest": {"input_per_mtok": 0.0, "output_per_mtok": 0.0},
    "gemini-flash-latest": {"input_per_mtok": 0.0, "output_per_mtok": 0.0},
    "gemini-1.5-flash": {"input_per_mtok": 0.075, "output_per_mtok": 0.30},
    "gemini-2.0-flash": {"input_per_mtok": 0.10, "output_per_mtok": 0.40},
    # Groq / Open Models (Free or ultra-cheap)
    "llama-3.1-8b-instant": {"input_per_mtok": 0.05, "output_per_mtok": 0.08},
    # Test & Mock Models (Zero cost)
    "mock-model": {"input_per_mtok": 0.0, "output_per_mtok": 0.0},
}


def calculate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Computes exact cost in USD from token counts using effective rate table.
    cost = (input_tokens * price_in + output_tokens * price_out) / 1,000,000
    """
    pricing = MODEL_PRICING.get(model, {"input_per_mtok": 0.10, "output_per_mtok": 0.30})
    cost_in = (input_tokens * pricing["input_per_mtok"]) / 1_000_000
    cost_out = (output_tokens * pricing["output_per_mtok"]) / 1_000_000
    return round(cost_in + cost_out, 6)
