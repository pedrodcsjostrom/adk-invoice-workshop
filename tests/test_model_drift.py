"""The drift guard for the architecture model: the diagram must stay true.

`docs/architecture/workspace.dsl` is the first document in the kit that names code
artifacts — module paths in component technology fields, and the three tools
named individually rather than collapsed into one box. A diagram that names
code rots the moment the code moves, and nothing in a rendered SVG complains.
This is what complains.

Three claims are pinned. Every module path the model names still exists on
disk. The tool components in the model are exactly the functions the agent is
given, so renaming a tool breaks the build rather than the picture. And the
vocabulary the model borrows from `CONTEXT.md` is spelled the way the glossary
spells it, and avoids the synonyms the glossary tells it to avoid.

It reads the workspace as text. No Docker, no Structurizr, no network — the
suite still finishes in seconds. Like the `solutions/` drift guard it skips
rather than fails when its precondition is missing: an attendee who has not
written the fill-in gap yet should not see a red test about a diagram.
"""

import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_PATH = os.path.join(REPO_ROOT, "docs", "architecture", "workspace.dsl")
CONTEXT_PATH = os.path.join(REPO_ROOT, "CONTEXT.md")

# A repo-relative path named anywhere in the model: `invoice_agent/upload.py`,
# `data/vendor_registry.json`. Matched generically rather than from a list, so
# a component added tomorrow is covered without touching this file. The slash
# is required: it is what separates a repo path from a bare filename such as
# the theme the views load from beside the workspace.
MODULE_PATH = re.compile(r"[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)+\.(?:py|json)\b")

COMPONENT = re.compile(r"^\s*\w+\s*=\s*component\s+\"([^\"]+)\"", re.MULTILINE)

# A component named the way a Python function is named is a tool, with one
# exception: the agent itself is a component too, and it is named after the
# `LlmAgent` rather than after a function. It is excluded by name at runtime.
FUNCTION_NAME = re.compile(r"^[a-z_][a-z0-9_]*$")

# The vocabulary the workspace borrows from the glossary. Every one of these
# must be a glossary entry, and the model must not use its `_Avoid_` synonyms.
BORROWED_TERMS = [
    "Rigged invoice",
    "Re-read",
    "Validation",
    "Document guard",
    "Upload page",
    "Records page",
    "Origin shim",
    "Attendee",
    "Deployed service",
    "Store",
    "Supplier registry",
    "Trace summary",
]


def _read_or_skip(path: str, reason: str) -> str:
    if not os.path.exists(path):
        pytest.skip(reason)
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _workspace() -> str:
    return _read_or_skip(WORKSPACE_PATH, "no docs/architecture/workspace.dsl to check")


def _context() -> str:
    return _read_or_skip(CONTEXT_PATH, "no CONTEXT.md to check the vocabulary against")


def _agent_tool_names() -> set[str]:
    """The names of the functions `root_agent` is actually given.

    ADK accepts bare functions and wraps some of them, so the name lives in a
    different attribute depending on what was passed. On a fresh clone the
    import can fail outright, because `invoice_agent/tools.py` ships with a
    gap in it — that is a skip, not a failure.
    """
    try:
        from invoice_agent.agent import root_agent

        tools = root_agent.tools
    except Exception as error:  # noqa: BLE001 - any import-time failure is a skip
        pytest.skip(f"the agent could not be imported, so its tools cannot be read: {error}")

    names = set()
    for tool in tools:
        name = (
            getattr(tool, "name", None)
            or getattr(getattr(tool, "func", None), "__name__", None)
            or getattr(tool, "__name__", None)
        )
        if name is None:
            pytest.skip(f"cannot read a tool name off {tool!r}")
        names.add(name)
    return names


def _agent_name() -> str:
    from invoice_agent.agent import root_agent

    return root_agent.name


def _glossary_entry(context: str, term: str) -> str | None:
    """The body of a `**Term**:` glossary entry, up to the next entry."""
    heading = re.compile(rf"^\*\*{re.escape(term)}\*\*\s*[,:]", re.MULTILINE | re.IGNORECASE)
    match = heading.search(context)
    if match is None:
        return None
    rest = context[match.end() :]
    following = re.search(r"^\*\*", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def _avoided_synonyms(entry: str) -> list[str]:
    match = re.search(r"^_Avoid_:(.*)$", entry, re.MULTILINE)
    if match is None:
        return []
    return [word.strip().strip("`") for word in match.group(1).split(",") if word.strip()]


def _mask(text: str, terms: list[str]) -> str:
    """Blank out every canonical spelling, so only the alternatives are left."""
    for term in sorted(terms, key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(term)}\b", " " * len(term), text, flags=re.IGNORECASE)
    return text


def test_every_module_the_model_names_still_exists():
    """A component stands for a file. Move the file and the model is a lie."""
    named = sorted(set(MODULE_PATH.findall(_workspace())))

    assert named, "the model names no modules at all — has the technology field been dropped?"

    missing = [path for path in named if not os.path.exists(os.path.join(REPO_ROOT, path))]
    assert not missing, (
        f"docs/architecture/workspace.dsl names {missing}, which no longer exist. "
        f"Either the model is out of date or the code moved without it."
    )


def test_the_tool_components_are_exactly_the_agents_tools():
    """Rename a tool and the box in the component view stops being real."""
    workspace = _workspace()
    expected = _agent_tool_names()

    declared = {
        name
        for name in COMPONENT.findall(workspace)
        if FUNCTION_NAME.match(name) and name != _agent_name()
    }

    assert declared == expected, (
        f"the model draws tools {sorted(declared)} but the agent is given "
        f"{sorted(expected)}. The component view names functions, so a rename "
        f"has to reach docs/architecture/workspace.dsl too."
    )


@pytest.mark.parametrize("term", BORROWED_TERMS)
def test_a_borrowed_term_is_a_glossary_entry(term):
    """The model borrows the glossary's words; the glossary has to have them."""
    assert _glossary_entry(_context(), term) is not None, (
        f"docs/architecture/workspace.dsl uses \"{term}\", but CONTEXT.md has no "
        f"**{term}**: glossary entry to spell it."
    )


@pytest.mark.parametrize("term", BORROWED_TERMS)
def test_the_model_avoids_the_synonyms_the_glossary_rejects(term):
    """Each entry lists the words it exists to replace. None may appear here."""
    entry = _glossary_entry(_context(), term)
    if entry is None:
        pytest.skip(f"CONTEXT.md has no **{term}**: entry yet")

    canonical = {word.lower() for word in BORROWED_TERMS}
    # Text already spelled the glossary's way is not drift, even when a
    # rejected synonym is a substring of it: "the trace summary" contains "the
    # trace", which **Trace summary** exists to replace. Blanking the canonical
    # spellings first leaves only the places the model chose another word.
    workspace = _mask(_workspace(), BORROWED_TERMS)

    for synonym in _avoided_synonyms(entry):
        # An `_Avoid_` line sometimes rejects a word that is another entry's
        # canonical name — "Document guard" tells prose not to call the guard
        # "validation", while **Validation** is a term in its own right. The
        # model is entitled to the canonical spelling, so those are skipped.
        if any(re.search(rf"\b{re.escape(name)}\b", synonym.lower()) for name in canonical):
            continue

        assert not re.search(rf"\b{re.escape(synonym)}\b", workspace, re.IGNORECASE), (
            f"docs/architecture/workspace.dsl says \"{synonym}\", which CONTEXT.md "
            f"lists under _Avoid_ for **{term}**. Use \"{term}\"."
        )
