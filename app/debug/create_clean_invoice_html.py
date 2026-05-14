from pathlib import Path


OUTPUT_PATH = Path("data/inbox/clean_invoice_test.html")


def main() -> None:
    html = """
<!doctype html>
<html lang="uk">
<head>
  <meta charset="utf-8">
  <title>Прихідна накладна</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      font-size: 16px;
      color: #000;
      margin: 40px;
    }
    h1 {
      text-align: center;
      font-size: 28px;
      margin-bottom: 10px;
    }
    h2 {
      text-align: center;
      font-size: 20px;
      margin-top: 0;
      margin-bottom: 30px;
    }
    .row {
      margin: 6px 0;
    }
    .label {
      font-weight: bold;
      display: inline-block;
      width: 180px;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      margin-top: 35px;
      margin-bottom: 35px;
    }
    th, td {
      border: 1px solid #000;
      padding: 8px;
      text-align: left;
      vertical-align: top;
    }
    th {
      font-weight: bold;
      text-align: center;
    }
    .number {
      text-align: right;
      white-space: nowrap;
    }
    .totals {
      width: 520px;
      margin-left: auto;
    }
    .totals-row {
      display: flex;
      justify-content: space-between;
      margin: 8px 0;
    }
    .totals-label {
      font-weight: bold;
    }
  </style>
</head>
<body>
  <h1>ПРИХІДНА НАКЛАДНА</h1>
  <h2>№ ПН-000127 від 08.05.2026</h2>

  <div class="row"><span class="label">Постачальник:</span>1001 Дрібниця, ТзОВ</div>
  <div class="row"><span class="label">ІПН:</span>191714913052</div>
  <div class="row"><span class="label">ЄДРПОУ:</span>19171498</div>

  <br>

  <div class="row"><span class="label">Покупець:</span>ТОВ "СЕ Борднетце - Україна"</div>
  <div class="row"><span class="label">ІПН:</span>344193819180</div>
  <div class="row"><span class="label">ЄДРПОУ:</span>34419383</div>

  <table>
    <thead>
      <tr>
        <th>№</th>
        <th>Найменування</th>
        <th>Од.</th>
        <th>К-сть</th>
        <th>Ціна без ПДВ</th>
        <th>Сума без ПДВ</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="number">1</td>
        <td>Фарба біла</td>
        <td>шт</td>
        <td class="number">10</td>
        <td class="number">200,00</td>
        <td class="number">2 000,00</td>
      </tr>
      <tr>
        <td class="number">2</td>
        <td>Горщики для вазонів</td>
        <td>шт</td>
        <td class="number">5</td>
        <td class="number">100,00</td>
        <td class="number">500,00</td>
      </tr>
    </tbody>
  </table>

  <div class="totals">
    <div class="totals-row"><span class="totals-label">Загальна сума без ПДВ:</span><span>2 500,00 грн</span></div>
    <div class="totals-row"><span class="totals-label">Знижка:</span><span>300,00 грн</span></div>
    <div class="totals-row"><span class="totals-label">Сума без ПДВ з урахуванням знижки:</span><span>2 200,00 грн</span></div>
    <div class="totals-row"><span class="totals-label">ПДВ 20%:</span><span>440,00 грн</span></div>
    <div class="totals-row"><span class="totals-label">Сума з ПДВ:</span><span>2 640,00 грн</span></div>
  </div>

  <p><strong>Всього до сплати:</strong> Дві тисячі шістсот сорок гривень 00 копійок</p>
</body>
</html>
"""

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()