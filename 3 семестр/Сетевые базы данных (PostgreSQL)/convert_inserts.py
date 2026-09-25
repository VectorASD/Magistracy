#!/usr/bin/env python3
"""
Преобразует пачку Oracle-подобных INSERT-ов в один multi-row INSERT
с выравниванием столбцов через ljust/rjust.

Использование:
    python convert_inserts.py Задания/wc2014.sql
"""

import re
import sys
from pathlib import Path


# Insert into SHOOTER_LIST(...) values (...);
INSERT_RE = re.compile(
    r"Insert\s+into\s+(\w+)\s*\(([^)]+)\)\s*values\s*\(([^)]+)\)\s*;",
    re.IGNORECASE,
)

def split_values(s: str) -> list[str]:
    """Разбивает строку значений по запятым, не трогая запятые внутри '...'."""
    result = []
    current = []
    in_quote = False
    i = 0
    while i < len(s):
        c = s[i]
        if c == "'" and not in_quote:
            in_quote = True
            current.append(c)
        elif c == "'" and in_quote:
            # Экранированный апостроф внутри строки: ''
            if i + 1 < len(s) and s[i + 1] == "'":
                current.append("''")
                i += 1
            else:
                in_quote = False
                current.append(c)
        elif c == "," and not in_quote:
            result.append("".join(current).strip())
            current = []
        else:
            current.append(c)
        i += 1
    if current:
        result.append("".join(current).strip())
    return result


def parse_line(line: str):
    m = INSERT_RE.search(line)
    if not m:
        return None
    table = m.group(1)
    columns = [c.strip() for c in m.group(2).split(",")]
    values = split_values(m.group(3))
    return table, columns, values


def format_insert(table: str, columns: list[str], rows: list[list[str]]) -> str:
    # Ширина каждого столбца = максимум из длины всех значений
    if not rows:
        print("Не найдено ни одного INSERT-а", file=sys.stderr)
        sys.exit(2)

    widths = [max(map(len, col)) for col in zip(*rows)]
    numeric = [all(v.isdigit() for v in col) for col in zip(*rows)]

    out = []
    out.append(f"INSERT INTO {table} ({', '.join(columns)}) VALUES")

    for idx, row in enumerate(rows):
        cells = [
            (v.rjust if is_num else v.ljust)(widths[i])
            for (i, v), is_num in zip(enumerate(row), numeric)
        ]
        if idx < len(rows) - 1:
            out.append("    (" + ", ".join(cells) + "),")
        else:
            out.append("    (" + ", ".join(cells) + ");")

    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_inserts.py <file.sql>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1]).resolve()

    if not path.exists():
        print(f"Файл не найден: {path}", file=sys.stderr)
        sys.exit(1)
    if not path.is_file():
        print(f"Это не файл: {path}", file=sys.stderr)
        sys.exit(1)

    with path.open(encoding="utf-8") as f:
        content = f.read()

    table = None
    columns = None
    rows = []

    for line in content.splitlines():
        parsed = parse_line(line)
        if not parsed:
            continue
        t, c, v = parsed
        if table is None:
            table = t
            columns = c
        elif t != table or c != columns:
            print(
                f"Warning: разная схема в строке – пропускаю: {line[:80]}",
                file=sys.stderr,
            )
            continue
        rows.append(v)

    rows = sorted(rows, key = lambda row: int(row[0]))
    print(format_insert(table, columns, rows))


if __name__ == "__main__":
    main()
