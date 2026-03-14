# Web fetch tool

The web fetch tool allows Claude to retrieve full content from specified web pages and PDF documents.

The latest web fetch tool version (`web_fetch_20260209`) supports dynamic filtering with Claude Opus 4.6 and Sonnet 4.6. Claude can write and execute code to filter fetched content before it reaches the context window, keeping only relevant information and discarding the rest. This reduces token consumption while maintaining response quality. The previous tool version (`web_fetch_20250910`) remains available without dynamic filtering.

## Supported models

Web fetch is available on:

- Claude Opus 4.6 (`claude-opus-4-6`)
- Claude Opus 4.5 (`claude-opus-4-5-20251101`)
- Claude Opus 4.1 (`claude-opus-4-1-20250805`)
- Claude Opus 4 (`claude-opus-4-20250514`)
- Claude Sonnet 4.6 (`claude-sonnet-4-6`)
- Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- Claude Sonnet 4 (`claude-sonnet-4-20250514`)
- Claude Sonnet 3.7 (deprecated) (`claude-3-7-sonnet-20250219`)
- Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)
- Claude Haiku 3.5 (deprecated) (`claude-3-5-haiku-latest`)

## How web fetch works

When you add the web fetch tool to your API request:

1. Claude decides when to fetch content based on the prompt and available URLs.
2. The API retrieves the full text content from the specified URL.
3. For PDFs, automatic text extraction is performed.
4. Claude analyzes the fetched content and provides a response with optional citations.

The web fetch tool currently does not support websites dynamically rendered via JavaScript.

### Dynamic filtering with Opus 4.6 and Sonnet 4.6

Fetching full web pages and PDFs can quickly consume tokens, especially when only specific information is needed from large documents. With the `web_fetch_20260209` tool version, Claude can write and execute code to filter the fetched content before loading it into context.

This dynamic filtering is particularly useful for:
- Extracting specific sections from long documents
- Processing structured data from web pages
- Filtering relevant information from PDFs
- Reducing token costs when working with large documents

Dynamic filtering requires the code execution tool to be enabled. The web fetch tool (with and without dynamic filtering) is available on the Claude API and Microsoft Azure.

To enable dynamic filtering, use the `web_fetch_20260209` tool version.

## How to use web fetch

Provide the web fetch tool in your API request. Example in Python:

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": "Please analyze the content at https://example.com/article",
        }
    ],
    tools=[{"type": "web_fetch_20250910", "name": "web_fetch", "max_uses": 5}],
)
print(response)
```

### Tool definition

The web fetch tool supports the following parameters:

- `type`: `"web_fetch_20250910"` or `"web_fetch_20260209"` (with dynamic filtering)
- `name`: `"web_fetch"`
- `max_uses`: Optional, limit the number of fetches per request
- `allowed_domains`: Optional, only fetch from these domains
- `blocked_domains`: Optional, never fetch from these domains
- `citations`: Optional, `{"enabled": true}` to enable citations
- `max_content_tokens`: Optional, maximum content length in tokens

#### Domain filtering

When using domain filters:
- Domains should not include the HTTP/HTTPS scheme (use `example.com` instead of `https://example.com`)
- Subdomains are automatically included (`example.com` covers `docs.example.com`)
- Subpaths are supported (`example.com/blog`)
- You can use either `allowed_domains` or `blocked_domains`, but not both in the same request.

#### Content limits

The `max_content_tokens` parameter limits the amount of content included in the context. If the fetched content exceeds this limit, the tool truncates it. This helps control token usage when fetching large documents.

#### Citations

Unlike web search where citations are always enabled, citations are optional for web fetch. Set `"citations": {"enabled": true}` to enable Claude to cite specific passages from fetched documents.

### Response structure

Fetch results include:
- `url`: The URL that was fetched
- `content`: A document block containing the fetched content
- `retrieved_at`: Timestamp when the content was retrieved

For PDF documents, content is returned as base64-encoded data.

### Error codes

- `invalid_input`: Invalid URL format
- `url_too_long`: URL exceeds maximum length (250 characters)
- `url_not_allowed`: URL blocked by domain filtering rules and model restrictions
- `url_not_accessible`: Failed to fetch content (HTTP error)
- `too_many_requests`: Rate limit exceeded
- `unsupported_content_type`: Content type not supported (only text and PDF)
- `max_uses_exceeded`: Maximum web fetch tool uses exceeded
- `unavailable`: An internal error occurred

## URL validation

For security reasons, the web fetch tool can only fetch URLs that have previously appeared in the conversation context. This includes:
- URLs in user messages
- URLs in client-side tool results
- URLs from previous web search or web fetch results

The tool cannot fetch arbitrary URLs that Claude generates or URLs from container-based server tools (Code Execution, Bash, etc.).

## Combined search and fetch

Web fetch works seamlessly with web search for comprehensive information gathering:

```python
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=4096,
    messages=[
        {
            "role": "user",
            "content": "Find recent articles about quantum computing and analyze the most relevant one in detail",
        }
    ],
    tools=[
        {"type": "web_search_20250305", "name": "web_search", "max_uses": 3},
        {
            "type": "web_fetch_20250910",
            "name": "web_fetch",
            "max_uses": 5,
            "citations": {"enabled": True},
        },
    ],
)
```

In this workflow, Claude will:
1. Use web search to find relevant articles
2. Select the most promising results
3. Use web fetch to retrieve full content
4. Provide detailed analysis with citations

## Prompt caching

Web fetch works with prompt caching. To enable prompt caching, add `cache_control` breakpoints in your request. Cached fetch results can be reused across conversation turns.

## Streaming

With streaming enabled, fetch events are part of the stream with a pause during content retrieval.

## Batch requests

You can include the web fetch tool in the Messages Batches API. Web fetch tool calls through the Messages Batches API are priced the same as those in regular Messages API requests.

## Usage and pricing

Web fetch usage has no additional charges beyond standard token costs. The web fetch tool is available on the Claude API at no additional cost. You only pay standard token costs for the fetched content that becomes part of your conversation context.

To protect against inadvertently fetching large content that would consume excessive tokens, use the `max_content_tokens` parameter to set appropriate limits based on your use case and budget considerations.

Example token usage for typical content:
- Average web page (10 kB): ~2,500 tokens
- Large documentation page (100 kB): ~25,000 tokens
- Research paper PDF (500 kB): ~125,000 tokens

## Security considerations

Enabling the web fetch tool in environments where Claude processes untrusted input alongside sensitive data poses data exfiltration risks. Only use this tool in trusted environments or when handling non-sensitive data.

To minimize exfiltration risks, Claude is not allowed to dynamically construct URLs. Claude can only fetch URLs that have been explicitly provided by the user or that come from previous web search or web fetch results.

If data exfiltration is a concern, consider:
- Disabling the web fetch tool entirely
- Using the `max_uses` parameter to limit the number of requests
- Using the `allowed_domains` parameter to restrict to known safe domains

The basic web fetch tool (`web_fetch_20250910`) is eligible for Zero Data Retention (ZDR). The `web_fetch_20260209` version with dynamic filtering is not ZDR-eligible by default because dynamic filtering relies on code execution internally. To use `web_fetch_20260209` with ZDR, disable dynamic filtering by setting `"allowed_callers": ["direct"]` on the tool.
