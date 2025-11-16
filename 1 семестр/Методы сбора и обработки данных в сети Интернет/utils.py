from datetime import datetime, timezone, timedelta



def print_table(table: tuple[tuple, ...], stream, middle_sep = True):
    """
    Печатает таблицу с одинаковой шириной колонок и рамками +---+.
    table: кортеж из кортежей, где первый кортеж — заголовки.
    """
    # вычисляем ширину каждой колонки
    col_widths = tuple(max(len(str(row[i])) for row in table) for i in range(len(table[0])))

    line_separator = "".join(("+", *("-" * (w + 2) + "+" for w in col_widths), "\n"))

    # определяем, числовая ли колонка
    def skip_header():
        it = iter(table)
        next(it)
        return it
    types = (int, float, complex, type(None))
    numeric_cols = tuple(
        all(isinstance(v, types) for v in (row[i] for row in skip_header()))
        for i in range(len(table[0]))
    )

    # печать таблицы
    stream.write(line_separator)
    it = iter(table)
    header = "".join(("|", *(" " + str(cell).ljust(width) + " |" for cell, width in zip(next(it), col_widths)), "\n"))
    stream.write(header)
    stream.write(line_separator)
    for row in it:
        line = "".join(("|", *(" " + (str(cell).rjust if is_num else str(cell).ljust)(width) + " |" for cell, width, is_num in zip(row, col_widths, numeric_cols)), "\n"))
        stream.write(line)
        if middle_sep: stream.write(line_separator)
    if not middle_sep: stream.write(line_separator)



def href_to_url_wrap(base_url):
    def href_to_url(href):
        if type(href) is list:
            if not href: return None
            href = href[0]
        if href.startswith("/"): href = base_url + href
        return href
    return href_to_url



nsk_tz = timezone(timedelta(hours=7))

months = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

def iso_to_human(date_iso):
    dt = datetime.fromisoformat(date_iso)
    dt_nsk = dt.astimezone(nsk_tz)
    formatted = f"{dt_nsk:%H:%M}, {dt_nsk.day} {months[dt_nsk.month]} {dt_nsk.year}"
    return formatted
