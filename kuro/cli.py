import logging
import re
import time

from kuro.agents.unified import chat
from kuro.skills import get_skill, load_skills

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("kuro.cli")

SLASH_CMD_PATTERN = re.compile(r"^/(\S+)\s*(.*)", re.DOTALL)


def detect_skill(text: str) -> str | None:
    """Detect skill from slash command or trigger keyword. Returns skill name or None."""
    slash = SLASH_CMD_PATTERN.match(text)
    if slash:
        cmd = slash.group(1)
        skill = get_skill(cmd)
        if skill:
            return cmd

    text_lower = text.lower()
    for skill in load_skills().values():
        for trigger in skill.get("triggers", []):
            if trigger.lower() in text_lower:
                return skill["name"]

    return None


def main():
    print("Kuro — Knowledge capture & retrieval")
    user_id = input("Username (default): ").strip() or "default"
    print(f"Logged in as: {user_id}")
    print("Type 'exit' to quit.\n")

    history: list[dict] = []

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

        skill = detect_skill(user_input)

        # Strip slash command prefix so the agent sees clean text
        if skill:
            slash = SLASH_CMD_PATTERN.match(user_input)
            if slash:
                user_input = slash.group(2).strip() or user_input

        start = time.time()
        response = chat(user_input, history=history, user_id=user_id, skill=skill)

        skill_label = f" /{skill}" if skill else ""
        print(f"Kuro{skill_label}: {response}")
        log.info(f"Turn: {time.time() - start:.2f}s")


if __name__ == "__main__":
    main()
