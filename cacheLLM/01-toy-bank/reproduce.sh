#!/bin/sh
# Lab 01 - toy bank: cross-user leak through a semantic cache with a global key.
#   1/2 vulnerable: CACHE_SCOPE=global (shared cache)
#   2/2 fixed     : CACHE_SCOPE=user   (the user is part of the key)
# Needs .venv at the repository root. First run downloads the embedding model.
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
ROOT="$(cd ../.. && pwd)"; PY="$ROOT/.venv/bin/python"
PORT=8000

run() {  # $1 = CACHE_SCOPE
  (CACHE_SCOPE="$1" LAB_DEBUG=1 nohup "$PY" -m uvicorn app:app --port $PORT >/tmp/sc_lab01.log 2>&1 &)
  for i in $(seq 1 120); do curl -s -m 2 -X POST "127.0.0.1:$PORT/admin/reset" >/dev/null 2>&1 && return 0; sleep 1; done
  echo "[!] server did not start; last lines of /tmp/sc_lab01.log:"; tail -5 /tmp/sc_lab01.log; return 1
}
stop() { pkill -f "uvicorn app:app --port $PORT" 2>/dev/null; sleep 1; }

echo "== 1/2 vulnerable: global cache key (CACHE_SCOPE=global)"
stop; run global
"$PY" attack.py "http://127.0.0.1:$PORT"; VULN=$?
stop

echo
echo "== 2/2 fixed: user in the key (CACHE_SCOPE=user)"
run user
"$PY" attack.py "http://127.0.0.1:$PORT"; FIXED=$?
stop

echo
if [ "$VULN" -eq 0 ] && [ "$FIXED" -eq 1 ]; then
  echo "LAB 01 OK: leak reproduced with the global key, gone with the user in the key"
  exit 0
fi
echo "LAB 01 UNEXPECTED (vulnerable=$VULN fixed=$FIXED)"; exit 2
