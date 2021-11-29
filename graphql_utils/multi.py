def _build_queries_for_multi(query, iterable, extra_format=None):
    if extra_format is None:
        extra_format = {}
    return [
        query.format(**{**i, **extra_format})
        for i in iterable
    ]


def _format_queries(queries):
    return "{\n" + "\n".join(
        ("Q%d: " % idx) + query for idx, query in enumerate(queries)
    ) + "\n}"


async def multi_query(query, iterable, send_fn,
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
    queries = [
        (query.replace("{", "{{").replace("}", "}}").replace(
            "{{after}}", "{after}"), "")
        for query
        in _build_queries_for_multi(query, iterable, {"after": "{after}"})
    ]

    while queries:
        batched_queries = queries[:max_batch_size]
        del queries[:max_batch_size]
        response = await send_fn(
            _format_queries(
                (query.format(after=after_key)
                 for query, after_key in batched_queries)
            )
        )
        data = response.get('data')
        if not data:
            break
        yield data

        # Now handle pagination
        if pageinfo_path is not None:
            for query, pageinfo in zip(batched_queries, data.values()):
                for key in pageinfo_path:
                    if key not in pageinfo:
                        raise ValueError("Unable to find key %s" % key)
                    pageinfo = pageinfo[key]
                if pageinfo['hasNextPage']:
                    queries.append((
                        query[0],
                        " after: \"%s\" " % pageinfo['endCursor']
                    ))
