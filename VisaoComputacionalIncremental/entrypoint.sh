#!/bin/bash
set -e

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-config.settings_production}

POSTGRES_HOST=${POSTGRES_HOST:-db}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-postgres}

echo "=== VisaoComputacionalIncremental Entrypoint ==="
echo "DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"
echo "FORCE_SCRIPT_NAME=$FORCE_SCRIPT_NAME"

echo "Aguardando o banco de dados em $POSTGRES_HOST:$POSTGRES_PORT..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" > /dev/null 2>&1; do
    echo "Banco de dados não disponível, aguardando..."
    sleep 2
done
echo "Banco de dados disponível!"

echo "Aplicando migrações..."
python manage.py migrate --noinput || echo "AVISO: Migração falhou, continuando..."

echo "Coletando arquivos estáticos..."
mkdir -p /app/staticfiles
if python manage.py collectstatic --noinput --clear; then
    echo "Arquivos estáticos coletados com sucesso!"
else
    echo "ERRO: collectstatic falhou! Tentando sem --clear..."
    python manage.py collectstatic --noinput || echo "ERRO CRÍTICO: collectstatic falhou completamente!"
fi

echo "Iniciando aplicação..."
exec "$@"
