FROM python:3

WORKDIR /usr/src/app

COPY src/main/resources/requirements.txt ./
RUN pip install -r requirements.txt
COPY src/main/python .

CMD ["python", "./runner.py", "filter.json"]