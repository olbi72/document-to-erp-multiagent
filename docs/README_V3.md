Нижче — детальний `README` для поточного стану проєкту. Його можна зберегти як, наприклад:

```text
docs/README_CURRENT_STATE.md
```

або тимчасово як:

```text
README_VISION_PARSING_EXPERIMENTS.md
```

---

# Document to ERP Multiagent Parser

## 1. Суть проєкту

Проєкт призначений для автоматичного парсингу бухгалтерських документів і підготовки структурованих даних для подальшої передачі в ERP-систему.

Основна задача системи:

```text
вхідний документ
→ парсинг
→ визначення контрагента
→ визначення господарського або негосподарського характеру операції
→ валідація
→ передача далі або HITL-перевірка
```

На поточному етапі система працювала переважно з актами виконаних робіт, але зараз проєкт розширюється для обробки накладних, тобто документів із товарними позиціями, ПДВ, знижками та підсумковими сумами.

---

# 2. Поточна архітектура MVP

Поточний pipeline має приблизно таку логіку:

```text
data/inbox
→ ParserAgent
→ DoclingClient
→ ExtractionAgent
→ BuhgalterAgent
→ ValidatorAgent
→ data/review_pending або validated output
```

## 2.1. Основні модулі

### `ParserAgent`

Відповідає за первинну обробку документа.

Його поточна логіка:

```text
1. отримує шлях до файлу
2. визначає тип файлу через FileDetector
3. передає файл у DoclingClient
4. отримує текст документа
5. передає текст в ExtractionAgent
6. формує DocumentCase
```

---

### `FileDetector`

Визначає тип документа за розширенням файлу.

Поточні або тестові типи:

```text
.pdf  → pdf
.png  → image
.jpg  → image
.jpeg → image
.html → html, тимчасово для тестів
```

HTML було додано тільки для експерименту з чистою структурованою таблицею.

---

### `DoclingClient`

Відправляє файл у локальний Docling Serve.

Базова адреса:

```text
http://localhost:5002
```

Endpoint:

```text
/v1/convert/file
```

Основні параметри, які тестувалися:

```python
data = {
    "to_formats": "md",
    "do_ocr": "true",
    "force_ocr": "false",
    "ocr_engine": "tesseract",
    "ocr_lang": ["ukr", "eng"],
    "do_table_structure": "true",
    "table_mode": "accurate",
    "table_cell_matching": "false",
    "pipeline": "standard",
}
```

Також тестувалися:

```text
easyocr
json output
images_scale = 4
table_cell_matching = true / false
```

Висновок: для PNG/JPEG-таблиць Docling у поточній конфігурації часто не створює структуровану таблицю, навіть якщо `do_table_structure = true`.

---

### `ExtractionAgent`

Отримує текст або markdown від Docling і через локальну LLM витягує JSON.

Поточна модель у `.env`:

```text
PARSER_MODEL=gemma3:4b
```

Раніше `ExtractionAgent` намагався одразу витягувати складну структуру:

```text
document fields
items
amount_model
discount_model
vat_model
confidence
reason
```

Але після тестів було прийнято архітектурне рішення:
`ExtractionAgent` має витягувати тільки первинні дані з документа, без складних бухгалтерських висновків.

Тобто він має бути не “аналітиком”, а “екстрактором фактів”.

---

### `BuhgalterAgent`

Виконує бухгалтерську логіку.

Поточні функції:

```text
1. пошук контрагента в базі
2. звірка за ІПН / ЄДРПОУ / назвою
3. визначення господарського або негосподарського характеру операції
4. для документів без ПДВ може використовувати LLM-класифікацію
```

Для актів логіка вже працює.

Для накладних поточна логіка ще не є фінальною, бо треба переходити до аналізу кожної товарної позиції окремо.

---

### `ValidatorAgent`

Перевіряє результат після ParserAgent і BuhgalterAgent.

Поточна логіка:

```text
1. перевіряє наявність обов’язкових полів
2. перевіряє, чи потрібна HITL-перевірка
3. формує final_status
4. формує hitl_status
```

