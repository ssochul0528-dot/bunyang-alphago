FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 포트 설정을 더 확실하게 처리하기 위해 shell 형식의 CMD 사용
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
