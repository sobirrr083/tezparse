# 📚 Quiz Format Converter Bot

Test fayllarini standart A/B/C/D + ANSWER formatiga o'tkazuvchi Telegram bot.

---

## 🏗️ Arxitektura

```
quiz-bot/
│
├── main.py                  ← Telegram bot (entry point)
├── router.py                ← Format aniqlab, converter tanlaydi
│
├── converters/
│   ├── __init__.py          ← REGISTRY ro'yxati (barcha converterlar)
│   ├── base.py              ← BaseConverter (abstract class)
│   └── quiz_converter.py    ← ?/=/+ → A/B/C/D converter
│
├── utils/
│   ├── __init__.py
│   └── file_reader.py       ← Fayl turlaridan matn chiqarish
│
├── requirements.txt
├── Procfile                 ← Railway uchun
├── railway.toml             ← Railway sozlamalari
└── .env.example             ← Muhit o'zgaruvchilari namunasi
```

### Ma'lumot oqimi

```
Foydalanuvchi fayl yuboradi
        ↓
    main.py
  (faylni yuklab oladi)
        ↓
    router.py
  (matn chiqaradi → converter qidiradi)
        ↓
  converters/REGISTRY
  (har birini can_handle() bilan tekshiradi)
        ↓
  [mos converter].convert(text)
        ↓
  ConversionResult
        ↓
  main.py → foydalanuvchiga .txt fayl yuboradi
```

---

## 🔌 Yangi Converter Qo'shish

### 1. Yangi fayl yarating: `converters/my_format.py`

```python
from .base import BaseConverter, ConversionResult

class MyFormatConverter(BaseConverter):
    NAME        = "my_format"
    DESCRIPTION = "My Format → Standard A/B/C/D"
    SUPPORTED_EXTENSIONS = {".txt", ".docx"}
    PRIORITY    = 20  # katta = oldin sinasin

    @classmethod
    def can_handle(cls, text: str) -> bool:
        # Faqat shu converter ishlashi kerak bo'lgan matndagi belgilarni tekshiring
        return "MY_MARKER" in text and text.count("CORRECT:") >= 1

    @classmethod
    def convert(cls, text: str) -> ConversionResult:
        # ... parsing logikasi ...
        return ConversionResult(
            success=True,
            output_text="1. Savol\n    A. ...\n    ANSWER: A\n",
            converted_count=1,
            skipped_count=0,
            errors=[],
        )
```

### 2. `converters/__init__.py` ga qo'shing

```python
from .my_format import MyFormatConverter

REGISTRY = [
    QuizConverter,
    MyFormatConverter,   # ← shu qatorni qo'shing
]
```

**Boshqa hech narsani o'zgartirmang** — router va bot avtomatik sezadi.

---

## 🚀 Railway.com ga Deploy Qilish

### 1. GitHub repoga yuklang

```bash
cd quiz-bot
git init
git add .
git commit -m "init"
gh repo create quiz-bot --public --push
```

### 2. Railway'da yangi loyiha

1. [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
2. Reponi tanlang
3. **Variables** bo'limiga o'ting:
   ```
   BOT_TOKEN = <@BotFather dan olingan token>
   ```
4. Deploy tugmasi — bot 1-2 daqiqada ishga tushadi

### 3. Bot turini tekshirish

Railway **Worker** tipida ishlatadi (HTTP server emas).  
`Procfile` da `worker:` prefiksi shu uchun.

---

## 🛠️ Lokal Ishga Tushirish

```bash
# 1. Muhit
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Kutubxonalar
pip install -r requirements.txt

# 3. Token
cp .env.example .env
# .env ni oching va BOT_TOKEN ni to'ldiring

# 4. Ishga tushirish
python main.py
```

---

## 📋 Qo'llab-quvvatlanadigan Fayl Formatlari

| Format | Kutubxona       | Izoh                          |
|--------|-----------------|-------------------------------|
| .txt   | built-in        | UTF-8, cp1251, latin-1        |
| .docx  | python-docx     | Paragraflar + jadvallar       |
| .pdf   | pdfplumber      | PyPDF2 zaxira sifatida        |
| .xlsx  | openpyxl        | Barcha varaqlar               |
| .xls   | xlrd            | Eski Excel format             |
| .doc   | antiword/textract | Railway'da antiword kerak   |

---

## ⚙️ Konfiguratsiya

| O'zgaruvchi   | Majburiy | Tavsif                    |
|---------------|----------|---------------------------|
| `BOT_TOKEN`   | ✅       | Telegram bot tokeni       |

---

## 🔮 Kelajakdagi Rejalar

- `converters/antest_converter.py` — AnTest format
- `converters/numbered_quiz.py` — 1/2/3/4 raqamli variant format  
- `converters/excel_table.py` — Excel jadval formatdagi testlar
- Admin panel: statistika, fayl tarixi
- Guruhlar uchun qo'llab-quvvatlash
