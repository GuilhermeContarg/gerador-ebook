# Use a imagem base oficial do Python
FROM python:3.11-slim

# Instalar dependências do sistema operacional necessárias para o weasyprint
# O weasyprint requer pango, cairo e gdk-pixbuf
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libcairo2 \
    libffi-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Definir o diretório de trabalho
WORKDIR /app

# Copiar o arquivo de requisitos e instalar as dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY app.py .

# Expor a porta que o Gunicorn irá usar
EXPOSE 8080

# Comando para rodar a aplicação com Gunicorn
# O Render usará a variável de ambiente PORT, mas 8080 é um bom padrão para o Docker
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
