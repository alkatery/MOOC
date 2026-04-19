# منصة المساقات المفتوحة (MOOC Platform)

نظام تعليمي مفتوح المصدر مبني على مبدأ **MOOC** ومتوافق مع
[معايير التميز في التعليم الإلكتروني](https://nelc.gov.sa/ar/regulations-and-standards/elearning-excellence-standards)
الصادرة عن **المركز الوطني للتعليم الإلكتروني (NELC)** في المملكة العربية السعودية.

## المكونات

```
src/mooc/
├── nelc/              ← تصنيف NELC الكامل (8 مجالات، 43 محور، 339 معيار)
├── models.py          ← نماذج SQLAlchemy (17 جدول)
├── schemas.py         ← مخططات Pydantic
├── security.py        ← التجزئة، JWT، RBAC
├── config.py          ← إعدادات NELC والإقامة
├── database.py        ← محرك قاعدة البيانات
├── services/          ← xAPI, SCORM, grading, certificates, review, audit
├── routers/           ← API (JSON) + بوابات HTML
├── templates/         ← قوالب Jinja2 عربية RTL
├── static/            ← CSS متوافق مع WCAG 2.1 AA
└── seed.py            ← بيانات تجريبية
```

## التشغيل السريع

```bash
pip install -e .
python -m mooc --seed --reload
# ثم افتح http://127.0.0.1:8000
```

## الأدوار المدعومة

| الدور | الصفحة | الصلاحيات |
|-------|---------|-----------|
| طالب | `/student` | التسجيل في المقررات، متابعة الدروس، حل الاختبارات والواجبات، استلام الشهادات |
| معلم | `/teacher` | إنشاء مقررات، وحدات، دروس، اختبارات، واجبات، تقييم تسليمات الطلاب |
| مراجع جودة | `/admin/reviews` | مراجعة المقررات وفق معايير NELC |
| مشرف | `/admin` | إدارة المستخدمين، المقررات، السياسات، التقارير، سجل التدقيق |

## أنواع الدروس المدعومة

| النوع | الوصف |
|--------|--------|
| `video` | فيديو مع ترجمة نصية وترجمة إشارية اختيارية |
| `text` | درس نصي بتنسيق بسيط |
| `pdf` | ملفات PDF مدمجة |
| `scorm` | حزم SCORM 1.2/2004 (استيراد تلقائي للمانيفست) |
| `interactive` | تدريبات تفاعلية (كود، أسئلة داخل الدرس) |
| `external` | مصدر خارجي |
| `live` | جلسة مباشرة (رابط Zoom/Teams) |

## أنواع الأسئلة

- **اختيار من متعدد** (Multiple Choice)
- **متعدد الإجابات** (Multiple Answer)
- **صح أو خطأ** (True/False)
- **إجابة قصيرة** (Short Answer)
- **مقالية** (Essay — تصحيح يدوي)

## مسار اعتماد المقرر

```
مسودة (Draft)
   ↓
قيد المراجعة (Under Review)   ← المعلم يضغط "إرسال للمراجعة"
   ↓
اعتماد / يحتاج تعديلات / رفض   ← المراجع يقيّم وفق {339} معياراً
   ↓
منشور (Published)              ← الإدارة تضغط "نشر"
   ↓
مؤرشف (Archived)
```

## امتثال NELC

المنصة تُطبّق المواصفات الرسمية من وثيقة
*Rubrics of Criteria for Excellence — K-12, v2.0 (December 2023)*
مرخصة تحت **CC BY-NC-SA 4.0**.

**المجالات الثمانية:**

| الرمز | المجال | عدد المعايير |
|-------|---------|----------------|
| K.1 | المؤسسة (Institution) | ~40 |
| K.2 | إدارة البرنامج (Program Administration) | ~55 |
| K.3 | الإدارة الإلكترونية (Online Admin) | ~49 |
| K.4 | تصميم المقرر الإلكتروني (Online Course Design) | ~53 |
| K.5 | التعليم الإلكتروني (Online Teaching) | ~48 |
| K.6 | التعلم المدمج (Blended Learning) | ~43 |
| K.7 | إنتاج الفيديو (Video Production) | ~33 |
| K.8 | الفصل الافتراضي (Virtual Classroom) | ~20 |

**سلم التقييم:**
- `1 — ناشئ (Emerging)`
- `2 — متحقق (Accomplished)`
- `3 — مثالي (Exemplary)`

## الإتاحة (Accessibility)

- واجهة عربية RTL كاملة
- دعم قارئ الشاشة عبر `aria-*`
- Skip link للتنقل السريع
- التزام WCAG 2.1 AA (تباين ألوان ≥ 4.5:1)
- دعم `prefers-contrast: more` و `prefers-reduced-motion`
- دعم الترجمة المكتوبة والترجمة الإشارية للفيديو

## قابلية التشغيل البيني

- **xAPI / Tin Can**: يتم تسجيل كل تفاعل (`registered`, `launched`, `experienced`, `completed`, `attempted`, `scored`, `passed`, `failed`, `earned`) في جدول `xapi_statements`
- **SCORM**: استيراد حزم ZIP، قراءة `imsmanifest.xml`، حماية من zip-slip
- **JSON API**: كل الموارد متاحة عبر REST لغرض التكامل

## البيانات والخصوصية

- تخزين محلي للبيانات في منطقة `sa-central-1` افتراضياً
- سجل تدقيق (`audit_log`) يُحتفظ به لمدة قابلة للتعديل (افتراضي: سنتان)
- موافقة صريحة على سياسة الخصوصية قبل التسجيل
- تجزئة كلمات المرور بـ `pbkdf2_sha256` (260,000 iteration)
- جلسات مرمزة HMAC-SHA256 (HS256)

## البيانات التجريبية

بعد التشغيل مع `--seed`:

| الدور | البريد الإلكتروني | كلمة المرور |
|-------|-------------------|-------------|
| admin | `admin@mooc.sa` | `Admin1234` |
| reviewer | `reviewer@mooc.sa` | `Review1234` |
| instructor | `teacher@mooc.sa` | `Teach1234` |
| student | `student@mooc.sa` | `Study1234` |

## الاختبارات

```bash
pytest tests/mooc_platform -q
```

يغطي:
- صحة تصنيف NELC
- تجزئة كلمات المرور و JWT
- حساب درجات الأسئلة
- منطق مراجعة الجودة
- تدفقات HTTP الرئيسية (تسجيل، دخول، healthz، صفحات عامة)

## المصادر

- [المركز الوطني للتعليم الإلكتروني — NELC](https://nelc.gov.sa/)
- [معايير التميز في التعليم الإلكتروني](https://nelc.gov.sa/ar/regulations-and-standards/elearning-excellence-standards)
- `Rubrics of Criteria for Excellence — K-12, Version 2.0 (Dec 2023)` — CC BY-NC-SA 4.0
