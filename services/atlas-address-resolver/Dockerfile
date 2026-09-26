FROM python:3.12-slim
WORKDIR /app
COPY app.py /app/app.py
COPY representation_provider.py /app/representation_provider.py
ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/app.py"]
