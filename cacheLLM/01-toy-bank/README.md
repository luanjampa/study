# Lab 01: Toy bank

A small banking app that demonstrates how a shared semantic cache can return one user's
private data to another. It uses real embeddings and a mocked LLM, with no Docker, Redis,
or API keys required.

## Test users

| Role | Who | Color in the terminal |
|------|-----|-----------------------|
| Victim | Papa-Figo, a customer of Ponta do Seixas Bank | magenta |
| Attacker | Chico do Pentest, authenticated with his own token | cyan |
| Leak | Papa-Figo's data delivered to Chico | white on red |

All account data is fictitious. Names and addresses reference João Pessoa.

## What you will see

Papa-Figo asks "What is my account balance?" The mocked LLM returns his balance, and the
cache stores the answer. Chico then sends five balance questions using his own token.
If a question matches the cached prompt with a cosine similarity of at least 0.8,
he receives Papa-Figo's answer. A sixth question, about his registered address, serves
as a negative control.

With `CACHE_SCOPE=user`, cache lookups only consider entries belonging to the caller.
Chico no longer receives Papa-Figo's cached answer.

```
[chico]     LEAK  sim=0.987 HIT      21ms  'what is my account balance'
            -> Papa-Figo, the balance of account 0083 / 01585-8 is R$ 48,312.07.
...
[+] VULNERABLE: authenticated as Chico do Pentest, 1/6 prompts returned Papa-Figo's cached answer
```

## Run

```bash
./reproduce.sh
```

The script expects a Python environment at `.venv` in the repository root, with FastAPI,
Uvicorn, NumPy, HTTPX, and sentence-transformers installed. The embedding model is
downloaded on the first run.

The script starts the app twice: first with a shared cache, then with a cache scoped to
each user. It exits with status 0 when the first run leaks data and the second does not.
See `EXPECTED_OUTPUT.txt` for a sample run. Timings may vary.
Colors only appear on a terminal (`NO_COLOR=1` disables, `FORCE_COLOR=1` forces).

## How it works

- `app.py`: FastAPI app. `POST /chat` authenticates the Bearer token before looking up
  the prompt in the cache. In global mode, all entries are candidates. In user mode,
  only the caller's entries are candidates. The mocked LLM adds a 1.5-second delay
  so the timing difference between hits and misses is visible.
- `embed.py`: generates embeddings using `paraphrase-multilingual-MiniLM-L12-v2`.
- `attack.py`: sends the six test prompts and checks for Papa-Figo's name in the answers.
- `paint.py`: colors the terminal output to distinguish each user's data and leaked answers.

## Why it leaks

The app authenticates each request, but the shared cache selects an answer using only
prompt similarity. It does not check who owns that answer. A valid token therefore does
not prevent a user from receiving another user's data on a cache hit.

Scoping lookups by user fixes the leak demonstrated here. The mock still uses keyword
matching, so some paraphrases receive a generic response instead of account data.
