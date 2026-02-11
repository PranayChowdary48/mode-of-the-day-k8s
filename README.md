make deploy-dev
make deploy-prod

Rollouts (prod):
make rollout-set-image
make rollout-status
make rollout-describe

Dev overlay removes: NetworkPolicies, Prometheus Adapter (custom metrics), Argo Rollouts.
Prod overlay uses Rollouts + NetworkPolicies + custom-metrics HPA.

platform components:
make deploy-platform-dev
make deploy-platform-prod

kubectl -n mood port-forward svc/app 8080:80
kubectl -n mood port-forward svc/prometheus 9090:9090
kubectl -n mood port-forward svc/grafana 3000:3000

Ingress access without /etc/hosts (host-header proxy):
make ingress-local
open http://localhost:8088/

minikube status
kubectl get nodes
kubectl -n ingress-nginx get pods
kubectl -n mood get all
kubectl -n mood get ingress
kubectl -n mood get pods
kubectl -n mood describe ingress mood-ingress

kubectl -n mood logs app-cbf7484b-z7rvg --previous
kubectl -n mood logs app-cbf7484b-z7rvg
kubectl -n mood describe pod app-cbf7484b-z7rvg
kubectl -n mood get pod app-cbf7484b-z7rvg -o jsonpath='{.spec.containers[0].image}{"\n"}'

kubectl -n ingress-nginx get svc
kubectl -n ingress-nginx get endpoints ingress-nginx-controller -o wide

kubectl -n mood logs deploy/prometheus --tail=80
kubectl -n mood exec -it deploy/prometheus -- sh -c 'sed -n "1,140p" /etc/prometheus/prometheus.yml'

kubectl argo rollouts restart app -n mood
kubectl -n mood rollout restart deployment/prometheus
kubectl -n mood rollout status deployment/prometheus

Argo Rollouts:
kubectl -n mood get rollouts
kubectl argo rollouts get rollout app -n mood

Custom metrics (HPA):
kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1" | head
