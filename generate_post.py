import os
import random
import re
import subprocess
from datetime import datetime
from pathlib import Path

from openai import OpenAI

# -----------------------
# Paths / files
# -----------------------
SITE_ROOT = Path(__file__).resolve().parent
CONTENT_DIR = SITE_ROOT / "content" / "posts"

TOPICS_FILE = SITE_ROOT / "automation" / "topics.txt"
USED_TOPICS_FILE = SITE_ROOT / "automation" / "topics_used.txt"

# -----------------------
# Prompting
# -----------------------
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

Structure:
- H1 title
- Short intro (why this matters)
- Clear section headers (H2/H3)
- Bullet points where helpful

Do NOT:
- Use emojis
- Mention selling picks
- Make income claims
"""

# -----------------------
# Topic rotation (no duplicates)
# -----------------------
def get_next_topic() -> str:
    if not TOPICS_FILE.exists():
        raise SystemExit(
            f"topics.txt not found at: {TOPICS_FILE}\n"
            "Create it with one topic per line (automation/topics.txt).\n"
        )

    all_topics = [
        t.strip()
        for t in TOPICS_FILE.read_text(encoding="utf-8").splitlines()
        if t.strip()
    ]

    used = set()
    if USED_TOPICS_FILE.exists():
        used = {
            t.strip()
            for t in USED_TOPICS_FILE.read_text(encoding="utf-8").splitlines()
            if t.strip()
        }

    remaining = [t for t in all_topics if t not in used]

    if not remaining:
        raise SystemExit(
            "All topics exhausted.\n"
            "Add more lines to automation/topics.txt or clear automation/topics_used.txt.\n"
        )

    topic = random.choice(remaining)

    USED_TOPICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with USED_TOPICS_FILE.open("a", encoding="utf-8") as f:
        f.write(topic + "\n")

    return topic

# -----------------------
# Markdown helpers + CTAs
# -----------------------
INTRO_CTA_MARKER = "<!-- SVS_INTRO_CTA -->"

def normalize_md(md: str) -> str:
    md = md.replace("\r\n", "\n").replace("\r", "\n")
    return md.strip() + "\n"


def ensure_intro_cta(md: str) -> str:
    """
    Inserts a short CTA near the top of the article.
    Works even if the intro is a single long paragraph.
    Uses a marker to avoid duplicates.
    """
    md_norm = normalize_md(md)

    if INTRO_CTA_MARKER in md_norm:
        return md_norm

    lines = md_norm.splitlines()

    # Find H1
    h1_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# "):
            h1_idx = i
            break

    if h1_idx is None:
        return md_norm

    # Find first non-empty line after H1
    intro_start = None
    for i in range(h1_idx + 1, len(lines)):
        if lines[i].strip():
            intro_start = i
            break

    if intro_start is None:
        return md_norm

    # Insert CTA after intro paragraph OR after a couple lines max
    insert_at = intro_start + 1
    for i in range(intro_start + 1, min(intro_start + 4, len(lines))):
        if lines[i].strip() == "":
            insert_at = i
            break

    cta_block = [
        "",
        INTRO_CTA_MARKER,
        "**Want the full framework?**",
        "→ [Get the Free Guide](/free-guide/)",
        "*No picks. No hype. Unsubscribe anytime.*",
        "",
    ]

    new_lines = lines[:insert_at] + cta_block + lines[insert_at:]
    return "\n".join(new_lines).strip() + "\n"


def ensure_cta_footer(md: str) -> str:
    """
    Ensures every article ends with a consistent footer:
    - Disclaimer
    - "How professionals think about this" section (if missing)
    - CTA to /free-guide/ (if missing)
    Avoids duplicates.
    """
    md_norm = ensure_intro_cta(md)
    lower = md_norm.lower()

    has_free_guide_link = "/free-guide/" in lower
    footer_parts: list[str] = []

    # Disclaimer
    if "educational only" not in lower:
        footer_parts.append("> Educational only; not betting advice.\n")

    # Ensure "How professionals think..." exists
    if "how professionals think about this" not in lower:
        footer_parts.append("## How professionals think about this\n")
        footer_parts.append(
            "- They focus on calibration and process, not short-term outcomes.\n"
            "- They separate signal from noise over many trials.\n"
            "- They care about prices, liquidity, and incentives—not narratives.\n"
        )

    # CTA
    if not has_free_guide_link:
        footer_parts.append(
            "\nIf this was useful, the free guide walks through the core mechanics and mental models.\n"
            "→ [Get the Free Guide](/free-guide/)\n"
        )

    if not footer_parts:
        return md_norm

    return md_norm + "\n---\n\n" + "".join(footer_parts).strip() + "\n"

# -----------------------
# Misc helpers
# -----------------------
def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text or "post"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


# -----------------------
# Main
# -----------------------
def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set. Run: export OPENAI_API_KEY='...'\n")

    # If TOPIC is provided, use it. Otherwise auto-pick a fresh one.
    topic = os.getenv("TOPIC")
    if not topic:
        topic = get_next_topic()

    print(f"Using topic: {topic}")

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

    # Enforce CTAs deterministically
    text = ensure_cta_footer(text)

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
        safe_title = title.replace('"', "'")
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