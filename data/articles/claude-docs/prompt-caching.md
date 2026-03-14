# Prompt Caching - Claude API Docs

Prompt caching optimizes your API usage by allowing resuming from specific prefixes in your prompts. This significantly reduces processing time and costs for repetitive tasks or prompts with consistent elements.

Prompt caching stores KV cache representations and cryptographic hashes of cached content, but does not store the raw text of prompts or responses. This may be suitable for customers who require ZDR-type data retention commitments.

There are two ways to enable prompt caching:

- **Automatic caching**: Add a single `cache_control` field at the top level of your request. The system automatically applies the cache breakpoint to the last cacheable block and moves it forward as conversations grow. Best for multi-turn conversations where the growing message history should be cached automatically.
- **Explicit cache breakpoints**: Place `cache_control` directly on individual content blocks for fine-grained control over exactly what gets cached.

## How prompt caching works

When you send a request with prompt caching enabled:

1. The system checks if a prompt prefix, up to a specified cache breakpoint, is already cached from a recent query.
2. If found, it uses the cached version, reducing processing time and costs.
3. Otherwise, it processes the full prompt and caches the prefix once the response begins.

This is especially useful for:
- Prompts with many examples
- Large amounts of context or background information
- Repetitive tasks with consistent instructions
- Long multi-turn conversations

By default, the cache has a 5-minute lifetime. The cache is refreshed for no additional cost each time the cached content is used.

Anthropic also offers a 1-hour cache duration at additional cost.

Prompt caching references the entire prompt - `tools`, `system`, and `messages` (in that order) up to and including the block designated with `cache_control`.

## Pricing

Prompt caching introduces a new pricing structure. The table below shows the price per million tokens for each supported model:

| Model | Base Input Tokens | 5m Cache Writes | 1h Cache Writes | Cache Hits & Refreshes | Output Tokens |
|---|---|---|---|---|---|
| Claude Opus 4.6 | $5 / MTok | $6.25 / MTok | $10 / MTok | $0.50 / MTok | $25 / MTok |
| Claude Opus 4.5 | $5 / MTok | $6.25 / MTok | $10 / MTok | $0.50 / MTok | $25 / MTok |
| Claude Opus 4.1 | $15 / MTok | $18.75 / MTok | $30 / MTok | $1.50 / MTok | $75 / MTok |
| Claude Opus 4 | $15 / MTok | $18.75 / MTok | $30 / MTok | $1.50 / MTok | $75 / MTok |
| Claude Sonnet 4.6 | $3 / MTok | $3.75 / MTok | $6 / MTok | $0.30 / MTok | $15 / MTok |
| Claude Sonnet 4.5 | $3 / MTok | $3.75 / MTok | $6 / MTok | $0.30 / MTok | $15 / MTok |
| Claude Sonnet 4 | $3 / MTok | $3.75 / MTok | $6 / MTok | $0.30 / MTok | $15 / MTok |
| Claude Haiku 4.5 | $1 / MTok | $1.25 / MTok | $2 / MTok | $0.10 / MTok | $5 / MTok |

Pricing multipliers:
- 5-minute cache write tokens are 1.25 times the base input tokens price
- 1-hour cache write tokens are 2 times the base input tokens price
- Cache read tokens are 0.1 times the base input tokens price

## Supported models

Prompt caching (both automatic and explicit) is currently supported on:
- Claude Opus 4.6, Claude Opus 4.5, Claude Opus 4.1, Claude Opus 4
- Claude Sonnet 4.6, Claude Sonnet 4.5, Claude Sonnet 4
- Claude Haiku 4.5, Claude Haiku 3.5 (deprecated), Claude Haiku 3

## Automatic caching

