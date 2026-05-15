# Hybrid LLM Architecture Design

## Goal

Replace the current two-tier LLM setup (free Gemini Flash Lite / premium GPT-4o) with a three-tier architecture that uses open-source models via Together AI (primary) and Groq (fallback) for non-premium tasks. This reduces cost, removes dependency on Google's free-tier rate limits, improves global availability, and creates the abstraction needed to move lightweight tasks on-device when a native mobile app is built.

## Motivation

- **Cost**: Gemini Flash Lite's free tier has hard limits (15 RPM, 1M tokens/day) that will bottleneck as users grow. Together AI's Llama 3.1 8B Turbo costs ~$0.10/M tokens — effectively free at current scale, and predictable at larger scale.
- **Jurisdiction**: Groq has limited availability in some regions. Together AI has broader global coverage, making it safer as the primary provider for an educational app with international users.
- **Mobile prep**: A three-tier model with a clean `tier` abstraction lets the `lite` tier swap to on-device inference (e.g., Llama 3.2 3B via ONNX Runtime) without changing any caller code.

## Current State

### Existing Architecture

Two tiers routed by `get_llm_client(premium: bool)`:

| Tier | Model | Provider | Call Sites |
|------|-------|----------|------------|
| Free (`premium=False`) | `gemini-2.5-flash-lite` | Google (OpenAI-compat endpoint) | Chart Coach chat, chart guide, portfolio news, stock news, time machine fun facts |
| Premium (`premium=True`) | `gpt-4o` or Anthropic | OpenAI / Anthropic | Tutor chat, quiz generation |

### Existing LLM Client Protocol

```python
class LLMClient(Protocol):
    async def complete(self, messages, temperature, max_tokens) -> str: ...
    async def stream(self, messages, temperature, max_tokens) -> AsyncIterator[str]: ...
```

All 7 call sites use `complete()`. The `stream()` method is used only by the tutor service.

## Design

### Three Model Tiers

| Tier | Model | Primary Provider | Fallback | Call Sites | Rationale |
|------|-------|-----------------|----------|------------|-----------|
| **lite** | Llama 3.1 8B Turbo | Together AI | Groq | Time machine fun facts, portfolio news summary, stock news summary | Short single-turn outputs, simple prompts, highest volume. Smallest capable model. |
| **standard** | Llama 3.1 8B Turbo | Together AI | Groq | Chart Coach chat, chart guide | Multi-turn conversational, needs decent reasoning, has safety filtering. Same model as lite for now — the tier separation exists so standard can independently upgrade to a larger model (e.g., Llama 70B) without affecting lite. |
| **premium** | GPT-4o / Anthropic | OpenAI / Anthropic | — | Tutor chat, quiz generation | No change. Evaluate open-source replacement later by running parallel inference and comparing quality. |

### Provider Fallback Chain

For `lite` and `standard` tiers, the client attempts providers in order:

1. **Together AI** (primary) — broad availability, cheap, reliable
2. **Groq** (fallback) — very fast inference, optional speed boost

Fallback triggers on:
- HTTP 429 (rate limited)
- HTTP 5xx (server error)
- Connection timeout (10s)

The fallback is a single retry with provider switch, not exponential backoff. If both providers fail, raise `LLMError` (existing error handling in all call sites already catches this).

Premium tier has no fallback chain — it uses the existing direct client.

### Configuration

New fields in `config.py` (`Settings` class):

```python
# Tier routing
llm_lite_providers: str = "together,groq"      # comma-separated, ordered
llm_standard_providers: str = "together,groq"

# Together AI
llm_together_api_key: str = ""
llm_together_base_url: str = "https://api.together.xyz/v1"
llm_together_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"

# Groq
llm_groq_api_key: str = ""
llm_groq_base_url: str = "https://api.groq.com/openai/v1"
llm_groq_model: str = "llama-3.1-8b-instant"
```

Existing premium config fields are unchanged:

```python
llm_premium_provider: str = "openai"
llm_premium_api_key: str = ""
llm_premium_model: str = "gpt-4o"
```

The old `llm_free_*` fields are removed (replaced by together/groq fields).

Any code that references `settings.llm_free_model` for cache keys or logging (e.g., `tutor_service.py` line 109) should switch to a helper like `get_model_name(tier)` that returns the model string for the given tier. This keeps cache keys stable when providers change.

### API Change: `get_llm_client()`

Current signature:
```python
def get_llm_client(premium: bool = False) -> LLMClient
```

New signature:
```python
def get_llm_client(tier: str = "lite") -> LLMClient
```