Приклад:

```text
final_status: validated
hitl_status: not_required
```

або:

```text
final_status: review_required
hitl_status: pending
```

---

# 3. Поточні директорії

Основні директорії:

```text
data/inbox
```

Вхідні документи.

```text
data/review_pending
```

Документи, які потребують перевірки людиною.

```text
data/approved
```

Документи, які підтверджені.

```text
data/rejected
```

Документи, які відхилені.

```text
data/reference
```

Довідники, наприклад база контрагентів і довідник негосподарських операцій.

```text
data/debug
```

Тестові файли, crop-и, результати експериментів.

---

# 4. Поточний `.env`

Поточні ключові налаштування:

```env
OLLAMA_BASE_URL=http://localhost:11434
PARSER_MODEL=gemma3:4b
BUHGALTER_MODEL=gemma3:4b

DOCLING_BASE_URL=http://localhost:5002

INPUT_DIR=data/inbox
REVIEW_PENDING_DIR=data/review_pending
APPROVED_DIR=data/approved
REJECTED_DIR=data/rejected

CONTRAGENTS_FILE=data/reference/contragents.xls

CLIENT_NAME=
CLIENT_EDRPOU=
CLIENT_IPN=

NON_BUSINESS_OPERATIONS_FILE=data/reference/non_business_operations_mvp.xlsx

LANGFUSE_SECRET_KEY=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_ENABLED=true
```

---

# 5. Що вже було зроблено

## 5.1. Робота з актами

Система вже вміє обробляти акти виконаних робіт.

Приклад успішного extraction для акта:

```json
{
  "document_type": "act",
  "document_kind": "act",
  "document_number": "OY-0004521",
  "document_date": "31.12.2025",
  "customer_name": "ТОВ \"СЕ БОРДНЕТЦЕ-УКРАЇНА\"",
  "supplier_name": "ТОВ \"Хмельницьке таксі\"",
  "supplier_edrpou": "12345678",
  "supplier_ipn": "123456789012",
  "total_amount": "1 500,00",
  "vat_amount": "0.00",
  "currency": "грн",
  "description": "Послуги таксі та перевезення працівників"
}
```

Було реалізовано логіку:

```text
якщо документ без ПДВ,
то визначення господарського або негосподарського характеру може виконуватися через LLM-рішення на підставі prompt.
```

---

## 5.2. Додана підтримка `document_kind`

Було додано ідею розділення:

```text
document_kind = act
document_kind = invoice
document_kind = unknown
```

Це потрібно, щоб у майбутньому різні типи документів оброблялися різною логікою.

---

## 5.3. Запропоновано єдину структуру для актів і накладних

Було прийнято концептуальне рішення:

```text
акт = документ із однією або кількома сервісними позиціями
накладна = документ із кількома товарними позиціями
```

Тому і акти, і накладні можуть мати єдину структуру:

```json
{
  "document_kind": "act | invoice",
  "items": []
}
```

Це дає можливість у майбутньому однаково обробляти:

```text
послуги
роботи
товари
матеріали
```

---

## 5.4. Перероблено концепт ExtractionAgent

Спочатку prompt ExtractionAgent був ускладнений і мав витягувати:

```text
amount_model
discount_model
vat_scenario
vat_calculation_level
vat_inclusion
confidence
reason
```

Але локальна модель `gemma3:4b` почала плутатись, зокрема:

```text
vat_scenario = without_vat
vat_calculation_level = line_level
discount_base = net при discount_present = false
```

Тому було вирішено розділити роботу:

```text
ExtractionAgent
→ витягує тільки первинні факти

AmountAnalyzer
→ окремо аналізує ПДВ, знижки, нетто, брутто, арифметику
```

---

## 5.5. Створено спрощений extraction prompt

Було створено prompt, який повертає структуру:

