FROM ubuntu:latest

# Atualiza e instala dependências essenciais
RUN apt-get update && apt-get install -y \
    apt-utils \
    python3-pip \
    python3-dev \
    build-essential \
    unzip \
    curl \
    tzdata \
    gnupg \
    python3-venv \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Define o fuso horário corretamente
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Adiciona a chave de assinatura e o repositório do Google Chrome
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Instala o Google Chrome
RUN apt-get update && apt-get install -y google-chrome-stable && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Cria um link simbólico para python3
RUN ln -s /usr/bin/python3 /usr/local/bin/python

# Copia o código-fonte para o container
COPY . /python
WORKDIR /python

# Cria um ambiente virtual e ativa
RUN python3 -m venv /python/venv
ENV PATH="/python/venv/bin:$PATH"

# Instala as dependências do Python dentro do ambiente virtual
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Define o comando padrão para rodar a aplicação
CMD ["python", "-u", "./app.py"]
