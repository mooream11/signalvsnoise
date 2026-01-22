import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from openai import OpenAI

SITE_ROOT = Path(__file__).resolve().parent
CONTENT_DIR = SITE_ROOT / "content" / "posts"

SYSTEM_INSTRUCTIONS = """You are writing an educational article for SignalVsNoise, an anonymous,
data-driven site explaining prediction markets and sharp betting.

Tone:
- Clear, neutral, analytical
- No hype, no promises
- Assume intelligent but non-expert reader

Requirements:
- 1,200–1,500 words
- Simple explanations first, then depth
- Use examples (NBA when relevant)
- No picks, no betting advice
- Explain incentives and mechanics
- End with a short section: "How professionals think about this"

Structure:
- H1 title
- Short intro (why this matters)
- Clear section headers (H2/H3)
- Bullet points where helpful
- Add a short disclaimer: "Educational only; not betting advice."
- End with a soft CTA to the Free Guide page (/free-guide/)

Do NOT:
- Use emojis
- Mention selling picks
- Make income claims
"""


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text or "post"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set. Run: export OPENAI_API_KEY='...'\n")

    topic = os.getenv("TOPIC")
    if not topic:
        topic = input("Topic: ").strip()
    if not topic:
        raise SystemExit("Topic cannot be empty.\n")

    client = OpenAI(api_key=api_key)

    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": f"Write the article. Topic: {topic}"},
        ],
    )

    text = (resp.output_text or "").strip()
    if not text:
        raise SystemExit("Model returned empty output.\n")

    # Derive title: use first markdown H1 if present, otherwise the topic
    title = topic
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break

    date = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date}-{slugify(title)}.md"
    outpath = CONTENT_DIR / filename
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    # If the model already included frontmatter, keep it; otherwise add it.
    if not text.lstrip().startswith("---"):
        safe_title = title.replace('"', "'")  # avoid breaking YAML frontmatter
        frontmatter = (
            f"---\n"
            f'title: "{safe_title}"\n'
            f"date: {date}\n"
            f"draft: false\n"
            f"---\n\n"
        )
        text = frontmatter + text

    outpath.write_text(text, encoding="utf-8")
    print(f"\n✅ Wrote: {outpath}")

    # Build site (updates public/)
    run(["hugo"])
    print("✅ Hugo build complete (public/ updated)")


if __name__ == "__main__":
    main()
