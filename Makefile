deploy-platform-dev:
	kubectl apply -k platform/ingress-nginx/overlays/local

deploy-platform-prod:
	kubectl apply -k platform/ingress-nginx/overlays/local
	kubectl apply -k platform/argo-rollouts/overlays/local

deploy-app-dev:
	kubectl apply -k k8s/overlays/dev

deploy-app-prod:
	kubectl apply -k k8s/overlays/prod

deploy-dev: deploy-platform-dev deploy-app-dev

deploy-prod: deploy-platform-prod deploy-app-prod

rr-local:
	./tools/rr_start.sh

ingress-local:
	./tools/ingress_start.sh

rollout-set-image:
	kubectl -n mood patch rollout app --type='merge' -p \
	'{"spec":{"template":{"spec":{"containers":[{"name":"app","image":"docker-app:latest"}]}}}}'

rollout-status:
	kubectl -n mood get rollout app -w

rollout-describe:
	kubectl -n mood describe rollout app
