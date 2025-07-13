import json
from typing import Any, List, Tuple

import networkx as nx
from networkx.readwrite import json_graph


class KnowledgeGraph:
    """Simple wrapper around a MultiDiGraph for entity relations."""

    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()

    def add_entity(self, name: str, **attrs: Any) -> None:
        """Add a node representing an entity."""
        self.graph.add_node(name, **attrs)

    def add_relation(self, source: str, target: str, relation: str, **attrs: Any) -> None:
        """Create a typed relation between two entities."""
        self.graph.add_edge(source, target, key=relation, **attrs)

    def remove_entity(self, name: str) -> None:
        """Remove an entity and its relations."""
        if self.graph.has_node(name):
            self.graph.remove_node(name)

    def remove_relation(self, source: str, target: str, relation: str) -> None:
        """Remove a specific relation between two entities."""
        if self.graph.has_edge(source, target, key=relation):
            self.graph.remove_edge(source, target, key=relation)

    def query(self, entity: str) -> List[Tuple[str, str]]:
        """Return outgoing relations from the given entity."""
        return [(key, tgt) for _, tgt, key in self.graph.out_edges(entity, keys=True)]

    def to_json(self) -> str:
        """Serialize the graph to a JSON string."""
        # Explicitly set edges="links" to preserve current behavior and
        # silence FutureWarning about the default changing in NetworkX 3.6.
        data = json_graph.node_link_data(self.graph, edges="links")
        return json.dumps(data)

    @classmethod
    def from_json(cls, data: str) -> "KnowledgeGraph":
        """Create a KnowledgeGraph instance from JSON."""
        instance = cls()
        # Use edges="links" here for compatibility with graphs serialized by
        # ``to_json`` above.
        instance.graph = json_graph.node_link_graph(
            json.loads(data), multigraph=True, edges="links"
        )
        return instance
