docker exec -it istio-proxy-builder bash -c "make build BAZEL_STARTUP_ARGS='' BAZEL_BUILD_ARGS='-s --override_repository=envoy=/work/envoy' BAZEL_TARGETS=':envoy'"
docker cp istio-proxy-builder:/work/bazel-bin/envoy /mydata/istio/istio/out/envoy

/mydata/istio/istio/out/envoy -c envoy.yaml --log-level debug --concurrency 1
