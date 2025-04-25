docker build -t cpu-test-service:v1 .
docker tag cpu-test-service:v1 node0:5000/cpu-test-service:v1
docker push node0:5000/cpu-test-service:v1