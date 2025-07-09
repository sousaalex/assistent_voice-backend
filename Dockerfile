FROM python:3.12-slim as builder

# Instalar sed antes de usar
RUN apt-get update && apt-get install -y sed

# Substituir mirror do apt se existir o arquivo, senão ignora
RUN if [ -f /etc/apt/sources.list ]; then \
        sed -i 's/deb.debian.org/ftp.br.debian.org/' /etc/apt/sources.list ; \
    else \
        echo "Arquivo sources.list não encontrado, pulando substituição"; \
    fi

# Instalar outras dependências do sistema
RUN apt-get update && apt-get install -y --fix-missing \
        build-essential \
        cmake \
        libopenblas-dev \
        libomp-dev \
        swig && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy dependencies and application code
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . .

# Default command

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
