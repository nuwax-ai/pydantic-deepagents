# Fallback Models

When the primary model raises a transient API error (rate limit, 5xx, provider outage), `agent.run()` normally re-raises the exception and the run ends. The `fallback_model` parameter wraps the primary in pydantic-ai's [`FallbackModel`][pydantic_ai.models.fallback.FallbackModel] so the run continues on the next model in the chain instead.

## Basic usage

```python
from pydantic_deep import create_deep_agent

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    fallback_model="anthropic:claude-haiku-4-5-20251001",
)
```

Pass a list for an ordered fallback chain:

```python
agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    fallback_model=[
        "anthropic:claude-haiku-4-5-20251001",
        "openai:gpt-4o-mini",
    ],
)
```

!!! tip "Pin model versions in production"
    Examples here use date-suffixed model IDs (`claude-haiku-4-5-20251001`). In production code, pin the version explicitly so a provider's silent re-tag of an unversioned alias does not change the behavior of your fallback chain.

## CLI users

In the TUI, run `/model` to pick a primary model. A second modal then prompts for an optional fallback (or "No fallback"). Both values are persisted to `.pydantic-deep/config.toml` and used automatically on subsequent runs.

## Retry semantics

Fallback fires when the underlying exception is an instance of [`ModelAPIError`][pydantic_ai.exceptions.ModelAPIError] **and** its message does not contain any of these substrings (case-insensitive): `401`, `403`, `unauthorized`, `forbidden`. In practice this covers:

- Rate limits (HTTP 429)
- Server errors (HTTP 5xx)
- Provider outages and timeouts surfaced as `ModelAPIError`

It does **not** fire on:

- Auth/permission errors (401/403) — these are permanent and would fail on every model in the chain. The original exception is re-raised.
- `ModelRetry` — tool-driven retries are handled by pydantic-ai's retry loop before they ever reach the fallback layer.
- `BudgetExceededError` from [Cost Tracking](cost-tracking.md) — not a `ModelAPIError`; propagates unchanged.
- Validation errors and any non-`ModelAPIError` exception.

Message history is preserved across the fallback hop — the fallback model continues the conversation, it does not restart it.

## Observability via hooks

Use the `MODEL_FALLBACK_TRIGGERED` hook event to log or alert when a fallback occurs:

```python
from pydantic_deep import create_deep_agent
from pydantic_deep.capabilities.hooks import Hook, HookEvent, HookInput, HookResult

async def on_fallback(inp: HookInput) -> HookResult:
    primary = inp.tool_input["primary"]
    fallback = inp.tool_input["fallback"]
    print(f"Model fallback: {primary} → {fallback} (error: {inp.tool_error})")
    return HookResult()

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    fallback_model="anthropic:claude-haiku-4-5-20251001",
    hooks=[Hook(event=HookEvent.MODEL_FALLBACK_TRIGGERED, handler=on_fallback)],
)
```

The `HookInput` payload for this event:

| Field | Value |
|-------|-------|
| `tool_input["primary"]` | Name of the primary model |
| `tool_input["fallback"]` | Name of the **first** fallback in the chain (see limitation below) |
| `tool_error` | The stringified error message (`str(exc)`) — not the exception object itself |

## Limitations and caveats

**The `fallback` field in the hook payload is static.**
For a chain `[A, B, C]`, the hook reports `fallback=A` regardless of which hop is currently in flight (A→B, B→C, etc.). It identifies the chain, not the specific hop. If you need per-hop telemetry, inspect `tool_error` and your provider's own observability instead.

**Costs accumulate across the chain.**
Each model in the chain bills separately. The [`CostTracking`](cost-tracking.md) capability sums tokens and USD per-run across all models, and `cost_budget_usd` is enforced against the cumulative total — fallbacks do not get a separate budget.

**Auth error detection is substring-based.**
The filter looks for `401`, `403`, `unauthorized`, `forbidden` (case-insensitive) in the exception message. A provider that surfaces auth failures with a different phrasing would currently fall through to the next model. If you observe this, open an issue with the exception message.

**Fallback does not change the agent's model name.**
`agent.model` reports the `FallbackModel` wrapper. To know which underlying model handled a particular response, consult provider-level telemetry or the `MODEL_FALLBACK_TRIGGERED` hook.
