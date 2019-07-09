def _build_queries_for_multi(query, iterable, extra_format=None):
    if extra_format is None:
        extra_format = {}
    return {
        ("Q%d" % idx): ("Q%d: " % idx) + query.format(**{**i, **extra_format})
        for idx, i in enumerate(iterable)
    }


def _format_queries(queries):
    return "{\n" + "\n".join(queries) + "\n}"


def build_multi_query(query, iterable):
    """Build a giant GraphQL query that encapsulates a query multiple times.

    :param query: The original query. Use {} from `format` as placeholders.
    :param iterable: The iterable to use to build the subqueries.
    """
    return _format_queries(_build_queries_for_multi(query, iterable).values())


def multi_query(query, iterable, pageinfo_path, send_fn):
    """Build a GraphQL query that encapsulates a query multiple times.

    The master query must contains a way to retrieve a `pageInfo` structure in
    order to handle pagination. The request should request the `hasNextPage`
    and `endCursor` attributes of `pageInfo`.

    :param query: The original query. Use {} from `format` as placeholders.
                  The query must contains the {after} format
                  to handle pagination.
    :param iterable: The iterable to use to build the subqueries.
    :param pageinfo_path: The path of the pagination key.
    :param send_fn: The function to use to send the request.
                    It must accepts the query as argument and returns
                    the query result.

    """
    if '{after}' not in query:
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
    after_keys = {query_key: "" for query_key in queries.keys()}

    while True:
        response = send_fn(
            _format_queries(
                (query.format(after=after_keys[query_key])
                 for query_key, query in queries.items())
            )
        )
        data = response.get('data')
        if not data:
            break
        yield data

        # Now handle pagination
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
                del queries[subquery_key]
