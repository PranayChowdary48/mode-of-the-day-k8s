#!/usr/bin/env bash
set -euo pipefail

INGRESS_NS=${INGRESS_NS:-ingress-nginx}
INGRESS_SVC=${INGRESS_SVC:-ingress-nginx-controller}
INGRESS_HOST=${INGRESS_HOST:-mood.local}
APP_NS=${APP_NS:-mood}

kubectl -n "$INGRESS_NS" port-forward "svc/$INGRESS_SVC" 8080:80 >/tmp/ingress_pf_8080.log 2>&1 &
pf=$!
kubectl -n "$APP_NS" port-forward svc/prometheus 9090:9090 >/tmp/prom_pf_9090.log 2>&1 &
pf_prom=$!
kubectl -n "$APP_NS" port-forward svc/grafana 3000:3000 >/tmp/graf_pf_3000.log 2>&1 &
pf_graf=$!

cleanup() {
  kill "$pf" "$pf_prom" "$pf_graf" 2>/dev/null || true
}
trap cleanup EXIT

echo "ingress port-forward: http://127.0.0.1:8080"
echo "host-header proxy:   http://127.0.0.1:8088 (Host: $INGRESS_HOST)"
echo "prometheus:          http://127.0.0.1:9090"
echo "grafana:             http://127.0.0.1:3000"

python /Users/pranaychowd.pinapaka/Desktop/Projects/k8s/tools/ingress_host_proxy.py \
  --listen 127.0.0.1:8088 \
  --upstream 127.0.0.1:8080 \
  --host "$INGRESS_HOST"
