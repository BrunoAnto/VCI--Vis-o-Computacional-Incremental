FROM python:3.11-slim-bullseye

ARG DEBIAN_FRONTEND=noninteractive

ENV TZ=America/Sao_Paulo \
    LANG=pt_BR.utf8 \
    LANGUAGE=pt_BR:pt \
    LC_ALL=pt_BR.UTF-8 \
    PYTHONENCODING=utf-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get update && apt-get install -y \
       locales \
       python3-dev \
       python3-setuptools \
       python3-pip \
       build-essential \
       ca-certificates \
       gcc \
       libpq-dev \
       curl \
       postgresql-client \
    && localedef -i pt_BR -c -f UTF-8 -A /usr/share/locale/locale.alias pt_BR.UTF-8 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=config.settings_production

RUN mkdir -p /app/staticfiles /app/app/keys

RUN python manage.py collectstatic --noinput --clear 2>&1 || \
    echo "AVISO: collectstatic falhou no build (será executado novamente no entrypoint)"

EXPOSE 8060

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8060", "--timeout", "300", "--keep-alive", "60", "--graceful-timeout", "300", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-", "config.wsgi:application"]
