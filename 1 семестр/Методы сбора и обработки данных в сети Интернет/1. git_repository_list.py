import requests
from enum import Enum
from typing import Optional
from pprint import pprint

from ASDsecrets import Storage



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

    params = {}
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



storage = Storage("token.asd")
# storage.store({"token": "TOKEN"}, "secret", "token.asd")
token = storage.load("token.asd", "token")["token"]

session = requests.Session()
session.headers.update({
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {token}",
    "X-GitHub-Api-Version": "2022-11-28",
})

if __name__ == "__main__":
    try:
        activities = list_repo_activities(
            session       = session,
            owner         = "VectorASD",
            repo          = "Magistracy",
            direction     = Direction.DESC,
            per_page      = 10,
            time_period   = TimePeriod.YEAR,
            activity_type = ActivityType.PUSH,
        )
        print("|activities|:", len(activities))
        pprint(activities)
    except Exception as e:
        print("Ошибка:", e)
