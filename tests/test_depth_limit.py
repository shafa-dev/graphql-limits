from unittest import TestCase

import graphene
from graphql_limits import (
    ProtectorBackend,
    DepthLimitReached,
)


class User(graphene.ObjectType):
    id = graphene.Int()
    book = graphene.Field('tests.test_depth_limit.Book')

    def resolve_id(self, *args):
        return 1

    def resolve_book(self, *args):
        return {'title': 'QQ'}


class Book(graphene.ObjectType):
    title = graphene.String()
    author = graphene.Field(User)

    def resolve_author(self, *args):
        return {'id': 1}


class Query(graphene.ObjectType):
    viewer = graphene.Field(User)

    def resolve_viewer(self, *args):
        return {'id': 1}


class TestDepthLimit(TestCase):
    def test_big_depth(self):
        query_string = '''
            query Q {
                viewer {
                   book {
                        author {
                            book {
                                author {
                                    book {
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
                   book {
                        author {
                            book {
                                author {
                                    book {
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
        result = schema.execute(query_string, backend=ProtectorBackend(depth_limit=5, variable_values={}))

        self.assertIsInstance(result.errors[0], DepthLimitReached)
        self.assertIsNone(result.data)

    def test_small_depth(self):
        query_string = '''
            query {
                viewer {
                   book {
                        author {
                            id
                        }
                   }
                }
            }
        '''
        schema = graphene.Schema(query=Query)
        result = schema.execute(query_string, backend=ProtectorBackend(depth_limit=100, variable_values={}))

        self.assertEqual(
            result.data['viewer']['book']['author']['id'],
            1
        )
        self.assertIsNone(result.errors)

    def test_big_depth_with_fragment(self):
        query_string = '''
            fragment authorFragment on User {
                author {
                    book {
                        author {
                            book {
                                author {
                                    id
                                }
                            }
                        }
                    }
                }
            }
            query Q {
                viewer {
                   book {
                        author {
                            book {
                                ...authorFragment
                            }
                        }
                   }
                }
                viewer {
                   book {
                    ...authorFragment
                   }
                }
            }
        '''
        schema = graphene.Schema(query=Query)
        result = schema.execute(query_string, backend=ProtectorBackend(depth_limit=5, variable_values={}))

        self.assertIsInstance(result.errors[0], DepthLimitReached)
        self.assertIsNone(result.data)

    def test_ignore_introspection(self):
        query_string = """
            query IntrospectionQuery {
            __schema {
              queryType { name }
              mutationType { name }
              subscriptionType { name }
              types {
                ...FullType
              }
              directives {
                name
                description
                locations
                args {
                  ...InputValue
                }
              }
            }
          }
        
          fragment FullType on __Type {
            kind
            name
            description
            fields(includeDeprecated: true) {
              name
              description
              args {
                ...InputValue
              }
              type {
                ...TypeRef
              }
              isDeprecated
              deprecationReason
            }
            inputFields {
              ...InputValue
            }
            interfaces {
              ...TypeRef
            }
            enumValues(includeDeprecated: true) {
              name
              description
              isDeprecated
              deprecationReason
            }
            possibleTypes {
              ...TypeRef
            }
          }
        
          fragment InputValue on __InputValue {
            name
            description
            type { ...TypeRef }
            defaultValue
          }
        
          fragment TypeRef on __Type {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                  ofType {
                    kind
                    name
                    ofType {
                      kind
                      name
                      ofType {
                        kind
                        name
                        ofType {
                          kind
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        """

        schema = graphene.Schema(query=Query)
        result = schema.execute(query_string, backend=ProtectorBackend(depth_limit=5, variable_values={}))

        self.assertIsNone(result.errors)
