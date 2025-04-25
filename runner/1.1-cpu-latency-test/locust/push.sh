set -e
docker build -t locust-cpu-test:v1 .
docker tag locust-cpu-test:v1 node0:5000/locust-cpu-test:v1
docker push node0:5000/locust-cpu-test:v1
