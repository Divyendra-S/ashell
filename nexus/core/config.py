import os
from pathlib import Path

from dotenv import load_dotenv

# Load from root .env
load_dotenv(Path(__file__).parent.parent.parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "nexus123")

MODEL = os.getenv("MODEL", "gemini-3.1-pro-preview")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
GEMINI_STREAM_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:streamGenerateContent?alt=sse"
