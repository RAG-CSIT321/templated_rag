# base.Dockerfile = base_image
FROM python

WORKDIR /app

COPY requirements.txt .
RUN pip install --default-timeout=1000 -r requirements.txt --no-cache-dir