```json
{
  "document_type": null,
  "document_kind": "act | invoice | unknown",
  "document_number": null,
  "document_date": null,
  "customer_name": null,
  "supplier_name": null,
  "supplier_edrpou": null,
  "supplier_ipn": null,
  "total_amount": null,
  "vat_amount": null,
  "currency": null,
  "description": null,
  "document_totals_raw": {
    "total_without_vat": null,
    "discount_amount": null,
    "total_after_discount_without_vat": null,
    "vat_amount": null,
    "total_with_vat": null,
    "total_including_vat": null,
    "vat_included_amount": null
  },
  "items": [
    {
      "line_number": 1,
      "item_type": "service | goods | unknown",
      "item_name": null,
      "quantity": null,
      "unit": null,
      "unit_price": null,
      "line_amount": null,
      "line_total_without_vat": null,
      "line_vat_amount": null,
      "line_total_with_vat": null,
      "line_discount_amount": null
    }
  ],
  "raw_amount_labels": []
}
```

Головна ідея:

```text
не робити висновків
не рахувати ПДВ
не вигадувати нулі
не копіювати документні суми в рядки
```

---

## 5.6. Виправлено агресивну логіку `without VAT`

У `ExtractionAgent` була функція `_normalize_without_vat`, яка занадто агресивно визначала документ як “без ПДВ”, якщо бачила фразу `без ПДВ`.

Це було неправильно, бо в накладних може бути:

```text
Ціна без ПДВ
Сума без ПДВ
ПДВ 20%
Сума з ПДВ
```

Тобто наявність фрази `без ПДВ` не означає, що весь документ без ПДВ.

Було додано логіку:

```text
якщо є позитивний ПДВ або маркери "ПДВ 20%", "Сума з ПДВ", "В т.ч. ПДВ",
то не ставити vat_status = without_vat
```

---

# 6. Експерименти з Docling і накладними

## 6.1. Тестова накладна PNG

Було створено тестову накладну від постачальника:

```text
1001 Дрібниця, ТзОВ
ІПН: 191714913052
ЄДРПОУ: 19171498
```

Покупець:

```text
ТОВ "СЕ Борднетце - Україна"
```

Позиції:

```text
1. Фарба біла — 10 шт — 200 грн — 2 000 грн без ПДВ
2. Горщики для вазонів — 5 шт — 100 грн — 500 грн без ПДВ
```

Підсумки:

```text
Загальна сума без ПДВ: 2 500 грн
Знижка: 300 грн
Сума без ПДВ з урахуванням знижки: 2 200 грн
ПДВ 20%: 440 грн
Сума з ПДВ: 2 640 грн
```

---

## 6.2. Проблема Docling з PNG-таблицями

Docling погано витягнув таблицю з PNG.

Приклад markdown:

```text
Фарбабіла

200,00

2

000,00
```

Друга позиція:

```text
Горщики для вазонів
```

часто взагалі не розпізнавалася.

Docling повертав:

```text
tables count: 0
```

Тобто не створював table object у JSON.

---

## 6.3. Тест Docling JSON з bbox

Було отримано Docling JSON, де:

```text
tables = []
texts = 47
```

Хоча таблиця не була розпізнана як таблиця, у JSON були корисні дані:

```text
text
bbox
page_no
label
```

Це дозволило зробити експериментальний layout parser.

---

## 6.4. Створено тестовий layout parser

Файл:

```text
app/debug/test_docling_layout_parser.py
```

Його логіка:

```text
1. отримати Docling JSON
2. взяти всі texts
3. витягнути bbox
4. згрупувати блоки в рядки по Y-координаті
5. відсортувати блоки в рядку по X-координаті
6. розбити документ на секції
```

Було отримано секції:

```text
HEADER
COUNTERPARTIES
ITEM_ROWS
TOTALS
FOOTER
```

Результат був кращий за markdown:

```text
HEADER:
ПРИХІДНА НАКЛАДНА
Ме ПН-000127 від 08.05.2026

COUNTERPARTIES:
Постачальник: 1001 Дрібниця, ТзОВ
ІПН: 191714913052
ЄДРПОУ: 19171498

ITEM_ROWS:
1 | Фарбабіла | 200,00 | 2 | 000,00

TOTALS:
Загальна сума без ПДВ: 2 500,00 грн
Знижка: 300,00 грн
Сума без ПДВ з урахуванням знижки: 2 200,00 грн
ПДВ 2095: 440,00 грн
Сума з ПДВ: 2 640,00 грн
```

Висновок:

```text
Docling JSON з bbox корисний,
але не вирішує повністю проблему товарної таблиці.
```

---

## 6.5. Експерименти з crop

Було протестовано ідею:

```text
повний документ
→ bbox
→ визначення зони таблиці
→ crop таблиці
→ повторна відправка crop у Docling
```

Було створено crop-файли:

```text
data/debug/crops/1000dribnyts_items.png
data/debug/crops/1000dribnyts_totals.png
```

Висновок:

```text
crop не дав стабільного покращення.
Docling все одно не витягнув таблицю нормально.
```

---

## 6.6. Тест із технічно чистою PNG-накладною

Було створено чисту PNG-накладну кодом через Pillow:

```text
app/debug/create_clean_invoice_image.py
```

Файл:

```text
data/inbox/clean_invoice_test.png
```

Навіть на чистій PNG Docling повернув порожню markdown-таблицю:

```markdown
|    |    |    |    |    |    |
|----|----|----|----|----|----|
|    |    |    |    |    |    |
|    |    |    |    |    |    |
```

Висновок:

```text
проблема не тільки в AI-згенерованій картинці.
Docling у поточній конфігурації погано читає таблиці саме з image input.
```

---

## 6.7. Тест із HTML-накладною

Було створено HTML-документ зі справжньою HTML-таблицею:

```text
app/debug/create_clean_invoice_html.py
data/inbox/clean_invoice_test.html
```

Docling ідеально витягнув таблицю:

```markdown
| № | Найменування        | Од. | К-сть | Ціна без ПДВ | Сума без ПДВ |
|---|---------------------|-----|-------|--------------|--------------|
| 1 | Фарба біла          | шт  | 10    | 200,00       | 2 000,00     |
| 2 | Горщики для вазонів | шт  | 5     | 100,00       | 500,00       |
```

Висновок:

```text
Docling добре працює зі структурними таблицями,
але погано працює з таблицями, які є тільки картинкою.
```

Цей експеримент був потрібен не для production, а щоб локалізувати проблему.

---

# 7. Експерименти з OpenAI Vision

## 7.1. Мета

Перевірити, чи сильна мультимодальна модель може напряму витягнути таблицю з PNG, яку Docling не зміг витягнути.

Було використано модель:

```text
gpt-4.1-mini
```

---

## 7.2. Тестовий скрипт

Файл:

```text
app/debug/test_openai_vision_invoice.py
```

Логіка:

```text
1. взяти PNG-файл
2. закодувати в base64 data URL
3. відправити в OpenAI Responses API
4. попросити повернути JSON
5. розпарсити JSON
6. зберегти результат у data/debug/openai_vision_invoice_result.json
```

---

## 7.3. Результат OpenAI Vision

OpenAI Vision правильно витягнув:

```json
{
  "document_kind": "invoice",
  "document_number": "ПН-000127",
  "document_date": "08.05.2026",
  "supplier_name": "1001 Дрібниця, ТзОВ",
  "supplier_ipn": "191714913052",
  "supplier_edrpou": "19171498",
  "items": [
    {
      "line_number": "1",
      "item_name": "Фарба біла",
      "unit": "шт",
      "quantity": "10",
      "unit_price_without_vat": "200,00",
      "line_total_without_vat": "2 000,00"
    },
    {
      "line_number": "2",
      "item_name": "Горшки для вазонів",
      "unit": "шт",
      "quantity": "5",
      "unit_price_without_vat": "100,00",
      "line_total_without_vat": "500,00"
    }
  ],
  "totals": {
    "total_without_vat_before_discount": "2 500,00",
    "discount_amount": "300,00",
    "total_without_vat_after_discount": "2 200,00",
    "vat_rate": "20%",
    "vat_amount": "440,00",
    "total_with_vat": "2 640,00"
  }
}
```

