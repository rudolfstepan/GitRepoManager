"""Check local Markdown links and matching English/German guide filenames."""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    files = sorted([
        *ROOT.glob("*.md"), *(ROOT / "docs").rglob("*.md"), *(ROOT / ".github").rglob("*.md"),
    ])
    errors = []
    links = 0
    for path in files:
        # Code examples are not Markdown links.
        text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
        for match in re.finditer(r"!?\[[^\]\n]+\]\(([^)\n]+)\)", text):
            raw = match.group(1).strip().strip("<>")
            destination = urlsplit(raw)
            if destination.scheme or destination.netloc or not destination.path:
                continue
            target = (path.parent / unquote(destination.path)).resolve()
            links += 1
            if not target.is_relative_to(ROOT) or not target.exists():
                errors.append(f"{path.relative_to(ROOT)}: missing local target {raw}")
    english = {p.relative_to(ROOT / "docs/en") for p in (ROOT / "docs/en").rglob("*.md")}
    german = {p.relative_to(ROOT / "docs/de") for p in (ROOT / "docs/de").rglob("*.md")}
    for missing in sorted(english ^ german):
        errors.append(f"Missing English/German guide counterpart: {missing}")
    for name in ("README.md", "README.de.md", "CONTRIBUTING.md", "CONTRIBUTING.de.md", "LICENSE"):
        if not (ROOT / name).is_file():
            errors.append(f"Missing project document: {name}")
    for error in errors:
        print(error)
    if errors:
        return 1
    print(f"OK: {len(files)} Markdown files, {links} local links, {len(english)} bilingual guide pairs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
