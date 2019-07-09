==========================
 GraphQL Utils for Python
==========================

.. image:: https://circleci.com/gh/Mergifyio/graphql-utils.svg?style=svg
   :target: https://circleci.com/gh/Mergifyio/graphql-utils

.. image:: https://img.shields.io/endpoint.svg?url=https://gh.mergify.io/badges/Mergifyio/graphql-utils&style=flat
   :target: https://mergify.io
   :alt: Mergify Status

The ``graphql-utils`` Python package is a collection of utilities function for
interacting with GraphQL libraries. It is meant to be library agnostic so it
should work with whatever library or protocol you want.


Usage
=====

Multi-requests
--------------

The multi-requests module allows you to send a request multiple times with
different parameter. It also supports pagination, making sure that you'll get
all the results for all the requests you sent.

Example::

  import requests

  from graphql_utils import multi

  def requests_api(query):
      return requests.post("https://myapi.com/graphql", json=query)

  userlist = ("jd", "sileht", "foo", "bar")

  results = multi.multi_query("""
      user(login: "{login}") {{
        pets(first: 100{after}) {{
          nodes {{
            name
          }}
          pageInfo {{
            hasNextPage
            endCursor
          }}
        }}
      }}""",
      iterable=userlist,
      pageinfo_path=("pets", "pageInfo"),
      send_fn=requests_api,
  )


This will send one GraphQL requests with 4 queries (one for each user from
``userlist``). As `pageinfo_path` was specified, if any of the query does not
return all information in one request, a new query using the ``endCursor`` will
be automatically sent to get the next results.
