FROM python:3.7
WORKDIR /code
ENV PYTHONUNBUFFERED=1
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt
CMD python3 manage.py migrate