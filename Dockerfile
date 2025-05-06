FROM python:3.9
ADD . /app
WORKDIR /app
RUN pip install requests
ENV PYTHONPATH=/app
CMD ["python", "/app/deploy_to_rancher.py"]
