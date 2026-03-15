# ArchiveSys (MVP)

مشروع أولي فعلي (MVP) لتطبيق سطح مكتب محلي للأرشفة والفهرسة والبحث الشامل داخل المجلدات.

## ما تم بناؤه الآن

- تطبيق PySide6 قابل للتشغيل مع واجهة بحث/فهرسة أساسية.
- قاعدة بيانات SQLite محلية مع FTS5 للبحث النصي.
- فهرسة أولية للمجلدات:
  - حفظ بيانات الملفات (المسار، الاسم، الامتداد، النوع، الحجم، التواريخ، بصمة SHA-256).
  - قراءة محتوى الملفات النصية الشائعة (`.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html`, `.log`, `.py`, `.ini`, `.yaml`, `.yml`).
  - إدراج الملفات غير المدعومة على الأقل ببياناتها الأساسية.
- خدمة بحث موحدة في الاسم + النص المستخرج.

## التشغيل

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

## ملاحظات مهمة

- هذا إصدار MVP تأسيسي، وليس النسخة النهائية متعددة الـ Plugins/Connectors.
- لا يزال OCR وTika وConnectors قواعد البيانات الخارجية خارج نطاق هذا الإصدار الأول.

## الهيكل

- `app/main.py` نقطة التشغيل.
- `app/ui/main_window.py` واجهة سطح المكتب.
- `app/core/indexer.py` فهرسة الملفات.
- `app/core/search_service.py` البحث.
- `app/db/database.py` تهيئة SQLite + FTS5.
- `app/db/repository.py` عمليات الحفظ والاستعلام.

