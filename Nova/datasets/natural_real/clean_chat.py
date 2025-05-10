import re
import os

base_dir = os.path.dirname(__file__)
input_path = os.path.join(base_dir, "NATURALDATA.txt")
output_path = os.path.join(base_dir, "NATURALDATA_cleaned.txt")

with open(input_path, encoding="utf-8") as f:
    lines = [line.rstrip() for line in f]

output = []
user = None
timestamp = None
buffer = []
in_quote = False

def flush():
    global user, timestamp, buffer
    if user and buffer:
        msg = " ".join(buffer).strip()
        if msg:
            output.append(f"{timestamp} | {user}: {msg}")
    buffer.clear()

for i, line in enumerate(lines):
    # Detect timestamp lines (e.g., Fri 8:24 AM)
    if re.match(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)", line) and "AM" in line or "PM" in line:
        flush()
        timestamp = line
        user = None
        continue
    # Detect user lines (not empty, not timestamp, not quoted/system)
    if line and not line.startswith("Quoted") and not line.startswith("End Quote") and not line.startswith("Space update:") and not line.startswith("Image") and not line.startswith("Edited") and not line.startswith("https://") and not line.startswith("YouTube video") and not line.startswith("System"):
        # If previous user exists, flush
        if user and buffer:
            flush()
        user = line
        continue
    # Quoted block
    if line.startswith("Quoted"):
        in_quote = True
        buffer.append("\n  Quoted:")
        continue
    if line.startswith("End Quote"):
        in_quote = False
        buffer.append("  End Quote")
        continue
    # System messages, images, etc. are skipped
    if not line or line.startswith("Space update:") or line.startswith("Image") or line.startswith("Edited") or line.startswith("https://") or line.startswith("YouTube video") or line.startswith("System"):
        continue
    # Add message lines
    if in_quote:
        buffer.append("  " + line)
    else:
        buffer.append(line)

flush()

with open(output_path, "w", encoding="utf-8") as f:
    for line in output:
        f.write(line + "\n")

print(f"Cleaned chat saved to {output_path}")