Висновок:

```text
gpt-4.1-mini добре витягує таблицю напряму з PNG.
```

---

## 7.4. Вартість OpenAI Vision

Фактичний usage:

```text
input_tokens = 2712
output_tokens = 382
total_tokens = 3094
```

Орієнтовна вартість для `gpt-4.1-mini`:

```text
input:  2712 × $0.40 / 1 000 000 = $0.0010848
output: 382 × $1.60 / 1 000 000 = $0.0006112
total ≈ $0.001696
```

Тобто приблизно:

```text
1 документ ≈ $0.0017
100 документів ≈ $0.17
1 000 документів ≈ $1.70
10 000 документів ≈ $17
```

Висновок:

```text
OpenAI Vision може бути економічно прийнятним як fallback або як один із паралельних парсерів.
```

---

# 8. Експерименти з локальною Qwen Vision

## 8.1. Модель

Було встановлено локально через Ollama:

```text
qwen2.5vl:7b
```

Команда:

```powershell
ollama pull qwen2.5vl:7b
```

Перевірка:

```powershell
ollama list
```

Список після очищення:

```text
qwen2.5vl:7b
gemma4:e4b
bge-m3:latest
gemma3:4b
gemma3:latest
```

Було видалено зайві великі моделі:

```powershell
ollama rm gpt-oss:20b
ollama rm gemma3:27b
```

---

## 8.2. Простий тест Qwen Vision

Було створено тест:

```text
app/debug/test_qwen_vision_simple.py
```

Prompt:

```text
Look at the image. Return only JSON:
{"document_type": "...", "document_number": "..."}
```

Результат:

```json
{
  "document_type": "ПРИХІДНА НАКЛАДНА",
  "document_number": "ПН-000127"
}
```

Висновок:

```text
qwen2.5vl:7b бачить картинку і може читати документ.
```

---

## 8.3. Проблема зі складним prompt

При спробі одразу витягнути великий JSON через Qwen Vision запит зависав і давав timeout:

```text
Read timed out. read timeout = 300
```

Висновок:

```text
для qwen2.5vl:7b не треба одразу давати великий складний prompt.
Краще розділити extraction на кілька простих запитів.
```

---

# 9. Поточний архітектурний висновок

Раніше розглядалася логіка:

```text
Docling
→ якщо погано, тоді OpenAI або Qwen як fallback
```

Але після обговорення було запропоновано сильніший концепт:

```text
парсити документ паралельно кількома інструментами,
а потім порівнювати результати.
```

Тобто не fallback як виняток, а multi-source extraction.

---

# 10. Нова запропонована архітектура

## 10.1. Загальна ідея

```text
document
→ ParsingOrchestrator
    → DoclingExtractionTool
    → OllamaVisionExtractionTool
    → optional OpenAIVisionExtractionTool
→ ParsingQualityValidator
→ RetryParsingAgent, якщо є конфлікти
→ ResultMerger
→ AmountAnalyzer
→ CounterpartyResolver
→ BusinessClassifier
→ FinalValidator
→ ERP або HITL
```

---

## 10.2. ParsingOrchestrator

Новий центральний компонент.

Його задача:

```text
1. отримати документ
2. визначити тип документа
3. запустити кілька способів парсингу
4. зібрати результати
5. передати результати на quality validation
6. організувати retry loop, якщо потрібно
```

---

## 10.3. DoclingExtractionTool

Відповідає за парсинг через Docling.

Сильні сторони:

```text
шапка
номер документа
дата
контрагенти
ІПН / ЄДРПОУ
підсумки
структурні PDF / HTML
```

Слабкі сторони:

```text
PNG/JPEG-таблиці з товарами
```

---

## 10.4. OllamaVisionExtractionTool

Відповідає за парсинг зображення через локальну vision-модель:

```text
qwen2.5vl:7b
```

Сильні сторони:

```text
товарні таблиці на картинках
візуальне розуміння документа
локальність
відсутність API-витрат
```

Слабкі сторони:

```text
може помилятися
може бути повільною
великий prompt може давати timeout
потрібна кодова валідація
```

---

## 10.5. OpenAIVisionExtractionTool

Може використовуватись:

```text
1. як benchmark
2. як fallback для складних документів
3. як контрольний парсер, якщо локальна модель не впоралась
```

Модель:

```text
gpt-4.1-mini
```

Сильні сторони:

```text
висока якість extraction з PNG/JPEG
швидкість
відносно низька ціна
```

Слабкі сторони:

```text
зовнішній API
питання конфіденційності
залежність від інтернету
```

---

## 10.6. ParsingQualityValidator

Ключовий новий модуль.

Його задача — не довіряти жодному парсеру сліпо, а перевіряти:

```text
1. чи немає конфліктів між Docling і Qwen
2. чи сходиться арифметика
3. чи присутні обов’язкові поля
4. чи коректно витягнуті підсумки
5. чи є достатня якість для автоматичного проходження
```

---

## 10.7. RetryParsingAgent

Якщо є конфлікти, система може повторити парсинг.

Наприклад:

```text
attempt 1:
Docling + Qwen
→ validation failed

attempt 2:
Qwen отримує уточнений prompt:
"Попередній результат мав конфлікт:
сума рядків не сходиться з підсумком.
Перевір таблицю ще раз."

attempt 3:
ще одна спроба

якщо після 3 спроб проблема не вирішена:
HITL
```

Максимальна кількість спроб:

```text
3
```

---

# 11. Логіка перевірки якості парсингу

## 11.1. Перевірка критичних реквізитів

Порівнювати між джерелами:

```text
document_number
document_date
supplier_name
supplier_ipn
supplier_edrpou
customer_name
customer_ipn
customer_edrpou
```

Логіка:

```text
якщо Docling і Qwen збігаються → OK
якщо один має null, інший має значення → можна прийняти значення з нижчим confidence
якщо обидва мають різні значення → conflict
```

---

## 11.2. Перевірка підсумків

Порівнювати:

```text
total_without_vat_before_discount
discount_amount
total_without_vat_after_discount
vat_rate
vat_amount
total_with_vat
```

---

## 11.3. Арифметична перевірка

Для накладної з ПДВ і знижкою:

```text
sum(items.line_total_without_vat) = total_without_vat_before_discount

total_without_vat_before_discount - discount_amount = total_without_vat_after_discount

total_without_vat_after_discount × 20% = vat_amount

total_without_vat_after_discount + vat_amount = total_with_vat
```

Для тестового документа:

```text
2 000 + 500 = 2 500
2 500 - 300 = 2 200
2 200 × 20% = 440
2 200 + 440 = 2 640
```

Якщо всі перевірки сходяться, extraction можна вважати надійним.

---

## 11.4. Перевірка items

Для накладних:

```text
items бажано брати з vision-моделі,
бо Docling погано витягує таблиці з PNG/JPEG.
```

Але результат items треба перевіряти кодом:

```text
чи є line_number
чи є item_name
чи є quantity
чи є unit_price
чи є line_total
чи quantity × unit_price = line_total
чи сума всіх line_total сходиться з total_before_discount
```

---

# 12. Нова бізнес-логіка для накладних

## 12.1. Аналіз господарського призначення по рядках

Для накладної не можна просто визначити весь документ як господарський або негосподарський.

Потрібно аналізувати кожну позицію:

```text
Фарба біла → може бути господарська
Горщики для вазонів → може бути негосподарська
Продукти харчування → часто негосподарські
Коди без опису → невизначено
```

---

## 12.2. Варіанти результатів

### Варіант 1. Усі позиції господарські

```text
якщо всі items господарські
і модель/історія впевнені
→ HITL не потрібен
```

---

### Варіант 2. Усі позиції негосподарські

```text
якщо всі items негосподарські
і модель/історія впевнені
→ HITL не потрібен
```

---

### Варіант 3. Частина господарська, частина негосподарська

Тоді документ треба умовно розділити:

