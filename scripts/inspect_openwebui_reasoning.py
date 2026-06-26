from pathlib import Path


ROOT = Path("/app/backend/open_webui")


def find_occurrences(needle: str):
    print(f"\n=== Searching for: {needle} ===")
    for path in ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if needle in text:
            print(path)


def print_matches(path: Path, needles: list[str], context: int = 2):
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    print(f"\n=== {path} ===")
    for i, line in enumerate(lines, start=1):
        if any(n in line for n in needles):
            start = max(1, i - context)
            end = min(len(lines), i + context)
            print(f"\n-- lines {start}-{end} --")
            for j in range(start, end + 1):
                print(f"{j:5}: {lines[j-1]}")


def main():
    find_occurrences("metadata['params']")
    find_occurrences('metadata.get("params"')
    find_occurrences("metadata.get('params'")
    find_occurrences("form_data['params']")
    find_occurrences('form_data.get("params"')

    targets = [
        ROOT / "utils" / "middleware.py",
        ROOT / "main.py",
        ROOT / "utils" / "payload.py",
    ]
    needles = [
        "metadata['params']",
        'metadata.get("params"',
        "metadata.get('params'",
        "form_data['params']",
        'form_data.get("params"',
        "reasoning_tags_param",
        "DETECT_REASONING_TAGS",
        "apply_params_to_form_data",
    ]

    for t in targets:
        if t.exists():
            print_matches(t, needles, context=2)


if __name__ == "__main__":
    main()
