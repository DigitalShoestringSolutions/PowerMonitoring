FROM python:3.11

WORKDIR /app

COPY ./code/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./code/ /app/

CMD ["python","main.py"]
