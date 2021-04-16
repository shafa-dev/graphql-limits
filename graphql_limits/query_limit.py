import typing as t

from graphql import (
    GraphQLSchema,
    GraphQLDocument,
)
from graphql.backend.core import GraphQLCoreBackend
from graphql.language.ast import (
    FragmentDefinition,
    FragmentSpread,
    OperationDefinition,
    Field,
    Document,
    Definition,
    IntValue,
    Variable,
)


class DepthLimitReached(Exception):
    pass


class NodesLimitReached(Exception):
    pass


def get_fragments(definitions: t.Iterable[Definition]) -> t.Dict[str, FragmentDefinition]:
    return {
        definition.name.value: definition
        for definition in definitions
        if isinstance(definition, FragmentDefinition)
    }


def get_max_depth(
    node: t.Union[OperationDefinition, Field],
    fragments: t.Dict[str, FragmentDefinition],
    parent_depth: int = 0
) -> int:
    max_depth = parent_depth + 1

    if not node.selection_set:
        # leaf node
        return max_depth

    for field in node.selection_set.selections:
        if isinstance(field, FragmentSpread):
            field = fragments.get(field.name.value)

        depth = get_max_depth(
            field,
            fragments,
            max_depth,
        )
        max_depth = max(max_depth, depth)

    return max_depth


def get_count_of_fetched_nodes(
    node: t.Union[OperationDefinition, Field],
    fragments: t.Dict[str, FragmentDefinition],
    pagination_arguments: t.Iterable[str],
    variable_values: t.Dict[str, t.Any],
) -> int:
    fetched_nodes = 0

    if not node.selection_set:
        # leaf node
        return 0

    for field in node.selection_set.selections:
        if isinstance(field, FragmentSpread):
            field = fragments.get(field.name.value)

        fetched_nodes += get_count_of_fetched_nodes(
            field,
            fragments,
            pagination_arguments,
            variable_values,
        )

    if not fetched_nodes:
        fetched_nodes += 1

    if isinstance(node, Field):
        if node.arguments:
            pagination_arg = next(
                (
                    arg for arg in node.arguments
                    if arg.name.value in pagination_arguments
                ),
                None
            )

            if pagination_arg:
                if isinstance(pagination_arg.value, Variable):
                    value = int(variable_values[pagination_arg.value.name.value])
                    fetched_nodes *= value
                elif isinstance(pagination_arg.value, IntValue):
                    value = int(pagination_arg.value.value)
                    fetched_nodes *= value

    return fetched_nodes


class ProtectorBackend(GraphQLCoreBackend):
    def __init__(
        self,
        *args: t.Any,
        variable_values: t.Dict[str, t.Any],
        depth_limit: int = None,
        nodes_limit: int = None,
        pagination_arguments: t.Iterable[str] = ('first', 'last'),
        **kwargs: t.Any,
    ):
        """
        variable_values - variables dict if arguments for graphql operations pass in request body
        depth_limit - depth limit for graphql operations
        nodes_limit - how many nodes can be fetch.
            Example: {books(first: 100) {author { books(first: 100) }}} this query will fetch 100 * 100 nodes
        pagination_arguments - list of pagination argument names(it can be 'first', 'count' etc. )
            Default: 'first', 'last'
        """
        super().__init__(*args, **kwargs)
        self._depth_limit = depth_limit
        self._nodes_limit = nodes_limit
        self._variable_values = variable_values
        self._pagination_arguments = pagination_arguments

    def document_from_string(
        self,
        schema: GraphQLSchema,
        document_string: t.Union[Document, str]
    ) -> GraphQLDocument:
        document = super().document_from_string(schema, document_string)
        ast = document.document_ast
        # fragments are like a dictionary of views
        fragments = get_fragments(ast.definitions)

        for definition in ast.definitions:
            # only queries and mutations
            if not isinstance(definition, OperationDefinition):
                continue

            if self._nodes_limit:
                fetched_nodes = get_count_of_fetched_nodes(
                    definition,
                    fragments,
                    self._pagination_arguments,
                    self._variable_values,
                )

                if fetched_nodes > self._nodes_limit:
                    raise NodesLimitReached('Operation fetches a lot of nodes')

            if self._depth_limit:
                max_depth = get_max_depth(definition, fragments)

                if max_depth > self._depth_limit:
                    raise DepthLimitReached('Query is too deep')

        return document
