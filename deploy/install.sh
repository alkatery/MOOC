#!/usr/bin/env bash
# Bootstrap a fresh Ubuntu/Debian VPS for the MOOC platform on
# larning.alkathiri.net. Idempotent — safe to re-run.
#
# Usage (as root or via sudo):
#   sudo bash deploy/install.sh
#
# What it does:
#   1. Installs OS packages (python, postgres, nginx, certbot, ollama-deps)
#   2. Creates /var/www/larning.alkathiri.net with the right ownership
#   3. Clones (or pulls) the repo into that directory
#   4. Builds a venv and installs the project in production mode
#   5. Creates the postgres role + database (prompts for a password)
#   6. Installs systemd units and the nginx vhost
#   7. Reloads systemd + nginx
#   8. Tells you the next manual steps (.env edit, certbot, ollama pull)

set -euo pipefail

DOMAIN="larning.alkathiri.net"
# Default: VPS layout. For Hostinger/cPanel set:
#   APP_DIR=/home/u423175456/domains/alkathiri.net/public_html/larning sudo bash install.sh
APP_DIR="${APP_DIR:-/var/www/${DOMAIN}}"
APP_USER="${APP_USER:-www-data}"
APP_GROUP="${APP_GROUP:-www-data}"
REPO_URL="${REPO_URL:-https://github.com/alkatery/MOOC.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
PG_USER="larning"
PG_DB="larning_prod"

color() { printf "\e[1;36m▸ %s\e[0m\n" "$*"; }
ok()    { printf "\e[1;32m✓ %s\e[0m\n" "$*"; }
warn()  { printf "\e[1;33m! %s\e[0m\n" "$*"; }

if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo: sudo bash deploy/install.sh"
  exit 1
fi

# ---------------------------------------------------------------------------
# 1) System packages
# ---------------------------------------------------------------------------
color "تحديث النظام وتثبيت الحزم الأساسية..."
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip python3-dev \
    build-essential libpq-dev \
    git curl ca-certificates \
    nginx \
    postgresql postgresql-contrib \
    certbot python3-certbot-nginx \
    ufw locales

# Arabic locale (used by PostgreSQL collations and CLI)
locale-gen ar_SA.UTF-8 || true
ok "الحزم جاهزة"

# ---------------------------------------------------------------------------
# 2) Application directory + repo
# ---------------------------------------------------------------------------
color "تجهيز ${APP_DIR}..."
mkdir -p "${APP_DIR}"
chown -R ${APP_USER}:${APP_GROUP} "${APP_DIR}"
mkdir -p /var/www/letsencrypt
chown -R ${APP_USER}:${APP_GROUP} /var/www/letsencrypt

if [[ -d "${APP_DIR}/.git" ]]; then
  color "تحديث المستودع..."
  sudo -u "${APP_USER}" git -C "${APP_DIR}" fetch --depth=1 origin "${REPO_BRANCH}"
  sudo -u "${APP_USER}" git -C "${APP_DIR}" reset --hard "origin/${REPO_BRANCH}"
else
  color "استنساخ المستودع من ${REPO_URL}..."
  sudo -u "${APP_USER}" git clone --depth=1 -b "${REPO_BRANCH}" "${REPO_URL}" "${APP_DIR}"
fi

mkdir -p "${APP_DIR}/var/uploads" "${APP_DIR}/var/scorm" "${APP_DIR}/var/xapi" "${APP_DIR}/var/certificates"
chown -R ${APP_USER}:${APP_GROUP} "${APP_DIR}/var"
ok "المستودع جاهز"

# ---------------------------------------------------------------------------
# 3) Virtualenv + dependencies
# ---------------------------------------------------------------------------
color "بناء بيئة Python الافتراضية وتثبيت الاعتماديات..."
sudo -u "${APP_USER}" python3 -m venv "${APP_DIR}/.venv"
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install --upgrade pip wheel
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install -e "${APP_DIR}[deploy]"
ok "Python جاهز"

# ---------------------------------------------------------------------------
# 4) PostgreSQL role + database
# ---------------------------------------------------------------------------
color "إعداد PostgreSQL..."
systemctl enable --now postgresql

# Role
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}'" | grep -q 1; then
  read -srp "كلمة مرور قاعدة البيانات الجديدة لمستخدم ${PG_USER}: " DB_PASS; echo
  sudo -u postgres psql -c "CREATE ROLE ${PG_USER} LOGIN PASSWORD '${DB_PASS}';"
  ok "تم إنشاء مستخدم قاعدة البيانات"
else
  warn "مستخدم ${PG_USER} موجود مسبقاً — لم تُغيَّر كلمة المرور"
  DB_PASS=""
