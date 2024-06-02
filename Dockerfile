FROM python:3.9

RUN mkdir -p /app
RUN mkdir -p /build
COPY requirements.txt /build

RUN pip install -r /build/requirements.txt

COPY . /app

WORKDIR /app
EXPOSE 5000

CMD ["flask", "--app", "main", "run", "--host=0.0.0.0", "--debug"]
