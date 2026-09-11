"""Generate the English Transifex resource from this interpreter's turtle module."""

import argparse
import inspect
import json
import turtle
from pathlib import Path


def generate_catalog():
    if turtle._CFG["language"] != "english":
        raise RuntimeError(
            "Generate the template without a language override in turtle.cfg"
        )

    catalog = {}
    for cls, public_names in (
        ("Turtle", turtle._tg_turtle_functions),
        ("_Screen", turtle._tg_screen_functions),
    ):
        methods = {}
        for name in public_names:
            method = getattr(getattr(turtle, cls), name)
            methods.setdefault(method, []).append(name)

        entries = {}
        for method, names in methods.items():
            # Use CPython's preferred names, including position rather than pos.
            preferred = [
                name for name in names if name not in turtle._alias_list
            ] or names
            name = method.__name__ if method.__name__ in preferred else min(preferred)
            doc = inspect.getdoc(method)
            if not doc:
                raise ValueError(f"Missing docstring for {cls}.{name}")
            entries[name] = {"string": doc + "\n"}
        catalog[cls] = dict(sorted(entries.items()))
    return catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output", type=Path, help="Output path, e.g. dist/en/docstrings.json"
    )
    args = parser.parse_args()
    catalog = generate_catalog()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    count = sum(len(entries) for entries in catalog.values())
    print(f"Generated {count} English docstrings in {args.output}")


if __name__ == "__main__":
    main()
