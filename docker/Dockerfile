FROM python:3.10-buster
WORKDIR /code
ENV PYTHONUNBUFFERED=1
COPY requirements/requirements.txt /tmp/
RUN apt-get update && \
    apt-get install -y sudo && \
    apt-get install -y sssd && \
    apt-get install -y virtualenv && \
    apt-get install -y postgresql-client && \
    apt-get install -y libsasl2-dev && \
    apt-get install -y libldap2-dev && \
    rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt
