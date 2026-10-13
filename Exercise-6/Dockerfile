FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY delivery_metrics.py .
EXPOSE 8000
# -u: unbuffered output so the [DEBUG]/[INFO] lines show up in docker logs immediately
CMD ["python", "-u", "delivery_metrics.py"]
