deploy-dev:
	kubectl apply -k platform/ingress-nginx/overlays/local
	kubectl apply -k k8s/overlays/dev

deploy-prod:
	kubectl apply -k platform/ingress-nginx/overlays/local
	kubectl apply -k platform/argo-rollouts/overlays/local
	kubectl apply -k k8s/overlays/prod

deploy-platform-dev:
	kubectl apply -k platform/ingress-nginx/overlays/local

deploy-platform-prod:
	kubectl apply -k platform/ingress-nginx/overlays/local
	kubectl apply -k platform/argo-rollouts/overlays/local

.PHONY: deploy-dev deploy-prod deploy-platform-dev deploy-platform-prod ingress-local \
	test-basic test-whoami test-sticky test-auth-refresh test-rate-limit test-envoy-metrics test-envoy-cb test-prom-targets test-hpa-metrics \
	test-redis-repl load-test chaos-pod chaos-redis chaos-ingress pdb-check

ingress-local:
	./tools/ingress_start.sh


test-basic:
	curl -I http://localhost:8089/

test-whoami:
	for i in 1 2 3 4 5 6 7 8 9 10; do curl -s http://localhost:8089/whoami; echo; done

test-sticky:
	curl -I http://localhost:8089/ | grep -i set-cookie || true

test-auth-refresh:
	command curl --config /dev/null -i -X POST http://localhost:8089/refresh | head -n 1; \
	command curl --config /dev/null -i -u mood:mood -X POST http://localhost:8089/refresh | head -n 1

test-rate-limit:
	seq 1 200 | xargs -n1 -P40 curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8089/ | sort | uniq -c

test-envoy-metrics:
	POD=$$(kubectl -n mood get pods -l app=mood-app -o jsonpath='{.items[0].metadata.name}'); \
	kubectl -n mood exec "$$POD" -c app -- python -c "import urllib.request; print('\n'.join(urllib.request.urlopen('http://127.0.0.1:9901/stats/prometheus').read().decode().splitlines()[:10]))"

test-envoy-cb:
	for i in $$(seq 1 200); do curl -s -o /dev/null http://localhost:8089/ & done; wait; \
	POD=$$(kubectl -n mood get pods -l app=mood-app -o jsonpath='{.items[0].metadata.name}'); \
	kubectl -n mood exec "$$POD" -c app -- python -c "import urllib.request; d=urllib.request.urlopen('http://127.0.0.1:9901/stats/prometheus').read().decode().splitlines(); print('\n'.join([l for l in d if 'circuit_breakers' in l or 'overflow' in l][:20]))"

test-prom-targets:
	curl http://localhost:9090/targets

test-hpa-metrics:
	kubectl -n mood get --raw "/apis/custom.metrics.k8s.io/v1beta1" | head; \
	kubectl -n mood describe hpa app-hpa

test-redis-repl:
	kubectl -n mood exec -it redis-0 -- redis-cli info replication | head -n 20; \
	kubectl -n mood exec -it redis-1 -- redis-cli info replication | head -n 20; \
	kubectl -n mood exec -it redis-0 -- redis-cli set demo:test 123; \
	kubectl -n mood exec -it redis-1 -- redis-cli get demo:test

load-test:
	seq 1 8000 | xargs -n1 -P80 curl -s http://localhost:8089/ >/dev/null

chaos-pod:
	POD=$$(kubectl -n mood get pods -l app=mood-app -o jsonpath='{.items[0].metadata.name}'); \
	kubectl -n mood delete pod "$$POD"

chaos-redis:
	kubectl -n mood scale statefulset/redis --replicas=0; \
	sleep 5; \
	curl -I http://localhost:8089/ | head -n 1; \
	kubectl -n mood scale statefulset/redis --replicas=1

chaos-ingress:
	kubectl -n ingress-nginx rollout restart deploy/ingress-nginx-controller

pdb-check:
	kubectl -n mood get pdb app-pdb
