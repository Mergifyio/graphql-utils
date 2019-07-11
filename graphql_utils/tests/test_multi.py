import pytest

from graphql_utils import multi


def test_build_multi_query():
    query = """repository(owner: "{owner}", name: "{name}") {{
    name
}}"""
    repos = (
        {
            "owner": "jd",
            "name": "foo",
        },
        {
            "owner": "jd",
            "name": "bar",
        },
    )
    assert (
        multi.build_multi_query(query, repos) ==
        ["""{
Q0: repository(owner: "jd", name: "foo") {
    name
}
Q1: repository(owner: "jd", name: "bar") {
    name
}
}"""]
    )


def test_multi_query_limit():
    Q0_first_result = {
        "Q0": {
            "collaborators": {
                "nodes": [],
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": None,
                }
            },
        },
    }
    Q1_first_result = {
        "Q1": {
            "collaborators": {
                "nodes": [],
                "pageInfo": {
                    "hasNextPage": True,
                    "endCursor": "magic==",
                },
            }
        },
    }

    send_fn_calls = {"call": 0}

    def send_fn(query):
        send_fn_calls['call'] += 1
        if send_fn_calls['call'] == 1:
            assert query == """{
Q0: repository(owner: "jd", name: "foo") {
             collaborators(first: 100) {
                nodes {
                  login
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
        }
}"""
            return {"data": Q0_first_result}

        if send_fn_calls['call'] == 2:
            assert query == """{
Q1: repository(owner: "jd", name: "bar") {
             collaborators(first: 100) {
                nodes {
                  login
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
        }
}"""
            return {"data": Q1_first_result}

        assert query == """{
Q1: repository(owner: "jd", name: "bar") {
             collaborators(first: 100 after: "magic==" ) {
                nodes {
                  login
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
        }
}"""
        return {"data": {}}

    repos = (
        {
            "owner": "jd",
            "name": "foo",
        },
        {
            "owner": "jd",
            "name": "bar",
        },
    )

    iterable_result = multi.multi_query(
        """repository(owner: "{owner}", name: "{name}") {{
             collaborators(first: 100{{after}}) {{
                nodes {{
                  login
                }}
                pageInfo {{
                  hasNextPage
                  endCursor
                }}
              }}
        }}""",
        repos,
        send_fn,
        ("collaborators", "pageInfo"),
        max_batch_size=1,
    )

    assert next(iterable_result) == Q0_first_result
    assert next(iterable_result) == Q1_first_result
    with pytest.raises(StopIteration):
        next(iterable_result)


def test_multi_query():
    Q0_first_result = {
        "Q0": {
            "collaborators": {
                "nodes": [],
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": None,
                }
            },
        },
    }
    Q1_first_result = {
        "Q1": {
            "collaborators": {
                "nodes": [],
                "pageInfo": {
                    "hasNextPage": True,
                    "endCursor": "magic==",
                },
            }
        },
    }
    first_result = {**Q0_first_result, **Q1_first_result}

    send_fn_calls = {"call": 0}

    def send_fn(query):
        send_fn_calls['call'] += 1
        if send_fn_calls['call'] == 1:
            assert query == """{
Q0: repository(owner: "jd", name: "foo") {
             collaborators(first: 100) {
                nodes {
                  login
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
        }
Q1: repository(owner: "jd", name: "bar") {
             collaborators(first: 100) {
                nodes {
                  login
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
        }
}"""
            return {"data": first_result}

        assert query == """{
Q1: repository(owner: "jd", name: "bar") {
             collaborators(first: 100 after: "magic==" ) {
                nodes {
                  login
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
        }
}"""
        return {"data": {}}

    repos = (
        {
            "owner": "jd",
            "name": "foo",
        },
        {
            "owner": "jd",
            "name": "bar",
        },
    )

    iterable_result = multi.multi_query(
        """repository(owner: "{owner}", name: "{name}") {{
             collaborators(first: 100{{after}}) {{
                nodes {{
                  login
                }}
                pageInfo {{
                  hasNextPage
                  endCursor
                }}
              }}
        }}""",
        repos,
        send_fn,
        ("collaborators", "pageInfo"),
    )

    assert next(iterable_result) == first_result
    with pytest.raises(StopIteration):
        next(iterable_result)