```text
господарська частина:
сума без ПДВ
ПДВ
сума з ПДВ

негосподарська частина:
сума без ПДВ
ПДВ
сума з ПДВ
```

Приклад:

```text
Фарба — 1 500 грн без ПДВ
Горщики — 500 грн без ПДВ

ПДВ 20%:
Фарба → 300 грн
Горщики → 100 грн
```

Такий документ має йти на HITL для підтвердження.

---

### Варіант 4. Позиції незрозумілі

Якщо назви нечіткі або це коди:

```text
item_name = "СРС"
item_name = "код 12345"
```

то документ має йти на HITL.

---

# 13. AmountAnalyzer

Було вирішено створити окремий модуль:

```text
AmountAnalyzer
```

Він має працювати після extraction.

Його задача:

```text
1. визначити ПДВ-сценарій
2. визначити наявність знижки
3. перевірити арифметику
4. нормалізувати суми
5. сформувати amount_model
6. сформувати amount_conflicts
```

---

## 13.1. ПДВ-сценарії

Було погоджено, що краще не використовувати одну змішану категорію, а розділяти логіку так:

```text
without VAT

line mode + included
line mode + not included

document level + included
document level + not included

unknown
```

Тобто окремо визначати:

```text
де рахується ПДВ:
- на рівні рядків
- на рівні документа

як показано ПДВ:
- включено в суму
- не включено в суму
- без ПДВ
```

---

## 13.2. Знижка

Потрібно визначати:

```text
discount_present
discount_level
discount_base
discount_amount
```

Де:

```text
discount_present = чи є знижка
discount_level = none | line | document
discount_base = net | gross | unknown | none
discount_amount = сума знижки
```

---

# 14. HITL

Планується створити user-friendly HITL-інтерфейс.

Ідея:

```text
бухгалтер відкриває аплікацію
бачить таблицю документів, які потребують перевірки
бачить витягнуті дані
підтверджує або змінює рішення
```

Для накладних потрібно буде бачити:

```text
document header
supplier
customer
items
totals
business / non-business classification per item
conflicts
suggested final decision
```

---

# 15. Майбутній pipeline

## 15.1. Для актів

```text
Input document
→ Docling
→ ExtractionAgent
→ CounterpartyResolver
→ BuhgalterAgent
→ ValidatorAgent
→ output або HITL
```

---

## 15.2. Для накладних PNG/JPEG

```text
Input image
→ ParsingOrchestrator
    → DoclingExtractionTool
    → QwenVisionExtractionTool
    → optional OpenAIVisionExtractionTool
→ ParsingQualityValidator
→ retry loop, якщо потрібно
→ ResultMerger
→ AmountAnalyzer
→ LineItemBusinessClassifier
→ CounterpartyResolver
→ FinalValidator
→ output або HITL
```

---

# 16. Що планується зробити найближчим часом

## Крок 1. Спростити Qwen prompt

Для `qwen2.5vl:7b` треба не використовувати великий prompt.

Потрібно зробити короткий prompt:

```json
{
  "document_type": "",
  "document_number": "",
  "document_date": "",
  "supplier_name": "",
  "supplier_ipn": "",
  "supplier_edrpou": "",
  "customer_name": "",
  "customer_ipn": "",
  "customer_edrpou": "",
  "items": [],
  "totals": {}
}
```

Без:

```text
amount_model
discount_model
confidence
reason
line_vat_amount
line_total_with_vat
```

---

## Крок 2. Розділити Qwen extraction на 2 запити

Для стабільності:

```text
QwenHeaderTotalsExtractor
→ шапка, контрагенти, підсумки

QwenItemsExtractor
→ тільки товарні рядки
```

Це зменшить навантаження на локальну модель.

---

## Крок 3. Створити `OllamaVisionExtractionTool`

Файл може бути:

```text
app/extraction/ollama_vision_extraction_tool.py
```

Його задача:

```text
image file
→ base64
→ Ollama /api/generate
→ qwen2.5vl:7b
→ JSON
```

---

## Крок 4. Створити `DoclingExtractionTool`

