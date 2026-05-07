# النشر التلقائي من GitHub إلى Hostinger

كل دفع إلى فرع `main` يُشغّل سير عمل
[`deploy-hostinger.yml`](../.github/workflows/deploy-hostinger.yml)
الذي:

1. يُجري الاختبارات (`pytest`).
2. ينسخ الكود عبر `rsync` فوق SSH إلى مجلد المنصة على Hostinger.
3. يُشغّل `pip install -r requirements.txt` داخل البيئة الافتراضية.
4. يُحدّث `tmp/restart.txt` ليُعيد Passenger تشغيل التطبيق تلقائياً.

---

## ١. الخطوات اليدوية مرة واحدة فقط (في hPanel)

هذه الخطوات يجب إجراؤها **قبل** أول نشر تلقائي:

### ١-أ. أنشئ Python App
**hPanel → Advanced → Python App → Create Application**

| الحقل | القيمة |
|------|------|
| Python version | 3.11 (أو أحدث متاح) |
| Application root | `domains/alkathiri.net/public_html/larning` |
| Application URL | `larning.alkathiri.net` |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |

احفظ، ثم انسخ سطر **"Enter to the virtual environment"** الذي يظهر —
ستحتاجه في المتغيّر السري `VENV_ACTIVATE`.

### ١-ب. أنشئ قاعدة بيانات
**hPanel → Databases → PostgreSQL Databases** (أو MySQL إن لم تتوفر):
- اسم القاعدة: `u423175456_larning`
- مستخدم جديد + كلمة مرور قوية + صلاحيات كاملة على القاعدة

### ١-ج. ارفع `.env` يدوياً (أول مرة فقط)
ملف `.env` لا يُرفع عبر GitHub لأسباب أمنية. ارفعه يدوياً عبر:

**hPanel → File Manager → ادخل المجلد `larning` → Upload File**

محتواه (عدّل القيم):
```ini
MOOC_SECRET_KEY=<مفتاح عشوائي ٤٨ خانة على الأقل>
MOOC_DATABASE_URL=postgresql+psycopg://USER:PASS@127.0.0.1:5432/u423175456_larning
MOOC_DATA_DIR=/home/u423175456/domains/alkathiri.net/public_html/larning/var
MOOC_CORS_ORIGINS=https://larning.alkathiri.net
MOOC_TRUSTED_HOSTS=larning.alkathiri.net
MOOC_DEBUG=false
```

> توليد مفتاح عشوائي:
> ```bash
> python3 -c "import secrets; print(secrets.token_urlsafe(48))"
> ```

### ١-د. شغّل seed أول مرة (عبر SSH)
بعد رفع `.env` وأول نشر ناجح:
```bash
ssh -p 65002 u423175456@<host>.hostinger.com
cd ~/domains/alkathiri.net/public_html/larning
source ~/virtualenv/domains/alkathiri.net/public_html/larning/3.11/bin/activate
python -m mooc --seed
```

### ١-هـ. فعّل HTTPS
**hPanel → SSL → larning.alkathiri.net → Install SSL** (Let's Encrypt مجاني) → فعّل **Force HTTPS**.

---

## ٢. أضف الأسرار إلى GitHub

افتح
**GitHub → repo `mooc` → Settings → Secrets and variables → Actions → New repository secret**
وأضف هذه الأسرار:

| اسم السر | القيمة | كيف تحصل عليها |
|------|------|------|
| `SSH_HOST` | اسم/IP خادم Hostinger | hPanel → Advanced → SSH Access |
| `SSH_USER` | `u423175456` | اسم مستخدم استضافتك |
| `SSH_PORT` | `65002` | منفذ SSH على Hostinger (افتراضي 65002) |
| `SSH_PRIVATE_KEY` | محتوى المفتاح الخاص (`-----BEGIN OPENSSH PRIVATE KEY-----...`) | راجع القسم ٣ أدناه |
| `SSH_KNOWN_HOSTS` | (اختياري) ناتج `ssh-keyscan` | إن تركتها فارغة سيُنشأ تلقائياً |
| `VENV_ACTIVATE` | (اختياري) المسار الكامل لـ `activate` الذي أعطاك hPanel | نسخه من شاشة Python App |

---

## ٣. توليد مفتاح SSH وإضافته لـ Hostinger

على جهازك المحلي (مرة واحدة):

```bash
# 1) ولّد زوج مفاتيح خاص بهذا النشر
ssh-keygen -t ed25519 -C "github-deploy@larning" -f ~/.ssh/larning_deploy -N ""

# 2) المفتاح العام — أضفه في hPanel → SSH Access → Manage SSH Keys → Add new
cat ~/.ssh/larning_deploy.pub

# 3) المفتاح الخاص — أضفه كسر GitHub باسم SSH_PRIVATE_KEY
cat ~/.ssh/larning_deploy
```

> ⚠ **لا ترفع المفتاح الخاص في الكود.** يُحفظ فقط في GitHub Secrets.

---

## ٤. ادمج فرع التطوير إلى `main`

سير العمل يُشغَّل عند الدفع إلى `main` فقط. اعتمد PR #1 ثم ادمجه:

```bash
# على جهازك (أو من واجهة GitHub: Merge pull request)
git checkout main
git pull origin main
git merge --no-ff origin/claude/add-elearning-requirements-pvaxj
git push origin main
```

أو من GitHub UI: افتح PR #1 ثم **Merge pull request**.

---

## ٥. تابع النشر في GitHub Actions

**GitHub → Actions → Deploy to Hostinger**

ستجد تشغيلاً جديداً تلقائياً. عند نجاحه:
- التطبيق يعمل على `https://larning.alkathiri.net`
- Passenger أعاد تشغيل نفسه تلقائياً

---

## ٦. التشغيل اليدوي (في حالات الطوارئ)

من **GitHub → Actions → Deploy to Hostinger → Run workflow**.

---

## ٧. التراجع (Rollback)

```bash
# على جهازك
git revert <bad-commit-sha>
git push origin main
# سير العمل يعيد النشر تلقائياً
```

---

## ٨. استكشاف الأخطاء

| الخطأ في GitHub Actions | السبب | الحل |
|------|------|------|
| `Permission denied (publickey)` | المفتاح العام لم يُضَف لـ Hostinger | راجع القسم ٣ |
| `pytest` failed | اختبار فاشل في الكود | لن يُنشر حتى يمر — أصلح الاختبار |
| `Virtualenv not found` | لم تكتمل خطوة hPanel ١-أ | أكمل Setup Python App ثم أعد التشغيل |
| `cannot connect to db` | `.env` غير موجود/قيمة DATABASE_URL خاطئة | راجع الخطوة ١-ج |

| الخطأ في الموقع | السبب | الحل |
|------|------|------|
| 403 Forbidden | المجلد فارغ — لم يُنشر شيء | شغّل سير العمل أو راجع سجلاته |
| 500 Internal Server Error | `.env` ناقص أو DB ليست مُهيّأة | راجع `journalctl` أو **Python App → Logs** في hPanel |
| Passenger Error | `passenger_wsgi.py` أو `a2wsgi` غير موجود | تأكد أن `requirements.txt` يحتوي `a2wsgi` |
