# دليل النشر — larning.alkathiri.net

دليل تثبيت ونشر منصة المساقات على نطاق فرعي
`larning.alkathiri.net`. يغطي مسارَيْن:

- **المسار أ** — استضافة Hostinger / cPanel (مع Python App عبر Passenger)
- **المسار ب** — VPS / خادم Linux مستقل (nginx + systemd + gunicorn)

---

## ✅ متطلبات مسبقة (مشتركة)

1. سجل DNS من نوع **A** أو **CNAME** للنطاق `larning.alkathiri.net`
   يُشير إلى الخادم/الاستضافة.
2. وصول SSH أو File Manager إلى الاستضافة.
3. دعم **Python 3.10 أو أحدث**.
4. قاعدة بيانات **PostgreSQL 14+** (في المسار "أ" استخدم MySQL إن لم تتوفر
   PostgreSQL، أو SQLite للبدء السريع).
5. مساحة قرص لا تقل عن **2 GB** + ذاكرة 1 GB كحدّ أدنى (4 GB موصى).

---

## المسار أ — Hostinger (المسار الذي حددته)

### المسار النهائي للملفات
```
/home/u423175456/domains/alkathiri.net/public_html/larning
```

### ١. أنشئ النطاق الفرعي من hPanel
- ادخل **Domains → Subdomains** ثم أنشئ `larning` تحت `alkathiri.net`.
- وجّه مجلده إلى `public_html/larning` (افتراضي).

### ٢. ارفع المشروع
عبر Git (الأسهل) أو File Manager:

```bash
ssh u423175456@<host>.hostinger.com
cd ~/domains/alkathiri.net/public_html
git clone --branch claude/add-elearning-requirements-pvaxj \
    https://github.com/alkatery/MOOC.git larning
cd larning
```

### ٣. أنشئ تطبيق Python من hPanel
**hPanel → Advanced → Python App → Create Application**:

| الحقل | القيمة |
|------|------|
| Python version | 3.11 (أو الأحدث المتاح) |
| Application root | `domains/alkathiri.net/public_html/larning` |
| Application URL | `larning.alkathiri.net` |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |

بعد الحفظ ستحصل على أمر مثل:
```bash
source /home/u423175456/virtualenv/domains/alkathiri.net/public_html/larning/3.11/bin/activate
```
احفظه — سنستخدمه أدناه.

### ٤. ثبّت التبعيات
```bash
# بعد source للأمر السابق
cd ~/domains/alkathiri.net/public_html/larning
pip install --upgrade pip
pip install -e ".[deploy]"
pip install python-dotenv
```

### ٥. أنشئ قاعدة البيانات من hPanel
**hPanel → Databases → PostgreSQL Databases**:
- أنشئ قاعدة بيانات وليكن اسمها `u423175456_larning`.
- أنشئ مستخدم مع كلمة مرور قوية.
- اربط المستخدم بالقاعدة بصلاحيات كاملة.

> إذا لم تتوفر PostgreSQL في باقة Hostinger الخاصة بك، استخدم MySQL:
> غيّر سلسلة الاتصال إلى:
> `MOOC_DATABASE_URL=mysql+pymysql://USER:PASS@127.0.0.1:3306/u423175456_larning`
> وأضف `pymysql` للتثبيت: `pip install pymysql`.

### ٦. اضبط ملف `.env`
```bash
cp deploy/env.production.example .env
nano .env
```

عدّل القيم التالية:

```ini
MOOC_SECRET_KEY=$(openssl rand -hex 48)
MOOC_DATABASE_URL=postgresql+psycopg://u423175456_larning:STRONG-PASS@127.0.0.1:5432/u423175456_larning
MOOC_DATA_DIR=/home/u423175456/domains/alkathiri.net/public_html/larning/var
MOOC_CORS_ORIGINS=https://larning.alkathiri.net
MOOC_TRUSTED_HOSTS=larning.alkathiri.net
MOOC_DEBUG=false
```

ثم أكمل البنية:
```bash
chmod 600 .env
mkdir -p var/{uploads,scorm,xapi,certificates}
```

### ٧. أنشئ الجداول والبيانات التجريبية
```bash
python -m mooc --seed
```

### ٨. أعد تشغيل التطبيق
- من hPanel: **Python App → Restart**.
- أو عبر SSH: `touch tmp/restart.txt` (Passenger يعيد التحميل تلقائياً).

### ٩. فعّل HTTPS
في hPanel: **SSL → Manage** ثم فعّل شهادة Let's Encrypt المجانية على `larning.alkathiri.net` ثم **Force HTTPS**.

### ١٠. زُر الموقع
```
https://larning.alkathiri.net
```
سجّل الدخول بـ `admin@mooc.sa / Admin1234` ثم **غيّر كلمة المرور فوراً**.

> ⚠️ **المساعد الذكي على Hostinger**: ميزة Ollama المحلية تتطلب VPS — لن تعمل
> على الاستضافة المشتركة. أبقِ المتغيرات `MOOC_OLLAMA_*` معلَّقة وستتراجع
> المنصة بأمان لرسالة عربية بدلاً من الفشل.

---

## المسار ب — VPS / Linux مستقل

### الطريقة السريعة (سكربت تلقائي)
```bash
ssh root@your-vps
git clone --branch claude/add-elearning-requirements-pvaxj \
    https://github.com/alkatery/MOOC.git /tmp/mooc
cd /tmp/mooc
sudo bash deploy/install.sh
```

السكربت يقوم بكل شيء:
1. تثبيت Python و PostgreSQL و nginx و certbot.
2. استنساخ المستودع إلى `/var/www/larning.alkathiri.net`.
3. بناء venv وتثبيت الاعتماديات.
4. إنشاء مستخدم وقاعدة بيانات PostgreSQL.
5. توليد `.env` بمفتاح أمان عشوائي.
6. تثبيت `larning.service` و `larning.socket` ووحدة nginx.
7. تشغيل التطبيق وفتح جدار ufw للـ HTTP/HTTPS.

ثم أكمل يدوياً:
```bash
sudo certbot --nginx -d larning.alkathiri.net --redirect -m admin@alkathiri.net
```

### الطريقة اليدوية المختصرة
```bash
# 1) حزم
sudo apt update && sudo apt install -y python3-venv python3-dev build-essential \
    libpq-dev nginx postgresql certbot python3-certbot-nginx git

# 2) مستخدم وقاعدة
sudo -u postgres createuser --pwprompt larning
sudo -u postgres createdb -O larning larning_prod -E UTF8 --template=template0

# 3) المشروع
sudo mkdir -p /var/www/larning.alkathiri.net
sudo chown www-data:www-data /var/www/larning.alkathiri.net
sudo -u www-data git clone <repo> /var/www/larning.alkathiri.net
cd /var/www/larning.alkathiri.net
sudo -u www-data python3 -m venv .venv
sudo -u www-data .venv/bin/pip install -e ".[deploy]"

# 4) إعدادات
sudo -u www-data cp deploy/env.production.example .env
sudo -u www-data nano .env       # عدّل DATABASE_URL و SECRET_KEY
sudo chmod 600 .env

# 5) قاعدة بيانات
sudo -u www-data .venv/bin/python -m mooc --seed

# 6) systemd + nginx
sudo cp deploy/larning.service /etc/systemd/system/
sudo cp deploy/larning.socket  /etc/systemd/system/
sudo cp deploy/nginx.larning.alkathiri.net.conf /etc/nginx/sites-available/larning.alkathiri.net
sudo ln -s /etc/nginx/sites-available/larning.alkathiri.net /etc/nginx/sites-enabled/
sudo systemctl daemon-reload
sudo systemctl enable --now larning.socket larning.service
sudo nginx -t && sudo systemctl reload nginx

# 7) HTTPS
sudo certbot --nginx -d larning.alkathiri.net --redirect
```

