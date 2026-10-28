FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
WORKDIR /app
COPY requirements-runtime.txt /app/
RUN pip install --no-cache-dir -r requirements-runtime.txt
COPY grammar.py prepare.py runtime.py evaluate_cpu.py /app/
COPY model/ /model/
USER 10001:10001
ENTRYPOINT ["python", "/app/runtime.py", "--bundle", "/model"]
