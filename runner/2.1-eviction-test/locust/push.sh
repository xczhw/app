set -e
docker build -t node0:5000/locust-memory-test:v1 .
docker push node0:5000/locust-memory-test:v1