### المساعد الذكي (اختياري — VPS فقط)
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b-instruct
sudo nano /var/www/larning.alkathiri.net/.env  # ألغِ تعليق MOOC_OLLAMA_*
sudo systemctl restart larning
```

---

## 🔧 صيانة بعد النشر

### تحديث الكود
```bash
cd /var/www/larning.alkathiri.net    # أو المسار في Hostinger
sudo -u www-data git pull
sudo -u www-data .venv/bin/pip install -e ".[deploy]"
sudo systemctl restart larning      # على VPS
# أو على Hostinger: touch tmp/restart.txt
```

### نسخ احتياطية
```bash
# قاعدة البيانات
pg_dump -U larning larning_prod | gzip > /backup/larning-$(date +%F).sql.gz

# الملفات (uploads + scorm + certs)
tar czf /backup/larning-data-$(date +%F).tar.gz \
    /var/www/larning.alkathiri.net/var/
```

اجعلها cron يومية:
```cron
0 3 * * * pg_dump -U larning larning_prod | gzip > /backup/larning-$(date +\%F).sql.gz
```

### مراقبة السجلات
```bash
# VPS:
sudo journalctl -u larning -f
sudo tail -f /var/log/nginx/larning.error.log

# Hostinger: hPanel → Python App → Logs
```

### استكشاف الأخطاء

| العَرَض | السبب المحتمل | الحل |
|------|------|------|
| 502 Bad Gateway | gunicorn متوقف | `sudo systemctl status larning` ثم `journalctl -u larning -n 100` |
| 500 Internal Error | DB غير متصلة أو SECRET_KEY ناقص | راجع `.env` ثم أعد تشغيل التطبيق |
| الصفحة بدون CSS | nginx لم يجد `/static/` | تحقق من مسار `alias` في nginx vhost |
| Passenger Error | `a2wsgi` غير مثبت | `pip install a2wsgi python-dotenv` |
| الذكاء الاصطناعي معطل | Ollama غير موجود | المنصة تتراجع برسالة عربية — هذا متوقع على Hostinger |

### تأمين بعد النشر
1. **غيّر كلمة مرور `admin@mooc.sa` فوراً.**
2. عطّل الحسابات التجريبية الأخرى (`teacher@`, `student@`, `reviewer@`)
   من `/admin/users`.
3. فعّل التدقيق على PostgreSQL وراقب `audit_log` بانتظام.
4. أنشئ منصة (Tenant) خاصة بك من `/signup` بدلاً من العمل على
   "default".
5. نسخ احتياطية يومية مؤتمتة + اختبر الاسترجاع.

---

## 🌐 تخصيص النطاقات الفرعية للمشتركين (متعدد المنصات)

المنصة تدعم تعدد المنصات (SaaS): كل مشترك يحصل على نطاق فرعي خاص.
لتفعيل هذا في الإنتاج:

1. أنشئ سجل DNS من نوع **wildcard**:
   ```
   *.alkathiri.net   A   <IP الخادم>
   ```
2. أضف وحدة nginx ثانية تُشير لكل النطاقات الفرعية:
   ```nginx
   server_name larning.alkathiri.net *.larning.alkathiri.net;
   ```
3. اطلب شهادة wildcard من Let's Encrypt:
   ```bash
   sudo certbot --nginx -d larning.alkathiri.net -d "*.larning.alkathiri.net" \
        --preferred-challenges dns
   ```
4. كل مشترك يُسجَّل من `/signup` ويصبح متاحاً على
   `https://<slug>.larning.alkathiri.net` تلقائياً (يحلّ المنصة من
   النطاق الفرعي عبر `mooc.services.tenants.resolve_tenant`).

---

## للمساعدة
- ملف `nginx.larning.alkathiri.net.conf` — قالب nginx جاهز.
- ملف `larning.service` و `larning.socket` — وحدات systemd.
- ملف `gunicorn.conf.py` — إعدادات gunicorn.
- ملف `passenger_wsgi.py` (في الجذر) — مدخل Passenger للاستضافة المشتركة.
- ملف `env.production.example` — قالب متغيرات البيئة.
- ملف `install.sh` — سكربت التثبيت التلقائي للـ VPS.