fi

# Database
if ! sudo -u postgres psql -lqt | cut -d '|' -f1 | grep -qw "${PG_DB}"; then
  sudo -u postgres createdb -O "${PG_USER}" "${PG_DB}" -E UTF8 --template=template0
  ok "تم إنشاء قاعدة البيانات ${PG_DB}"
else
  warn "قاعدة البيانات ${PG_DB} موجودة"
fi

# ---------------------------------------------------------------------------
# 5) Environment file
# ---------------------------------------------------------------------------
color "إعداد ملف .env..."
if [[ ! -f "${APP_DIR}/.env" ]]; then
  install -m 0600 -o www-data -g www-data "${APP_DIR}/deploy/env.production.example" "${APP_DIR}/.env"
  SECRET=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
  sed -i "s|REPLACE-ME-WITH-A-LONG-RANDOM-STRING-AT-LEAST-48-BYTES|${SECRET}|" "${APP_DIR}/.env"
  if [[ -n "${DB_PASS:-}" ]]; then
    sed -i "s|STRONG-DB-PASSWORD|${DB_PASS}|" "${APP_DIR}/.env"
  fi
  ok ".env جاهز — راجع القيم بـ: sudo -u "${APP_USER}" ${EDITOR:-nano} ${APP_DIR}/.env"
else
  warn ".env موجود — لم يُلمس"
fi

# ---------------------------------------------------------------------------
# 6) systemd units + nginx vhost
# ---------------------------------------------------------------------------
color "تثبيت وحدات systemd ونغ‌نكس..."
install -m 0644 "${APP_DIR}/deploy/larning.service" /etc/systemd/system/larning.service
install -m 0644 "${APP_DIR}/deploy/larning.socket"  /etc/systemd/system/larning.socket
install -m 0644 "${APP_DIR}/deploy/nginx.larning.alkathiri.net.conf" \
  "/etc/nginx/sites-available/${DOMAIN}"
ln -sf "/etc/nginx/sites-available/${DOMAIN}" "/etc/nginx/sites-enabled/${DOMAIN}"
[[ -L /etc/nginx/sites-enabled/default ]] && rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl enable --now larning.socket
ok "systemd جاهز"

# ---------------------------------------------------------------------------
# 7) Initial DB schema + seed
# ---------------------------------------------------------------------------
color "إنشاء جداول قاعدة البيانات وبيانات تجريبية أولية..."
sudo -u "${APP_USER}" --preserve-env=PATH bash -c "
  cd ${APP_DIR}
  set -a
  source .env
  set +a
  ${APP_DIR}/.venv/bin/python -m mooc --seed
" || warn "تعذّر تنفيذ seed تلقائياً — نفّذه يدوياً بعد تعديل .env"

# ---------------------------------------------------------------------------
# 8) Start the app + nginx
# ---------------------------------------------------------------------------
color "إعادة تحميل nginx وتشغيل التطبيق..."
nginx -t && systemctl reload nginx
systemctl enable --now larning.service
ok "التطبيق يعمل: systemctl status larning"

# ---------------------------------------------------------------------------
# 9) Firewall
# ---------------------------------------------------------------------------
if command -v ufw >/dev/null 2>&1; then
  color "ضبط الجدار الناري..."
  ufw allow OpenSSH || true
  ufw allow 'Nginx Full' || true
  yes | ufw enable || true
fi

cat <<EOF

────────────────────────────────────────────────────────────────────────
✅ تم التثبيت بنجاح.
────────────────────────────────────────────────────────────────────────
الخطوات اليدوية المتبقية:

1) راجع متغيرات البيئة:
     sudo -u "${APP_USER}" ${EDITOR:-nano} ${APP_DIR}/.env

2) فعّل HTTPS عبر Let's Encrypt:
     sudo certbot --nginx -d ${DOMAIN} --redirect --agree-tos -m admin@alkathiri.net

3) (اختياري) ثبّت Ollama لتفعيل المساعد الذكي:
     curl -fsSL https://ollama.com/install.sh | sh
     ollama pull llama3.1:8b-instruct
     ثم أزل التعليق عن MOOC_OLLAMA_URL و MOOC_OLLAMA_MODEL في .env
     sudo systemctl restart larning

4) راقب السجلات:
     sudo journalctl -u larning -f
     sudo tail -f /var/log/nginx/larning.error.log

5) سجّل الدخول:
     https://${DOMAIN}/login
     admin@mooc.sa / Admin1234   ← غيّر كلمة المرور فوراً!

────────────────────────────────────────────────────────────────────────
EOF
