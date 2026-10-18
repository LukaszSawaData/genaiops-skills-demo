"""Lint plików SKILL.md przed wysłaniem do Foundry (reguły z dokumentacji Skills API)."""
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$")


def validate(path: Path) -> list[str]:
    errors = []
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return [f"{path}: brak bloku YAML front matter"]
    front, body = m.groups()
    fields = dict(
        line.split(":", 1) for line in front.splitlines() if ":" in line
    )
    fields = {k.strip(): v.strip() for k, v in fields.items()}

    name = fields.get("name", "")
    desc = fields.get("description", "")
    if not name:
        errors.append("brak pola name")
    elif name[0] in "'\"":
        errors.append("name nie może być w cudzysłowie")
    elif not NAME_RE.match(name) or "--" in name or len(name) > 64:
        errors.append(f"niepoprawna nazwa '{name}'")
    elif name != path.parent.name:
        errors.append(f"name '{name}' musi być równe nazwie folderu '{path.parent.name}'")

    if not desc:
        errors.append("brak pola description")
    elif desc[0] in "'\"":
        errors.append("description nie może być w cudzysłowie")
    elif len(desc) > 1024:
        errors.append("description dłuższe niż 1024 znaki")

    if len(body.strip()) < 50:
        errors.append("treść skilla jest pusta lub zbyt krótka")
    return [f"{path}: {e}" for e in errors]


if __name__ == "__main__":
    files = sorted(Path("skills").glob("*/SKILL.md"))
    all_errors = [e for f in files for e in validate(f)]
    for e in all_errors:
        print("BŁĄD:", e)
    print(f"Sprawdzono {len(files)} skill(e), błędów: {len(all_errors)}")
    sys.exit(1 if all_errors else 0)
