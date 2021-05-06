from unittest import TestCase

import graphene
from graphql import GraphQLCoreBackend

from graphql_limits import (
    ProtectorBackend,
    NodesLimitReached,
    get_count_of_fetched_nodes,
)


class User(graphene.ObjectType):
    id = graphene.Int()
    books = graphene.List(
        lambda: Book,
        first=graphene.Int()
    )
    second_books = graphene.List(
        lambda: Book,
        first=graphene.Int()
    )

    def resolve_id(self, *args):
        return 1

    def resolve_books(self, *args, **kwargs):
        return [{'title': 'QQ'}]

    def resolve_second_books(self, *args, **kwargs):
        return [{'title': 'QQ'}]


class Book(graphene.ObjectType):
    title = graphene.String()
    author = graphene.Field(User)

    def resolve_author(self, *args):
        return {'id': 1}


class Query(graphene.ObjectType):
    viewer = graphene.Field(User)

    def resolve_viewer(self, *args):
        return {'id': 1}


class TestNodesLimit(TestCase):
    def test_nodes_limit_reached(self):
        query_string = '''
        query Test($first: Int) {
            viewer {
               books(first: $first) {
                    author {
                        books(first: 4) {
                            author {
                                books(first: 100) {
                                    author {
                                        id
                                    }
                                }
                            }
                        }
                    }
               }
            }
            viewer {
               books(first: $first) {
                    author {
                        books(first: 4) {
                            author {
                                books(first: 100) {
                                    author {
                                        id
                                    }
                                }
                            }
                        }
                    }
               }
            }
        }
        '''
        schema = graphene.Schema(query=Query)
        backend = ProtectorBackend(nodes_limit=1_000, variable_values={'first': 100})
        result = schema.execute(query_string, backend=backend, variable_values={'first': 100})

        self.assertIsInstance(
            result.errors[0],
            NodesLimitReached
        )
        self.assertIsNone(result.data)

    def test_nodes_limit_not_reached(self):
        query_string = '''
        query Test($first: Int) {
            viewer {
               books(first: $first) {
                    author {
                        books(first: 4) {
                            author {
                                books(first: 100) {
                                    author {
                                        id
                                    }
                                }
                            }
                        }
                    }
               }
            }
        }
        '''
        schema = graphene.Schema(query=Query)
        backend = ProtectorBackend(nodes_limit=1_000, variable_values={'first': 2})
        result = schema.execute(query_string, backend=backend, variable_values={'first': 2})

        self.assertEqual(
            result.data['viewer']['books'][0]['author']['books'][0]['author']['books'][0]['author']['id'],
            1
        )
        self.assertIsNone(result.errors)

    def test_with_several_queries(self):
        query_string = (
            'query Q {' +
            '\n'.join('viewer { books { author { id } } }' for _ in range(200)) +
            '}'
        )
        schema = graphene.Schema(query=Query)
        backend = ProtectorBackend(nodes_limit=100, variable_values={})
        result = schema.execute(query_string, backend=backend)

        self.assertIsInstance(
            result.errors[0],
            NodesLimitReached
        )
        self.assertIsNone(result.data)

    def test_with_fragment(self):
        query_string = '''
        fragment authorFragment on User {
            author {
                books(first: 100) {
                    author {
                        id
                    }
                }
            }
        }
        query {
            viewer {
               books {
                    author {
                        books(first: 4) {
                            ...authorFragment
                        }
                    }
               }
            }
        }
        '''
        schema = graphene.Schema(query=Query)
        backend = ProtectorBackend(nodes_limit=399, variable_values={})
        result = schema.execute(query_string, backend=backend, variable_values={})

        self.assertIsInstance(
            result.errors[0],
            NodesLimitReached
        )
        self.assertIsNone(result.data)

    def test_get_count_of_fetched_nodes(self):
        query_string = '''
            query {
                viewer {
                   books(first: 2) {
                        author {
                            books(first: 4) {
                                author {
                                    aa: books(first: 100) {
                                        author {
                                            id
                                        }
                                    }
                                    second_books(first: 200) {
                                        author {
                                            id
                                        }
                                    }
                                }
                            }
                        }
                   }
                }
            }
        '''

        schema = graphene.Schema(query=Query)
        document = GraphQLCoreBackend().document_from_string(schema, query_string)
        ast = document.document_ast
        nodes = get_count_of_fetched_nodes(ast.definitions[0], {}, ['first'], {})
        self.assertEqual(nodes, 2400)
