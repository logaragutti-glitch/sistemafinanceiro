"""Análises com Claude API (cenários 5-7)."""
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
_cli = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def analisar(prompt, max_tokens=800):
    msg = _cli.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}])
    return msg.content[0].text
