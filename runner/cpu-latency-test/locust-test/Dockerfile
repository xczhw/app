FROM python:3.12-slim

WORKDIR /locust

RUN pip install locust==2.36.1

COPY locustfile.py .

EXPOSE 8089

ENTRYPOINT ["locust"]
# CMD ["--host", "http://cpu-test-service.cpu-latency-test.svc.cluster.local"]
