#!/bin/bash

kubectl port-forward svc/grafana -n istio-system 3000:3000 > grafana.log 2>&1 &
kubectl port-forward -n istio-system svc/prometheus 9090:9090 > prometheus.log 2>&1 &
kubectl port-forward svc/locust-master -n cpu-latency-test 8089:8089 > locust.log 2>&1 &
