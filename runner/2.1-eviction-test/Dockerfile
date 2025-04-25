# Dockerfile
FROM python:3.12-slim

# 安装编译psutil所需的依赖
RUN apt-get update && apt-get install -y gcc python3-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY memory_service.py .

EXPOSE 8080
CMD ["python", "memory_service.py"]