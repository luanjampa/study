"""Banking demo with a semantic cache and a mocked LLM.

Env vars:
  SIM_THRESHOLD  cosine threshold for a cache hit (default 0.8)
  CACHE_SCOPE    "global" (vulnerable, key = prompt only) or "user" (key = user + prompt)
  LAB_DEBUG      "1" adds X-Cache / X-Cache-Sim headers (default 1). Set 0 to force timing-only attacks.
"""
import os
import threading
import time

import numpy as np
from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel

from embed import embed

SIM_THRESHOLD = float(os.getenv("SIM_THRESHOLD", "0.8"))
CACHE_SCOPE = os.getenv("CACHE_SCOPE", "global")
LAB_DEBUG = os.getenv("LAB_DEBUG", "1") == "1"

# Fictional accounts. Each token identifies one test user.
USERS = {
    "token-papafigo": {  # the victim
        "id": "papafigo", "name": "Papa-Figo", "balance": "R$ 48,312.07",
        "account": "0083 / 01585-8", "address": "Av. Cabo Branco, 3000 - João Pessoa, PB",
        "limit": "R$ 15,000.00",
    },
    "token-chico": {  # the attacker
        "id": "chico", "name": "Chico do Pentest", "balance": "R$ 212.40",
        "account": "0083 / 98765-1", "address": "Rua das Trincheiras, 9 - João Pessoa, PB",
        "limit": "R$ 800.00",
    },
}


def fake_llm(user: dict, prompt: str) -> str:
    """Returns account data for the authenticated user using keyword matching."""
    time.sleep(1.5)  # Simulate latency to distinguish cache hits from misses.
    p = prompt.lower()
    if "balance" in p:
        return f"{user['name']}, the balance of account {user['account']} is {user['balance']}."
    if "address" in p:
        return f"{user['name']}, the registered address is {user['address']}."
    if "limit" in p:
        return f"{user['name']}, your available limit is {user['limit']}."
    return "I can help with balance, limit or registered address."


class SemanticCache:
    """Returns the nearest cached answer when cosine similarity meets the threshold."""

    def __init__(self, threshold: float, scope: str):
        self.threshold = threshold
        self.scope = scope
        self.vecs: list[np.ndarray] = []
        self.rows: list[dict] = []
        self.lock = threading.Lock()

    def _candidates(self, user_id: str):
        for vec, row in zip(self.vecs, self.rows):
            if self.scope == "user" and row["owner"] != user_id:
                continue
            yield vec, row

    def lookup(self, prompt: str, user_id: str):
        q = embed([prompt])[0]
        best, best_sim = None, -1.0
        with self.lock:
            for vec, row in self._candidates(user_id):
                sim = float(q @ vec)
                if sim > best_sim:
                    best, best_sim = row, sim
        if best is not None and best_sim >= self.threshold:
            return best, best_sim
        return None, best_sim

    def store(self, prompt: str, response: str, user_id: str):
        with self.lock:
            self.vecs.append(embed([prompt])[0])
            self.rows.append({"prompt": prompt, "response": response, "owner": user_id})

    def reset(self):
        with self.lock:
            self.vecs.clear()
            self.rows.clear()


cache = SemanticCache(SIM_THRESHOLD, CACHE_SCOPE)
app = FastAPI(title="lab-semantic-cache")


class ChatIn(BaseModel):
    prompt: str


def current_user(authorization: str | None) -> dict:
    token = (authorization or "").removeprefix("Bearer ").strip()
    user = USERS.get(token)
    if not user:
        raise HTTPException(401, "invalid token")
    return user


@app.post("/chat")
def chat(body: ChatIn, response: Response, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    # Global scope does not filter entries by user.
    row, sim = cache.lookup(body.prompt, user["id"])
    if row:
        status, answer = "HIT", row["response"]
    else:
        status, answer = "MISS", fake_llm(user, body.prompt)
        cache.store(body.prompt, answer, user["id"])
    if LAB_DEBUG:
        response.headers["X-Cache"] = status
        response.headers["X-Cache-Sim"] = f"{sim:.3f}"
    return {"answer": answer}


@app.post("/admin/reset")
def reset():
    cache.reset()
    return {"ok": True, "scope": CACHE_SCOPE, "threshold": SIM_THRESHOLD}


@app.on_event("startup")
def warmup():
    embed(["warmup"])  # load the model before the first request so timing is clean
