FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway에서 제공하는 $PORT 환경 변수를 사용하기 위해 shell형식의 CMD를 사용합니다.
# uvicorn 실행 시 파일 확장자(.py)가 아닌 모듈 이름(main)을 사용해야 합니다.
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
