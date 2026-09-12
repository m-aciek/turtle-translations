"""Compile KEYVALUEJSON translation catalogues into standalone turtle modules."""

import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def load_catalog(path):
    """Read a nested KEYVALUEJSON resource."""
    groups = read_json(path)
    language = path.parent.name
    if not re.fullmatch(r"[a-z]{2,3}(?:_[a-z0-9]+)*", language):
        raise ValueError(f"{path}: invalid language code")
    if (
        not isinstance(groups, dict)
        or not groups
        or set(groups) - {"Turtle", "_Screen"}
    ):
        raise ValueError(f"{path}: expected Turtle and/or _Screen docstrings")
    docsdict = {}
    for cls, entries in groups.items():
        if not isinstance(entries, dict) or not entries:
            raise ValueError(f"{path}: {cls} must contain entries")
        for method, entry in entries.items():
            if not re.fullmatch(r"[a-z][a-z0-9_]*", method):
                raise ValueError(f"{path}: invalid method name {method!r}")
            key = f"{cls}.{method}"
            if not isinstance(entry, str):
                raise ValueError(f"{path}: {key} must be a translation string")
            # Transifex's "Download file to translate" leaves untranslated strings empty.
            # Skip them so turtle keeps its English help, including for aliases.
            if entry.strip():
                docsdict[key] = entry

    return language, dict(sorted(docsdict.items()))


def render_module(docsdict):
    # repr() quotes translator-provided text as data, including quotes/backslashes.
    lines = [
        '"""Generated from the turtle-translations JSON catalogue; do not edit."""',
        "",
        "docsdict = {",
    ]
    lines.extend(f"    {key!r}: {value!r}," for key, value in sorted(docsdict.items()))
    return "\n".join([*lines, "}", ""])


class TranslationBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        paths = sorted((Path(self.root) / "translations").glob("*/docstrings.json"))
        if not paths:
            raise ValueError("No translation catalogues found")
        catalogs = [load_catalog(path) for path in paths]
        self.generated = TemporaryDirectory(prefix="turtle-translations-")
        for language, docsdict in catalogs:
            filename = f"turtle_docstringdict_{language}.py"
            output = Path(self.generated.name) / filename
            output.write_text(render_module(docsdict), encoding="utf-8")
            build_data["force_include"][str(output)] = filename

    def finalize(self, version, build_data, artifact_path):
        self.generated.cleanup()
