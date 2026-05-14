from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


OUTPUT_PATH = Path("data/inbox/clean_invoice_test.png")


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    font_paths = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibrib.ttf" if bold else r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\timesbd.ttf" if bold else r"C:\Windows\Fonts\times.ttf",
    ]

    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            continue

    return ImageFont.load_default()


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, size: int = 24, bold: bool = False) -> None:
    draw.text(xy, text, fill="black", font=get_font(size=size, bold=bold))


def main() -> None:
    width, height = 1400, 1900
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    title_font_size = 42
    text_size = 26
    small_size = 23

    # Header
    draw_text(draw, (430, 60), "ПРИХІДНА НАКЛАДНА", title_font_size, bold=True)
    draw_text(draw, (470, 125), "№ ПН-000127 від 08.05.2026", 30, bold=True)

    # Supplier
    y = 210
    draw_text(draw, (80, y), "Постачальник:", text_size, bold=True)
    draw_text(draw, (300, y), "1001 Дрібниця, ТзОВ", text_size)
    y += 42
    draw_text(draw, (80, y), "ІПН:", text_size, bold=True)
    draw_text(draw, (300, y), "191714913052", text_size)
    y += 42
    draw_text(draw, (80, y), "ЄДРПОУ:", text_size, bold=True)
    draw_text(draw, (300, y), "19171498", text_size)

    # Customer
    y += 80
    draw_text(draw, (80, y), "Покупець:", text_size, bold=True)
    draw_text(draw, (300, y), 'ТОВ "СЕ Борднетце - Україна"', text_size)
    y += 42
    draw_text(draw, (80, y), "ІПН:", text_size, bold=True)
    draw_text(draw, (300, y), "344193819180", text_size)
    y += 42
    draw_text(draw, (80, y), "ЄДРПОУ:", text_size, bold=True)
    draw_text(draw, (300, y), "34419383", text_size)

    # Table
    table_x = 70
    table_y = 600
    row_h = 70

    col_widths = [70, 460, 120, 160, 180, 220]
    headers = ["№", "Найменування", "Од.", "К-сть", "Ціна без ПДВ", "Сума без ПДВ"]

    rows = [
        ["1", "Фарба біла", "шт", "10", "200,00", "2 000,00"],
        ["2", "Горщики для вазонів", "шт", "5", "100,00", "500,00"],
    ]

    # Draw table grid
    total_table_width = sum(col_widths)
    total_rows = 1 + len(rows)

    x = table_x
    for w in col_widths:
        draw.line((x, table_y, x, table_y + row_h * total_rows), fill="black", width=2)
        x += w
    draw.line((x, table_y, x, table_y + row_h * total_rows), fill="black", width=2)

    for i in range(total_rows + 1):
        yy = table_y + i * row_h
        draw.line((table_x, yy, table_x + total_table_width, yy), fill="black", width=2)

    # Header row
    x = table_x
    for header, w in zip(headers, col_widths):
        draw_text(draw, (x + 10, table_y + 20), header, small_size, bold=True)
        x += w

    # Data rows
    for row_index, row in enumerate(rows, start=1):
        x = table_x
        yy = table_y + row_index * row_h
        for value, w in zip(row, col_widths):
            draw_text(draw, (x + 10, yy + 20), value, small_size)
            x += w

    # Totals
    y = table_y + row_h * total_rows + 80
    totals_x_label = 650
    totals_x_value = 1050

    totals = [
        ("Загальна сума без ПДВ:", "2 500,00 грн"),
        ("Знижка:", "300,00 грн"),
        ("Сума без ПДВ з урахуванням знижки:", "2 200,00 грн"),
        ("ПДВ 20%:", "440,00 грн"),
        ("Сума з ПДВ:", "2 640,00 грн"),
    ]

    for label, value in totals:
        draw_text(draw, (totals_x_label, y), label, text_size, bold=True)
        draw_text(draw, (totals_x_value, y), value, text_size)
        y += 46

    draw_text(
        draw,
        (80, y + 60),
        "Всього до сплати: Дві тисячі шістсот сорок гривень 00 копійок",
        text_size,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT_PATH)
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()