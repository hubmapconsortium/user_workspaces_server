FROM python:3.8
WORKDIR /code
ENV PYTHONUNBUFFERED=1
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt