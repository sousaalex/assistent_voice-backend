# Etapa de build
FROM python:3.12-slim as builder

# Instalar sed e atualizar mirror do apt
RUN apt-get update && apt-get install -y sed

RUN if [ -f /etc/apt/sources.list ]; then \
        sed -i 's/deb.debian.org/ftp.br.debian.org/' /etc/apt/sources.list ; \
    else \
        echo "sources.list não encontrado"; \
    fi

# Instalar dependências do sistema para compilação + whisper
RUN apt-get update && apt-get install -y --fix-missing \
    build-essential \
    cmake \
    libopenblas-dev \
    libomp-dev \
    swig \
    ffmpeg \
    libsndfile1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# Instalar dependências Python do projeto
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Etapa de runtime
FROM python:3.12-slim

# Instalar ffmpeg no ambiente de runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar dependências da etapa anterior
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copiar o código da aplicação
COPY . .

# Comando para iniciar a API
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