Where `tier` is `"lite"` | `"standard"` | `"premium"`.

- `"lite"` and `"standard"` return a `FallbackLLMClient` that wraps the provider chain
- `"premium"` returns the existing direct client (OpenAI or Anthropic)

### FallbackLLMClient

New class implementing `LLMClient` protocol:

```python
class FallbackLLMClient:
    def __init__(self, clients: list[LLMClient]):
        self.clients = clients

    async def complete(self, messages, temperature, max_tokens) -> str:
        last_error = None
        for client in self.clients:
            try:
                return await client.complete(messages, temperature, max_tokens)
            except LLMError as e:
                if e.retryable:
                    last_error = e
                    continue
                raise
        raise last_error

    async def stream(self, messages, temperature, max_tokens):
        # Same fallback logic, yields from first successful provider
```

`LLMError` gains a `retryable: bool` field. Rate limits (429) and server errors (5xx) are retryable. Auth errors (401/403) and bad requests (400) are not.

### Call Site Migration

| File | Function | Current | New |
|------|----------|---------|-----|
| `simulator.py` | `_time_machine` (fun fact) | `get_llm_client(premium=False)` | `get_llm_client(tier="lite")` |
| `simulator.py` | `_portfolio_news_summary` | `get_llm_client(premium=False)` | `get_llm_client(tier="lite")` |
| `simulator.py` | `_stock_news_summary` | `get_llm_client(premium=False)` | `get_llm_client(tier="lite")` |
| `simulator.py` | `_chart_guide` | `get_llm_client(premium=False)` | `get_llm_client(tier="standard")` |
| `chart_coach_service.py` | `chart_coach_chat` | `get_llm_client(premium=False)` | `get_llm_client(tier="standard")` |
| `tutor_service.py` | `tutor_chat` | `get_llm_client(premium=user.is_premium)` | `get_llm_client(tier="premium" if premium else "standard")` |
| `ai_content_service.py` | `generate_practice_quiz` | `get_llm_client(premium=user.is_premium)` | `get_llm_client(tier="premium" if premium else "standard")` |

Note: The tutor and quiz services branch on `user.is_premium` to select both the model and message limits. This stays the same — free users get `tier="standard"` (Llama 8B via Together/Groq) with 6 messages, premium users get `tier="premium"` (GPT-4o) with 12 messages. The `premium` bool parameter on the service functions is kept for limit branching; only the `get_llm_client()` call changes.

### Backward Compatibility

- `get_llm_client(premium=True)` continues to work as an alias for `tier="premium"` during migration. Deprecated with a warning log.
- `get_llm_client(premium=False)` maps to `tier="lite"`. Same deprecation.
- Remove the `premium` parameter after all call sites are migrated (same PR).

### Environment Variables

`.env.example` updated with:

```
# LLM — Lite/Standard tiers (open-source models)
LLM_TOGETHER_API_KEY=
LLM_GROQ_API_KEY=

# LLM — Premium tier (unchanged)
LLM_PREMIUM_API_KEY=
```

The old `LLM_FREE_API_KEY` is removed.

### No Prompt Changes

All existing prompts work unchanged with Llama 3.1 8B. The model accepts the same OpenAI chat format (system/user/assistant messages). Temperature and max_tokens values remain the same.

If quality testing reveals issues with specific prompts on Llama 8B (e.g., the chart coach safety filter or quiz JSON schema compliance), those prompts can be tuned independently — but this is not expected for the simple educational content these tasks generate.

## Testing

- Unit tests for `FallbackLLMClient`: mock two providers, verify fallback on retryable errors, verify no fallback on non-retryable errors
- Unit test for `get_llm_client(tier=...)`: verify correct client returned for each tier
- Integration test: existing `test_simulator.py` tests continue to pass (they mock the LLM layer)
- Manual test: hit each endpoint with real Together AI key, verify responses are coherent

## Future: On-Device Migration Path

When a native mobile app is built:

1. `lite` tier gets a new `OnDeviceLLMClient` implementation that runs Llama 3.2 3B (or similar) via ONNX Runtime / CoreML / MediaPipe
2. The mobile app's `get_llm_client(tier="lite")` returns `OnDeviceLLMClient` instead of `FallbackLLMClient`
3. `standard` and `premium` tiers stay cloud-based
4. No changes to prompts, call sites, or business logic

This design also supports a progressive rollout: the mobile app could use on-device for lite tasks when offline, and fall back to the cloud when online, by wrapping both in a priority chain.
