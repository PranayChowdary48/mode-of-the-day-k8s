#!/usr/bin/env bash
set -euo pipefail

NAMESPACE=${NAMESPACE:-mood}
LABEL_SELECTOR=${LABEL_SELECTOR:-app=mood-app}

pods=()
while IFS= read -r p; do
  [[ -n "$p" ]] && pods+=("$p")
done < <(kubectl -n "$NAMESPACE" get pods -l "$LABEL_SELECTOR" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')

if [[ ${#pods[@]} -lt 2 ]]; then
  echo "need at least 2 pods, found ${#pods[@]}" >&2
  exit 1
fi

pod1=${pods[0]}
pod2=${pods[1]}

kubectl -n "$NAMESPACE" port-forward "pod/$pod1" 8081:5000 >/tmp/rr_pf_8081.log 2>&1 &
pf1=$!
kubectl -n "$NAMESPACE" port-forward "pod/$pod2" 8082:5000 >/tmp/rr_pf_8082.log 2>&1 &
pf2=$!

cleanup() {
  kill "$pf1" "$pf2" 2>/dev/null || true
}
trap cleanup EXIT

echo "port-forwarding $pod1 -> http://127.0.0.1:8081"
echo "port-forwarding $pod2 -> http://127.0.0.1:8082"
echo "round-robin proxy on http://127.0.0.1:8080"

python /Users/pranaychowd.pinapaka/Desktop/Projects/k8s/tools/rr_proxy.py \
  --listen 127.0.0.1:8080 \
  http://127.0.0.1:8081 \
  http://127.0.0.1:8082
