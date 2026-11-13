FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

COPY alembic.ini ./
COPY alembic ./alembic

# As imagens (assets/, ~1 GB) nao entram na imagem: ficam fora do Git e sao
# montadas como volume somente leitura em /app/assets (veja os arquivos compose).
RUN mkdir -p /app/assets

CMD ["asterion-api"]
