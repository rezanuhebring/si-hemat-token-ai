FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY tools/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY tools/app /app

EXPOSE 9099

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9099"]
