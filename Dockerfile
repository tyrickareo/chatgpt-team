FROM python:slim

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt  -i https://mirrors.aliyun.com/pypi/simple/

COPY . /app

WORKDIR /app

EXPOSE 8000

CMD ["python", "main.py"]