import logging
import re
import time

from kuro.agents.ingest import ingest
from kuro.agents.query import query
from kuro.skills import get_skill

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("kuro.cli")

QUERY_PATTERN = re.compile(
    r"^(who|what|when|where|why|how|tell|is |are |do |does |did |can |could |would |should |has |have |find |show |list |compare |explain |describe |give |if I |summarize |search |research |deep dive|investigate|quiz me|test me|I want to )",
    re.IGNORECASE,
)

SLASH_CMD_PATTERN = re.compile(r"^/(\S+)\s*(.*)", re.DOTALL)


def classify(text: str) -> tuple[str, str | None]:
    slash = SLASH_CMD_PATTERN.match(text)
    if slash:
        cmd = slash.group(1)
        skill = get_skill(cmd)
        if skill:
            return (skill.get("mode", "query"), cmd)

    if text.rstrip().endswith("?"):
        return ("query", None)
    if QUERY_PATTERN.match(text):
        return ("query", None)
    return ("ingest", None)


def main():
    print("Kuro — Knowledge capture & retrieval")
    user_id = input("Username (default): ").strip() or "default"
    print(f"Logged in as: {user_id}")
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

        mode, skill = classify(user_input)

        # Strip slash command prefix so the agent sees clean text
        if skill:
            slash = SLASH_CMD_PATTERN.match(user_input)
            if slash:
                user_input = slash.group(2).strip() or user_input

        start = time.time()

        if mode == "query":
            response = query(user_input, history=query_history, user_id=user_id, skill=skill)
        else:
            skill_instructions = None
            if skill:
                skill_data = get_skill(skill)
                if skill_data:
                    skill_instructions = f"## Active Skill: /{skill_data['name']}\n{skill_data['body']}"
            response = ingest(user_input, history=ingest_history, user_id=user_id, skill_instructions=skill_instructions)

        skill_label = f" /{skill}" if skill else ""
        print(f"Kuro [{mode}{skill_label}]: {response}")
        log.info(f"Turn: {time.time() - start:.2f}s")


if __name__ == "__main__":
    main()
