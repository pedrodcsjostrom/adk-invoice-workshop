"""The drift guard: `solutions/` must stay in step with the real files.

`solutions/tools.py` and `solutions/agent.py` are the finished versions of the
two gapped files, and an attendee who falls behind recovers by copying one over
the other. That only works if the two files are identical everywhere outside
the fill-in fence — otherwise a `cp` quietly reverts whatever else has changed
since the solutions were written.

This reads committed content (`git show HEAD:...`), not the working copy, so an
attendee's own half-finished edits never trip it. It is the repo's guard, and
the rehearsal's: run it before cutting the workshop tag.
"""

import re
import subprocess

import pytest

FENCE = re.compile(r"^# ={5} (?:END )?FILL-IN\b.*$", re.MULTILINE)

PAIRS = [
    ("invoice_agent/tools.py", "solutions/tools.py"),
    ("invoice_agent/agent.py", "solutions/agent.py"),
]


def _committed(path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"HEAD:{path}"], capture_output=True, text=True
    )
    if result.returncode != 0:
        pytest.skip(f"no committed copy of {path} to compare")
    return result.stdout


def _outside_the_fence(source: str) -> tuple[str, str]:
    """Split a fenced file into (everything outside the fence, the fenced part)."""
    markers = list(FENCE.finditer(source))
    assert len(markers) == 2, f"expected one FILL-IN fence, found {len(markers)} markers"
    opening, closing = markers
    outside = source[: opening.start()] + source[closing.end() :]
    return outside, source[opening.end() : closing.start()]


@pytest.mark.parametrize("shipped_path,solution_path", PAIRS)
def test_identical_outside_the_fence(shipped_path, solution_path):
    shipped_outside, _ = _outside_the_fence(_committed(shipped_path))
    solution_outside, _ = _outside_the_fence(_committed(solution_path))

    assert shipped_outside == solution_outside, (
        f"{solution_path} has drifted from {shipped_path} outside the fill-in fence. "
        f"Copying the solution over would revert unrelated code."
    )


@pytest.mark.parametrize("shipped_path,solution_path", PAIRS)
def test_the_fence_differs(shipped_path, solution_path):
    _, shipped_gap = _outside_the_fence(_committed(shipped_path))
    _, solution_gap = _outside_the_fence(_committed(solution_path))

    assert shipped_gap != solution_gap, f"{shipped_path} ships with the answer already filled in"
    assert len(solution_gap) > len(shipped_gap), f"{solution_path} is not the fuller version"


def test_the_shipped_tool_is_still_a_stub():
    assert "NotImplementedError" in _committed("invoice_agent/tools.py")
    assert "NotImplementedError" not in _committed("solutions/tools.py")


def test_the_shipped_instruction_is_missing_the_re_read():
    assert '_STEPS_RE_READ = ""' in _committed("invoice_agent/agent.py")
    assert "check_invoice_arithmetic a second time" in _committed("solutions/agent.py")
