import itertools


def _grouper(iterable, n):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


def _build_queries_for_multi(query, iterable, extra_format=None):
    if extra_format is None:
        extra_format = {}
    return {
        ("Q%d" % idx): ("Q%d: " % idx) + query.format(**{**i, **extra_format})
        for idx, i in enumerate(iterable)
    }


def _format_queries(queries):
    return "{\n" + "\n".join(queries) + "\n}"


def build_multi_query(query, iterable, max_batch_size=100):
    """Build a giant GraphQL query that encapsulates a query multiple times.

    :param query: The original query. Use {} from `format` as placeholders.
    :param iterable: The iterable to use to build the subqueries.
    :param max_batch_size: The maximum number of queries to execute in one
                           batch.
    :return: A list of queries to execute.
    """
    return [
        _format_queries(_build_queries_for_multi(query, subiter).values())
        for subiter in _grouper(iterable, max_batch_size)
    ]


def multi_query(query, iterable, send_fn,
                pageinfo_path=None, max_batch_size=100):
    """Build a GraphQL query that encapsulates a query multiple times.

    The master query must contains a way to retrieve a `pageInfo` structure in
    order to handle pagination. The request should request the `hasNextPage`
    and `endCursor` attributes of `pageInfo`.

    :param query: The original query. Use {} from `format` as placeholders.
                  The query must contains the {after} format
                  to handle pagination.
    :param iterable: The iterable to use to build the subqueries.
    :param send_fn: The function to use to send the request.
                    It must accepts the query as argument and returns
                    the query result.
    :param pageinfo_path: The path of the pagination key.
    :param max_batch_size: The maximum number of queries to execute in one
                           batch.
    """
    if pageinfo_path is not None and '{after}' not in query:
        raise ValueError("No {after} placeholder found in query")

    # Compile queries but keep them in a state where we can replace {after} by
    # our cursor for pagination
    queries = {
        key: query.replace("{", "{{").replace("}", "}}").replace(
            "{{after}}", "{after}")
        for key, query
        in _build_queries_for_multi(
            query, iterable, {"after": "{after}"}).items()
    }

    for batch in _grouper(queries.items(), max_batch_size):
        batched_queries = dict(batch)
        after_keys = {query_key: "" for query_key in batched_queries.keys()}
        while batched_queries:
            response = send_fn(
                _format_queries(
                    (query.format(after=after_keys[query_key])
                     for query_key, query in batched_queries.items())
                )
            )
            data = response.get('data')
            if not data:
                break
            yield data

            # Now handle pagination
            if pageinfo_path is None:
                batched_queries = {}
            else:
                after_keys = {}
                for subquery_key, subquery_response in data.items():
                    pageinfo = data[subquery_key]
                    for key in pageinfo_path:
                        if key not in pageinfo:
                            raise ValueError("Unable to find key %s" % key)
                        pageinfo = pageinfo[key]
                    if pageinfo['hasNextPage']:
                        after_keys[subquery_key] = (
                            " after: \"%s\" " % pageinfo['endCursor']
                        )
                    else:
                        del batched_queries[subquery_key]
