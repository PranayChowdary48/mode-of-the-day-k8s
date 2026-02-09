deploy-platform:
	kubectl apply -k platform/ingress-nginx/overlays/dev

deploy-app:
	kubectl apply -k k8s/overlays/dev

deploy: deploy-platform deploy-app

rr-local:
	./tools/rr_start.sh

ingress-local:
	./tools/ingress_start.sh
