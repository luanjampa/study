"""ANSI colors for the lab output: who owns the data on each line.

  victim    Papa-Figo          bold magenta
  attacker  Chico do Pentest   bold cyan
  leak      victim data delivered to the attacker: white on red

Colors only when stdout is a terminal, so redirected runs (EXPECTED_OUTPUT.txt) stay plain.
NO_COLOR=1 disables, FORCE_COLOR=1 forces (e.g. when piping through `tee`).
"""
import os
import sys

ON = bool(os.getenv("FORCE_COLOR")) or (sys.stdout.isatty() and not os.getenv("NO_COLOR"))


def _style(code):
    return lambda text: f"\033[{code}m{text}\033[0m" if ON else str(text)


victim = _style("1;35")
attacker = _style("1;36")
leak = _style("1;97;41")
good = _style("1;32")
bad = _style("1;31")
dim = _style("2")
