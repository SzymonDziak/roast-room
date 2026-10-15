#!/usr/bin/env python
"""
Check every quoted line in a council session against the seats' brains.

Usage:
  python .claude/skills/roast-room/scripts/check_quotes.py <session folder>

Scans round-*.md and verdict.md for quotes attributed to a source id, like "..." (S095), and looks
for each in the brain files. A quote that is in no brain is either a quote of
another seat or the founder (fine if it appears in an earlier round file of the
same session) or an invented quote (flag it and remove it from the verdict).
Exit code 1 if any quote is unaccounted for.

Quotes may hold nested quote marks, like "Stick with big, "easy" decisions ..." (S090),
and any mix of straight, curly, single and double quote marks.
"""
import re
import sys
from pathlib import Path

BRAINS = Path(__file__).resolve().parents[1] / "brains"

# an opening quote at the start of a line or after a space or bracket, the quoted text (which may
# itself hold quote marks), a closing quote, then a source id within 40 characters,
# e.g. "..." (S095) or "..." [S048, 2026]
QUOTE = re.compile(r"""(?:^|(?<=[\s(\[:*_]))["“](.{20,400}?)["”][^\n"“”]{0,40}?[(\[]S\d{3}""", re.M)
# an opening quote inside a match, where a later quote may start
INNER_OPEN = re.compile(r"""(?<=\s)["“]""")


def norm(s):
    s = s.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    # a single quote used as a quotation mark (not inside a word, like don't) is punctuation
    s = re.sub(r"(?<![a-z0-9])'|'(?![a-z0-9])", " ", s)
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def candidates(q):
    """The whole match, then each tail that starts at an inner opening quote.

    The tails cover a line like: he said "a b c d" and then "the real quote" (S001), where
    the match starts at the first quote and runs to the end of the second.
    """
    yield q
    for m in INNER_OPEN.finditer(q):
        yield q[m.end():]


def find_quotes(text):
    return [m.group(1) for m in QUOTE.finditer(text)]


def check(session, brains=BRAINS):
    session = Path(session)
    brain_text = norm(" ".join(p.read_text(encoding="utf-8", errors="replace") for p in Path(brains).rglob("*.md")))
    session_files = sorted(session.glob("round-*.md")) + [p for p in [session / "verdict.md"] if p.exists()]
    brief = norm((session / "brief.md").read_text(encoding="utf-8")) if (session / "brief.md").exists() else ""
    bad, ok, internal = [], 0, 0
    seen_session = ""
    for f in session_files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for q in find_quotes(text):
            forms = [(c, norm(c)) for c in candidates(q)]
            forms = [(c, n) for c, n in forms if len(n.split()) >= 6]
            if any(n in brain_text for _, n in forms):
                ok += 1
            elif any(n in seen_session or n in brief for _, n in forms):
                internal += 1
            elif forms and len(norm(list(candidates(q))[-1]).split()) >= 6:
                # flag it only when the quote right before the source id is long enough to check
                bad.append((f.name, forms[-1][0]))
        seen_session += " " + norm(text)
    return ok, internal, bad


def main():
    ok, internal, bad = check(sys.argv[1])
    print(f"brain quotes verified: {ok}; quotes of earlier rounds or the brief: {internal}; unverified: {len(bad)}")
    for name, q in bad:
        print(f"  UNVERIFIED [{name}] \"{q[:160]}\"")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
