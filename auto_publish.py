from pathlib import Path
import subprocess

TOPICS_FILE = Path("topics.txt")

if not TOPICS_FILE.exists():
    raise SystemExit("topics.txt not found")

topics = TOPICS_FILE.read_text().strip().splitlines()
if not topics:
    raise SystemExit("No topics left")

topic = topics[0]
remaining = topics[1:]

# Run the publish script
subprocess.run(
    ["bash", "-lc", f'TOPIC="{topic}" ./publish_topic.sh'],
    check=True,
)

# Save remaining topics
TOPICS_FILE.write_text("\n".join(remaining) + "\n")

print(f"Published: {topic}")