Automatic caching is the simplest way to enable prompt caching. Instead of placing `cache_control` on individual content blocks, add a single `cache_control` field at the top level of your request body. The system automatically applies the cache breakpoint to the last cacheable block.

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    cache_control={"type": "ephemeral"},
    system="You are a helpful assistant that remembers our conversation.",
    messages=[
        {"role": "user", "content": "My name is Alex. I work on machine learning."},
        {"role": "assistant", "content": "Nice to meet you, Alex! How can I help with your ML work today?"},
        {"role": "user", "content": "What did I say I work on?"},
    ],
)
```

### How automatic caching works in multi-turn conversations

With automatic caching, the cache point moves forward automatically as conversations grow. Each new request caches everything up to the last cacheable block, and previous content is read from cache.

| Request | Cache behavior |
|---------|----------------|
| Request 1 | Everything written to cache |
| Request 2 | Previous turns read from cache; new turns written |
| Request 3 | Previous turns read from cache; new turns written |

### TTL support

By default, automatic caching uses a 5-minute TTL. You can specify a 1-hour TTL at 2x the base input token price:

```json
{ "cache_control": { "type": "ephemeral", "ttl": "1h" } }
```

## Explicit cache breakpoints

For more control over caching, you can place `cache_control` directly on individual content blocks. This is useful when you need to cache different sections that change at different frequencies, or need fine-grained control over exactly what gets cached.

### Structuring your prompt

Place static content (tool definitions, system instructions, context, examples) at the beginning of your prompt. Mark the end of the reusable content for caching using the `cache_control` parameter.

Cache prefixes are created in the following order: `tools`, `system`, then `messages`.

#### How automatic prefix checking works

Three core principles:

1. **Cache keys are cumulative**: When you cache a block with `cache_control`, the cache hash key is generated by hashing all previous blocks sequentially.
2. **Backward sequential checking**: The system checks for cache hits by working backwards from your explicit breakpoint.
3. **20-block lookback window**: The system only checks up to 20 blocks before each explicit `cache_control` breakpoint.

You can define up to 4 cache breakpoints.

### Understanding cache breakpoint costs

Cache breakpoints themselves don't add any cost. You are only charged for:
- **Cache writes**: When new content is written to the cache (25% more than base input tokens for 5-minute TTL)
- **Cache reads**: When cached content is used (10% of base input token price)
- **Regular input tokens**: For any uncached content

## Cache limitations

The minimum cacheable prompt length is:
- 4096 tokens for Claude Opus 4.6, Claude Opus 4.5
- 2048 tokens for Claude Sonnet 4.6
- 1024 tokens for Claude Sonnet 4.5, Claude Opus 4.1, Claude Opus 4, Claude Sonnet 4
- 4096 tokens for Claude Haiku 4.5
- 2048 tokens for Claude Haiku 3.5 and Claude Haiku 3

Shorter prompts cannot be cached, even if marked with `cache_control`.

For concurrent requests, note that a cache entry only becomes available after the first response begins.

Currently, "ephemeral" is the only supported cache type, which by default has a 5-minute lifetime.

### What can be cached

- Tools: Tool definitions in the `tools` array
- System messages: Content blocks in the `system` array
- Text messages: Content blocks in the `messages.content` array
- Images & Documents: Content blocks in user turns
- Tool use and tool results: Content blocks in both user and assistant turns

### What cannot be cached

- Thinking blocks cannot be cached directly with `cache_control` (but CAN be cached alongside other content in previous assistant turns)
- Sub-content blocks (like citations) themselves cannot be cached directly
- Empty text blocks cannot be cached

### What invalidates the cache

The cache follows the hierarchy: `tools` -> `system` -> `messages`. Changes at each level invalidate that level and all subsequent levels.

- Modifying tool definitions invalidates the entire cache
- Enabling/disabling web search modifies the system prompt and invalidates system + message caches
- Changes to `tool_choice` affect message blocks
- Adding/removing images affects message blocks
- Changes to extended thinking settings affect message blocks

## Tracking cache performance

Monitor cache performance using these API response fields:
- `cache_creation_input_tokens`: Tokens written to cache
- `cache_read_input_tokens`: Tokens retrieved from cache
- `input_tokens`: Tokens after the last cache breakpoint (not cached)

Total input tokens = cache_read + cache_creation + input_tokens

## 1-hour cache duration

To use the extended cache, include `ttl` in the `cache_control` definition:

```json
{
  "cache_control": {
    "type": "ephemeral",
    "ttl": "1h"
  }
}
```

The 1-hour cache is best used when:
- Prompts are used less frequently than every 5 minutes but more frequently than every hour
- Latency is important and follow-up prompts may be sent beyond 5 minutes
- You want to improve rate limit utilization (cache hits are not deducted against rate limits)

### Mixing different TTLs

You can use both 1-hour and 5-minute cache controls in the same request. Cache entries with longer TTL must appear before shorter TTLs.

## Best practices

- Start with automatic caching for multi-turn conversations
- Use explicit breakpoints when different sections change at different frequencies
- Cache stable, reusable content (system instructions, background info, tool definitions)
- Place cached content at the prompt's beginning
- Set cache breakpoints at the end of conversations and before editable content
- Regularly analyze cache hit rates

## Use cases

- Conversational agents: Reduce cost and latency for extended conversations
- Coding assistants: Improve autocomplete and codebase Q&A
- Large document processing: Incorporate long-form material without increasing latency
- Detailed instruction sets: Share extensive instructions, procedures, and examples
- Agentic tool use: Enhance performance for multiple tool calls and iterative code changes
- Talk to books, papers, documentation: Embed entire documents and let users ask questions

## Cache storage and sharing

- **Organization Isolation**: Caches are isolated between organizations
- **Exact Matching**: Cache hits require 100% identical prompt segments
- **Output Token Generation**: Prompt caching has no effect on output token generation
- Starting February 5, 2026, prompt caching will use workspace-level isolation instead of organization-level isolation
