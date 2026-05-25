"""
1.) печатает метаданные merge-коммита 9dce5d6
и всех зависимых от него коммитов в main, включая изменения (A/M/D/R).
Только чтение. Использует исключительно GitPython (pip install GitPython).

2.) пересоздаёт 9dce5d6 без D-удалений под "2 семестр/Моделирование/"
и пересчитывает двух его потомков в main (a4436f9, e2d48b2).
Метаданные (author / committer / обе даты / message / encoding) сохраняются.
В overlay также добавляется сам commit-fixer.py (в корень репозитория).
Используется только API GitPython (pip install GitPython).
"""

import os
import sys
from io import BytesIO

from git import Repo, Commit
from git.index import IndexFile
from git.index.typ import BaseIndexEntry, IndexEntry
from git.objects import Blob
from gitdb.base import IStream


BAD = "9dce5d6"
BRANCH = "main"
PREFIX = "2 семестр/Моделирование/"
SCRIPT_IN_REPO = "commit-fixer.py"
BACKUP_BRANCH = "main-before-fix"


# ~~~ вычислительные функции ~~~

def show_meta(c):
    def fmt(dt):
        return dt.isoformat() if dt else "(нет)"

    print(f"{'=' * 77}")
    print(f"commit     {c.hexsha}")
    print(f"tree       {c.tree.hexsha}")

    if len(c.parents) > 1:
        print(f"merge      {', '.join(p.hexsha for p in c.parents)}")
        print(f"           ({len(c.parents)} родителя)")
    elif c.parents:
        print(f"parent     {c.parents[0].hexsha}")
    else:
        print(f"parent     (корневой)")

    print()
    print(f"author     {c.author.name} <{c.author.email}>")
    print(f"authored   {fmt(c.authored_datetime)}")
    print(f"committer  {c.committer.name} <{c.committer.email}>")
    print(f"committed  {fmt(c.committed_datetime)}")

    if c.encoding:
        print(f"encoding   {c.encoding}")

    print()
    print("message:")
    for line in c.message.rstrip("\n").splitlines():
        print(f"  | {line}")
    print()


def show_diff(parent, commit, label):
    print(f"  --- {label}: {parent.hexsha[:8]} → {commit.hexsha[:8]} ---")

    # GitPython: parent.diff(commit) == изменения от parent к commit
    try:
        diffs = parent.diff(commit, find_renames=True)
    except TypeError:
        diffs = parent.diff(commit)

    if not diffs:
        print("  (пусто)")
        print()
        return

    for d in diffs:
        score = d.score if d.score is not None else 100
        if d.renamed_file:
            print(f"  R{score:03d}  {d.a_path}  →  {d.b_path}")
        elif d.new_file:
            print(f"  A   {d.b_path or d.a_path}")
        elif d.deleted_file:
            print(f"  D   {d.a_path or d.b_path}")
        elif d.change_type == "M":
            print(f"  M   {d.b_path or d.a_path}")
        else:
            print(f"  {d.change_type}   {d.a_path or d.b_path}")
    print()


