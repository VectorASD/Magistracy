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
