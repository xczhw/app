FROM python:3.9-slim

WORKDIR /locust

RUN pip install locust

COPY locustfile.py .

EXPOSE 8089

ENTRYPOINT ["locust"]
CMD ["--host", "http://cpu-test-service.cpu-latency-test.svc.cluster.local"]