def scanner():
    repo = Repo(".")

    try:
        bad = repo.commit(BAD)
    except Exception as e:
        print(f"Не найден {BAD}: {e}", file=sys.stderr)
        return

    print()
    print(f"### ЦЕЛЕВОЙ MERGE-КОММИТ {BAD} ###")
    print()
    show_meta(bad)

    if len(bad.parents) > 1:
        for i, p in enumerate(bad.parents, start=1):
            show_diff(p, bad, f"diff vs parent #{i}")

    print(f"### ПОТОМКИ {BAD} ПО FIRST-PARENT ЦЕПОЧКЕ {BRANCH} ###")
    print()

    try:
        descendants = list(
            repo.iter_commits(
                f"{BAD}..{BRANCH}",
                first_parent=True,
                reverse=True,
            )
        )
    except Exception as e:
        print(f"Ошибка iter_commits: {e}", file=sys.stderr)
        return

    if not descendants:
        print(f"Потомков нет (или {BAD} не на first-parent цепочке {BRANCH}).")
        return

    for c in descendants:
        show_meta(c)
        if len(c.parents) > 1:
            for i, p in enumerate(c.parents, start=1):
                show_diff(p, c, f"diff vs parent #{i}")
        elif c.parents:
            show_diff(c.parents[0], c, "diff vs parent")

    print(f"### СВОДКА: 2 семестр/Моделирование/ в {BRANCH} относительно {BAD}^1 ###")
    print()

    if bad.parents:
        base = bad.parents[0]
        tip  = repo.commit(BRANCH)
        found = False
        try:
            diffs = base.diff(tip, find_renames=True)
        except TypeError:
            diffs = base.diff(tip)

        for d in diffs:
            paths = (d.a_path or "", d.b_path or "")
            if any(p.startswith("2 семестр/Моделирование/") for p in paths):
                found = True
                score = d.score if d.score is not None else 100
                if d.renamed_file:
                    print(f"  R{score:03d}  {d.a_path}  →  {d.b_path}")
                elif d.new_file:
                    print(f"  A   {d.b_path or d.a_path}")
                elif d.deleted_file:
                    print(f"  D   {d.a_path or d.b_path}")
                else:
                    print(f"  {d.change_type}   {d.b_path or d.a_path}")

        if not found:
            print("  (в 2 семестр/Моделирование/ относительно 9dce5d6^1 ничего не изменилось)")
    print()


def collect_under(tree, prefix):
    """Все blobs под prefix из дерева: {path: (mode, hexsha)}."""
    out = {}
    for item in tree.traverse():
        if item.type != "blob":
            continue
        p = item.path
        if p == prefix.rstrip("/") or p.startswith(prefix):
            out[p] = (item.mode, item.hexsha)
    return out


def overlay_tree(repo, base_tree, overlay):
    """Новое дерево = base_tree, поверх которого наложены overlay-пути."""
    index = IndexFile.from_tree(repo, base_tree)
    for path, (mode, hexsha) in overlay.items():
        binsha = bytes.fromhex(hexsha)
        entry = IndexEntry.from_base(
            BaseIndexEntry((mode, binsha, 0, path))
        )
        index.entries[(path, 0)] = entry
    tree = index.write_tree()
    return tree if not isinstance(tree, str) else repo.tree(tree)


# ~~~ DANGER функции ~~~

def store_blob(repo, data, path, mode=0o100644):
    """Записать data в ODB как blob и добавить в индекс.

    Возвращает (mode, hexsha: str), как collect_under — единый формат
    для overlay. istream.hexsha у gitdb возвращает bytes, поэтому
    берём istream[0].hex() (binsha.hex() → str).
    """
    istream = repo.odb.store(IStream(Blob.type, len(data), BytesIO(data)))

    entry = IndexEntry.from_base(
        BaseIndexEntry((mode, istream.binsha, 0, path))
    )
    repo.index.entries[(path, 0)] = entry
    repo.index.write()

    return mode, istream[0].hex()

def make_commit(repo, tree, src, parents):
    """Создать коммит с метаданными src, но с новым деревом и родителями.

    create_from_tree не принимает encoding — берёт его из конфига или
    default_encoding (UTF-8). Для src.encoding == "UTF-8" результат
    семантически идентичен: заголовок "encoding UTF-8" в новом коммите
    просто не будет записан, потому что GitPython пишет его только
    если encoding отличается от UTF-8.
    """
    return Commit.create_from_tree(
        repo,
        tree=tree,
        message=src.message,
        parent_commits=parents,
        author=src.author,
        committer=src.committer,
        author_date=src.authored_datetime,
        commit_date=src.committed_datetime,
        head=False,  # держимся от бошки подальше :)
    )


# ~~~ основной код ~~~

