FROM python:3.9

RUN mkdir -p /app
RUN mkdir -p /build
COPY requirements.txt /build

RUN pip install -r /build/requirements.txt

COPY . /app

WORKDIR /app
EXPOSE 5001

ENV RABBIT_USER="guest"
ENV RABBIT_PASS="guest"
ENV RABBIT_URL="rabbit:5672"
ENV RABBIT_VHOST="/"

CMD ["celery", "-A", "tasks", "worker", "-l", "INFO", "--concurrency=3"]
