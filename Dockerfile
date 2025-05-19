FROM python:3.11

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libsndfile1 \
    libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install --no-cache-dir --retries 3 -r requirements.txt

# Manually install ultimatevocalremover
RUN git clone https://github.com/Anjok07/ultimatevocalremover.git /tmp/ultimatevocalremover \
    && cd /tmp/ultimatevocalremover \
    && git checkout master \
    && pip install . \
    && rm -rf /tmp/ultimatevocalremover

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
