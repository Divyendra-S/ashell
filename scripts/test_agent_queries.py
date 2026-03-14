"""Test the query agent end-to-end with real LLM calls."""
import logging
import sys

sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

from kuro.agents.query import query

TESTS = [
    {
        "q": "What do I know about prompt caching? What models support it and what are the pricing tiers?",
        "expect": "Should cite the prompt caching article with specific pricing details",
    },
    {
        "q": "How does the web fetch tool work? What are its security considerations?",
        "expect": "Should cite web fetch article, mention URL validation, domain filtering, exfiltration risks",
    },
    {
        "q": "What is programmatic tool calling and why is it useful?",
        "expect": "Should cite programmatic tool calling article, mention reduced latency and token savings",
    },
    {
        "q": "What is Proof and who created it?",
        "expect": "Should reference the Introducing Proof article from Every",
    },
    {
        "q": "Compare the different Claude API tools I have articles about",
        "expect": "Should list articles and compare web fetch, programmatic tool calling, prompt caching",
    },
]

for i, test in enumerate(TESTS, 1):
    print(f"\n{'='*60}")
    print(f"TEST {i}: {test['q']}")
    print(f"EXPECT: {test['expect']}")
    print("=" * 60)
    try:
        answer = query(test["q"])
        print(f"\nANSWER:\n{answer}")
    except Exception as e:
        print(f"\nFAILED: {e}")
    print()