Замість того, щоб Docling був тільки всередині ParserAgent, винести його як окремий tool.

---

## Крок 5. Створити `ParsingQualityValidator`

Файл може бути:

```text
app/validation/parsing_quality_validator.py
```

Має перевіряти:

```text
missing required fields
field conflicts
math conflicts
items completeness
totals consistency
```

---

## Крок 6. Створити `ParsingOrchestrator`

Файл може бути:

```text
app/orchestration/parsing_orchestrator.py
```

Він буде запускати:

```text
DoclingExtractionTool
OllamaVisionExtractionTool
ParsingQualityValidator
RetryParsingAgent
ResultMerger
```

---

## Крок 7. Створити retry loop

Логіка:

```text
max_attempts = 3

if quality_result.requires_retry:
    generate retry prompt
    call qwen again
else:
    accept result
```

Після 3 невдалих спроб:

```text
hitl_required = true
```

---

## Крок 8. Створити `ResultMerger`

Модуль, який обирає фінальні значення.

Принцип:

```text
якщо Docling і Qwen збігаються → прийняти
якщо Docling пустий, Qwen має значення → прийняти Qwen з нижчим confidence
якщо Qwen і Docling конфліктують → HITL або retry
items для PNG/JPEG переважно брати з Qwen
totals перевіряти через математику
```

---

## Крок 9. Створити `AmountAnalyzer`

Окремий модуль для:

```text
ПДВ
знижки
net/gross
arithmetical checks
amount_model
```

---

## Крок 10. Створити `LineItemBusinessClassifier`

Для накладних:

```text
item_name
→ business / non_business / unknown
```

Потім агрегувати на рівні документа:

```text
all business
all non-business
mixed
unknown
```

---

# 17. Що не варто робити зараз

## Не варто будувати універсальний crop parser

Ми протестували crop-підхід.

Висновок:

```text
для різних типів накладних crop буде нестабільним.
```

Його можна залишити як debug-інструмент, але не як основну архітектуру.

---

## Не варто поки переходити на data-prep-kit

Data-prep-kit може бути корисний для batch-процесингу, але він не вирішує проблему якості table extraction з PNG/JPEG, бо всередині все одно використовує Docling.

---

## Не варто ускладнювати ExtractionAgent

ExtractionAgent не повинен бути одночасно:

```text
OCR parser
amount analyzer
VAT analyzer
discount analyzer
business classifier
validator
```

Це треба розділити на окремі модулі.

---

# 18. Головний архітектурний принцип

Система має працювати не за принципом:

```text
одна модель сказала → значить правда
```

а за принципом:

```text
кілька джерел extraction
+ кодова перевірка
+ арифметична перевірка
+ retry
+ HITL тільки якщо залишилися конфлікти
```

Це особливо важливо для бухгалтерських документів.

---

# 19. Поточний стан у Git

Поточний MVP уже збережено в GitHub.

Основна гілка:

```text
main
```

Створена feature-гілка:

```text
feature/universal-document-items
```

У цій гілці планується розробка універсальної структури `items[]` для актів і накладних.

Було зроблено commit:

```text
Add without VAT handling for extraction and classification
```

Також був commit:

```text
Ignore temporary local data files
```

---

# 20. Короткий підсумок

На поточному етапі ми з’ясували:

```text
1. Поточна система добре працює з актами.
2. Для накладних потрібна item-based структура.
3. Docling погано витягує товарні таблиці з PNG/JPEG.
4. Docling добре витягує структурні таблиці з HTML.
5. OpenAI Vision добре витягує таблицю напряму з PNG.
6. Qwen2.5VL локально бачить документ і може читати шапку.
7. Для Qwen потрібні коротші prompts або розділення extraction на кілька запитів.
8. Найкраща майбутня архітектура — multi-source parsing + validator + retry loop.
```

Найближча практична ціль:

```text
зробити ParsingOrchestrator,
який запускає Docling + Qwen Vision,
порівнює результати,
перезапускає Qwen у разі конфліктів,
і повертає final_extracted_data або hitl_required.
```
