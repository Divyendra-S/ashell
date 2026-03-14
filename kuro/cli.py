import logging
import re
import time

from kuro.agents.ingest import ingest
from kuro.agents.query import query

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("kuro.cli")

QUERY_PATTERN = re.compile(
    r"^(who|what|when|where|why|how|tell|is |are |do |does |did |can |could |would |should |has |have )",
    re.IGNORECASE,
)


def classify(text: str) -> str:
    if text.rstrip().endswith("?"):
        return "query"
    if QUERY_PATTERN.match(text):
        return "query"
    return "ingest"


def main():
    print("Kuro — Knowledge capture & retrieval")
    print("Type 'exit' to quit.\n")

    ingest_history: list[dict] = []
    query_history: list[dict] = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Bye!")
            break

        mode = classify(user_input)
        start = time.time()

        if mode == "query":
            response = query(user_input, history=query_history)
        else:
            response = ingest(user_input, history=ingest_history)

        print(f"Kuro [{mode}]: {response}")
        log.info(f"Turn: {time.time() - start:.2f}s")


if __name__ == "__main__":
    main()
