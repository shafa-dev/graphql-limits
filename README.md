# graphql-limits

Features included: 
- Limit Query Depth
- [Limit Query Nodes](https://docs.github.com/en/graphql/overview/resource-limitations)

### Prerequisites 

- [graphql-core](https://github.com/graphql-python/graphql-core) 


### Installation 

-  `pip install graphql-limits` 


### Usage example 

```python
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
backend = ProtectorBackend(nodes_limit=399, depth_limit=5, variable_values={'first': 2})
result = schema.execute(query_string, backend=backend, variable_values={'first': 2})
```
    