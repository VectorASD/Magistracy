def print_table(table: tuple[tuple, ...], stream):
    """
    Печатает таблицу с одинаковой шириной колонок и рамками +---+.
    table: кортеж из кортежей, где первый кортеж — заголовки.
    """
    # вычисляем ширину каждой колонки
    col_widths = [max(len(str(row[i])) for row in table) for i in range(len(table[0]))]

    line_separator = "".join(("+", *("-" * (w + 2) + "+" for w in col_widths), "\n"))

    # печать таблицы
    stream.write(line_separator)
    for idx, row in enumerate(table):
        line = "".join(("|", *(" " + str(cell).ljust(col_widths[i]) + " |" for i, cell in enumerate(row)), "\n"))
        stream.write(line)
        stream.write(line_separator)
