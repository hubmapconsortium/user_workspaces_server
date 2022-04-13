FROM python:3.8
WORKDIR /code
ENV PYTHONUNBUFFERED=1
COPY requirements.txt /tmp/
RUN pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt
RUN apt-get update && \
    apt-get install -y sudo && \
    apt-get install -y sssd && \
    apt-get install -y virtualenv && \
    rm -rf /var/lib/apt/lists/*