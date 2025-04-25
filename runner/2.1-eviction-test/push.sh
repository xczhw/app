set -e
docker build -t node0:5000/memory-service:v1 .
docker push node0:5000/memory-service:v1