def fixer():
    repo = Repo(".")

    if repo.is_dirty(untracked_files=False):
        print("Есть незакоммиченные изменения. Сделайте commit/stash.")
        sys.exit(1)

    bad = repo.commit(BAD)
    if len(bad.parents) < 2:
        print(f"{BAD} — не merge-коммит.")
        sys.exit(1)

    # Защита от повторного запуска: после успешного фикса BAD уже не предок BRANCH.
    if not repo.is_ancestor(bad, repo.commit(BRANCH)):
        print(f"{BAD} не является предком {BRANCH} — фикс уже был применён.")
        print(f"Откат: git reset --hard {BACKUP_BRANCH}")
        sys.exit(1)

    p1, p2 = bad.parents[0], bad.parents[1]

    # Файлы "2 семестр/Моделирование/" из первого родителя
    extra = collect_under(p1.tree, PREFIX)
    print(f"Восстанавливаем {len(extra)} файлов из {p1.hexsha[:8]} под {PREFIX!r}:")
    for path in sorted(extra):
        mode, hexsha = extra[path]
        print(f"  {oct(mode)[2:]:>6}  {hexsha[:8]}  {path}")
    print()

    # Добавляем сам скрипт в overlay под именем commit-fixer.py в корне репозитория
    try:
        script_path = os.path.abspath(__file__)
        with open(script_path, "rb") as f:
            script_data = f.read()
        extra[SCRIPT_IN_REPO] = store_blob(repo, script_data, SCRIPT_IN_REPO)
        print(f"Добавляем в overlay: {SCRIPT_IN_REPO} ({len(script_data)} байт, "
              f"blob {extra[SCRIPT_IN_REPO][1][:8]})")
    except Exception as e:
        print(f"Не удалось прочитать {script_path!r}: {e}. Скрипт не будет добавлен.")
    print()

    # backup: не перезаписываем существующий, чтобы не потерять старый бэкап
    old_tip = repo.commit(BRANCH)
    existing_backup = next(
        (h for h in repo.heads if h.name == BACKUP_BRANCH), None
    )
    if existing_backup is not None:
        print(f"Ветка {BACKUP_BRANCH} уже существует на "
              f"{existing_backup.commit.hexsha[:8]}, не трогаем.")
        if existing_backup.commit.hexsha != old_tip.hexsha:
            print(f"  (текущий {BRANCH} = {old_tip.hexsha[:8]}; "
                  f"бэкап остаётся на {existing_backup.commit.hexsha[:8]})")
    else:
        repo.git.branch(BACKUP_BRANCH, old_tip.hexsha)
        print(f"Backup: {BACKUP_BRANCH} → {old_tip.hexsha[:8]}")
    print()

    # 1) новый merge без D
    bad_tree = overlay_tree(repo, bad.tree, extra)
    bad_new  = make_commit(repo, bad_tree, bad, [p1, p2])
    print(f"9dce5d6 → {bad_new.hexsha[:8]}")

    old2new = {bad.hexsha: bad_new.hexsha}

    # 2) потомки по first-parent chain
    descendants = list(
        repo.iter_commits(f"{BAD}..{BRANCH}", first_parent=True, reverse=True)
    )
    if not descendants:
        print("Потомков нет.")
        return

    for c in descendants:
        tree_new = overlay_tree(repo, c.tree, extra)
        parents_new = [
            repo.commit(old2new.get(p.hexsha, p.hexsha)) for p in c.parents
        ]
        c_new = make_commit(repo, tree_new, c, parents_new)
        old2new[c.hexsha] = c_new.hexsha
        print(f"{c.hexsha[:8]} → {c_new.hexsha[:8]}  ({c.summary})")

    new_tip = old2new[descendants[-1].hexsha]
    print(f"\n{BRANCH}: {old_tip.hexsha[:8]} → {new_tip[:8]}")

    # 3) обновить ref и рабочее дерево
    repo.git.update_ref(f"refs/heads/{BRANCH}", new_tip)
    try:
        repo.git.symbolic_ref("HEAD", f"refs/heads/{BRANCH}")
    except Exception:
        pass
    repo.git.reset("--hard", BRANCH)

    print("\nГотово. Проверка:")
    print(f"  git log --oneline --graph {BRANCH}")
    print(f"  git diff --name-status {BACKUP_BRANCH} {BRANCH}")
    print("\nОткат:")
    print(f"  git reset --hard {BACKUP_BRANCH}")
    print("\nPush:")
    print(f"  git push origin {BRANCH} --force")


if __name__ == "__main__":
    # scanner()
    fixer()
