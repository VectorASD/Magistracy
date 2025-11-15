from enum import Enum
from typing import Optional
from pprint import pprint, pformat
from io import StringIO
import json

from ASDsecrets import Storage

import requests # pip install requests



class Direction(str, Enum):
    ASC  = "asc"
    DESC = "desc"

class TimePeriod(str, Enum):
    DAY     = "day"
    WEEK    = "week"
    MONTH   = "month"
    QUARTER = "quarter"
    YEAR    = "year"

class ActivityType(str, Enum):
    PUSH              = "push"
    FORCE_PUSH        = "force_push"
    BRANCH_CREATION   = "branch_creation"
    BRANCH_DELETION   = "branch_deletion"
    PR_MERGE          = "pr_merge"
    MERGE_QUEUE_MERGE = "merge_queue_merge"

class Visibility(str, Enum):
    ALL    = "all"
    PUBLIC = "public"
    PRIVATE = "private"

class Affiliation(str, Enum):
    OWNER               = "owner"
    COLLABORATOR        = "collaborator"
    ORGANIZATION_MEMBER = "organization_member"

class RepoType(str, Enum):
    ALL    = "all"
    OWNER  = "owner"
    PUBLIC = "public"
    PRIVATE = "private"
    MEMBER = "member"

class Sort(str, Enum):
    CREATED   = "created"
    UPDATED   = "updated"
    PUSHED    = "pushed"
    FULL_NAME = "full_name"



class ParamsBuilder:
    def __init__(self, locals_dict: dict, session: requests.Session):
        self.locals = locals_dict
        self.params = {}
        self.session = session

    def use(self, name: str, param_name: str = None):
        """
        Добавляет параметр в self.params, если он задан в self.locals.
        name — имя переменной в locals_dict
        param_name — имя параметра для запроса (по умолчанию совпадает с name)
        """
        value = self.locals[name]
        if value is not None:
            if isinstance(value, Enum):
                value = value.value
            self.params[param_name or name] = value

    def apply(self, method: str, url: str, **kwargs):
        """
        Делает запрос через session, добавляя собранные параметры.
        """
        return self.session.request(method, url, params=self.params, **kwargs)



def list_repo_activities(
    session:       requests.Session,
    owner:         str,
    repo:          str,
    direction:     Optional[Direction]    = None,
    per_page:      Optional[int]          = None,
    before:        Optional[str]          = None,
    after:         Optional[str]          = None,
    ref:           Optional[str]          = None,
    actor:         Optional[str]          = None,
    time_period:   Optional[TimePeriod]   = None,
    activity_type: Optional[ActivityType] = None,
):
    """
    Получить список активностей репозитория через GitHub REST API.
    https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-repository-activities
    """

    url = f"https://api.github.com/repos/{owner}/{repo}/activity"

    builder = ParamsBuilder(locals(), session)
    builder.use("direction")
    builder.use("per_page")
    builder.use("before")
    builder.use("after")
    builder.use("ref")
    builder.use("actor")
    builder.use("time_period")
    builder.use("activity_type")

    response = builder.apply("GET", url)

    if response.ok: # response.status_code in range(200, 300):
        return response.json()
    raise Exception(f"GitHub API error {response.status_code}: {response.text}")

def list_user_repos(
    session:     requests.Session,
    visibility:  Optional[Visibility] = None,
    affiliation: Optional[Affiliation] = None,
    type:        Optional[RepoType]    = None,
    sort:        Optional[Sort]        = None,
    direction:   Optional[Direction]   = None,
    per_page:    Optional[int]         = None,
    page:        Optional[int]         = None,
    since:       Optional[str]         = None,  # ISO 8601 timestamp
    before:      Optional[str]         = None,  # ISO 8601 timestamp
):
    """
    Получить список репозиториев для авторизованного пользователя через GitHub REST API.
    https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-repositories-for-the-authenticated-user
    """

    url = "https://api.github.com/user/repos"

    builder = ParamsBuilder(locals(), session)
    builder.use("visibility")
    builder.use("affiliation")
    builder.use("type")
    builder.use("sort")
    builder.use("direction")
    builder.use("per_page")
    builder.use("page")
    builder.use("since")
    builder.use("before")

    response = builder.apply("GET", url)

    if response.ok:
        return response.json()
    raise Exception(f"GitHub API error {response.status_code}: {response.text}")



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

def print_repos(repos, stream):
    table = (
        ("ID", "Имя", "Полное имя", "Владелец", "Приватный", "Язык", "Описание",
         "Видимость", "Ветка по умолчанию", "Создан", "Обновлён", "Последний push",
         "Размер", "Stars", "Forks", "Issues", "HTML URL"),
        *((
            repo["id"],
            repo["name"],
            repo["full_name"],
            repo["owner"]["login"],
            f'{repo["private"]} (публичный)' if not repo["private"] else "True (приватный)",
            repo["language"],
            repo["description"],
            repo["visibility"],
            repo["default_branch"],
            repo["created_at"],
            repo["updated_at"],
            repo["pushed_at"],
            "%s Mb. %s Kb." % divmod(repo["size"], 1024),
            repo["stargazers_count"],
            repo["forks_count"],
            repo["open_issues_count"],
            repo["html_url"],
        ) for repo in repos),
    )
    print_table(table, stream)



storage = Storage("token.asd")
# storage.store({"token": "TOKEN"}, "secret", "token.asd")
token = storage.load("token.asd", "token")["token"]

session = requests.Session()
session.headers.update({
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {token}",
    "X-GitHub-Api-Version": "2022-11-28",
})

action = 1

if __name__ == "__main__":
    try:
        if action == 0:
            activities = list_repo_activities(
                session       = session,
                owner         = "VectorASD",
                repo          = "Magistracy",
                direction     = Direction.DESC,
                per_page      = 100,
                page          = 1,
                time_period   = TimePeriod.YEAR,
                activity_type = ActivityType.PUSH,
            )
            print("|activities|:", len(activities))
            pprint(activities)
        elif action == 1:
            repos = list_user_repos(
                session     = session,
                visibility  = Visibility.ALL,
                affiliation = Affiliation.OWNER,
                sort        = Sort.UPDATED,
                direction   = Direction.DESC,
                per_page    = 100,
                page        = 1,
            )

            stream = StringIO()
            stream.write(f"|repos|: {len(repos)}\n")
            print_repos(repos, stream)
            print(stream.getvalue()) # печатаем без pformat(repos)
            stream.write(pformat(repos))

            result = stream.getvalue()
            with open("stdout.txt", "w", encoding="utf-8") as file:
                file.write(result)
            # можно использовать напрямую file, вместо StringIO,
            # но, тогда, мы не сможем напечатать результат в консоль
            # без считывания файла...

            with open("repos.json", "w", encoding="utf-8") as file:
                json.dump(repos, file, indent=4, ensure_ascii=False, sort_keys=True)
    except Exception as e:
        print("Ошибка:", e)
