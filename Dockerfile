FROM python:3.9 AS builder
ADD . /app
WORKDIR /app
RUN pip install --target=/app requests

FROM gcr.io/distroless/python3-debian12
COPY --from=builder /app /app
WORKDIR /app
ENV PYTHONPATH=/app
CMD ["/app/deploy_to_rancher.py"]
