"""
travers

(C) 2023 Justin Joyce.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from pathlib import Path
from typing import Iterable, Tuple

import orjson

from travers.errors import MissingDependencyError


class Graph(object):
    """
    Graph object, optimized for traversal.

    Edges are stored in a dictionary, the key is the source node to speed up
    finding outgoing edges. The Edges only have three pieces of data:
        - the source node (the key)
        - the target node
        - the relationship
    The target and the relationship are stored as a tuple, the edge dictionary
    stores lists of tuples.

    """

    __slots__ = ("_nodes", "_edges")

    def __init__(self):
        """
        Directed Graph.
        """
        self._nodes = {}
        self._edges = {}

    def _make_a_list(self, obj):
        """internal helper method"""
        if isinstance(obj, list):
            return obj
        return [obj]

    def save(self, graph_path):
        """
        Persist a graph to storage. It saves nodes and edges to separate files.

        Parameters:
            graph_path: string
                The folder ?to save the node and edge files to
        """
        path = Path(graph_path)
        path.mkdir(exist_ok=True)

        with open(path / "edges.jsonl", "wb") as edge_file:
            for source, target, relationship in self.edges():
                edge_record = {
                    "source": source,
                    "target": target,
                    "relationship": relationship,
                }
                edge_file.write(orjson.dumps(edge_record) + b"\n")
        with open(path / "nodes.jsonl", "wb") as node_file:
            for nid, attr in self.nodes(data=True):
                node_file.write(orjson.dumps({"nid": nid, "attributes": attr}) + b"\n")

    def add_edge(self, source: str, target: str, relationship: str):
        """
        Add edge to the graph

        Note:
            This does not create nodes if they don't already exist

        Parameters:
            source: string
                The source node
            target: string
                The target node
            relationship: string
                The relationship between the source and target nodes
        """
        if source not in self._edges:
            targets = []
        else:
            targets = self._edges[source]
        targets.append(
            (
                target,
                relationship,
            )
        )
        self._edges[source] = list(set(targets))

    def add_node(self, nid: str, attributes: dict = {}):
        """
        Add node to the graph

        Parameters:
            nid: string
                The Node ID for the node (unique)
            attributes: dictionary (optional)
                The attributes of the node
        """
        self._nodes[nid] = attributes

    def nodes(self, data=False):
        """
        The nodes which comprise the graph

        Parameters:
            data: boolean (optional)
                if True return the details of the nodes, if False just return
                the list of node IDs

        Returns:
            List
        """
        if data:
            return self._nodes.items()
        return list(self._nodes.keys())

    def edges(self):
        """
        The edges which comprise the graph

        Returns:
            Generator of Tuples of (Source, Target and Relationship)
        """
        for s, records in self._edges.items():
            for t, r in records:
                yield s, t, r

    def breadth_first_search(self, source: str, depth: int = 100):
        """
        Search a tree for nodes we can walk to from a given node.

        Parameters:
            source: string
                The node to walk from
            depth: integer
                The maximum distance to walk from source
        Returns:
        """
        # This uses a variation of the algorith used by NetworkX optimized for
        # the travers data structures.
        #
        # https://networkx.org/documentation/networkx-1.10/_modules/networkx/algorithms/traversal/breadth_first_search.html#bfs_tree

        from collections import deque

        distance = 0

        visited = set([source])
        queue = deque(
            [
                (
                    source,
                    distance,
                    self.outgoing_edges(source),
                )
            ]
        )

        new_edges = []

        while queue:
            parent, node_distance, children = queue[0]
            if node_distance < depth:
                for child in children:
                    s, t, r = child
                    new_edges.append(child)
                    if t not in visited:
                        visited.add(t)
                        queue.append(
                            (
                                t,
                                node_distance + 1,
                                self.outgoing_edges(t),
                            )
                        )
            queue.popleft()
        return new_edges

    def outgoing_edges(self, source) -> Iterable[Tuple]:
        """
        Get the list of edges traversable from a given node.

        Parameters:
            source: string
                The node to get the outgoing edges for

        Returns:
            Set of Tuples (Source, Target, Relationship)
        """
        targets = self._edges.get(source) or {}
        return {(source, t, r) for t, r in targets}

    def ingoing_edges(self, target) -> Iterable[Tuple]:
        """
        Get the list of edges which can traverse to a given node.

        Parameters:
            target: string
                The node to get the incoming edges for

        Returns:
            Set of Tuples (Source, Target, Relationship)
        """
        return [(s, t, r) for s, t, r in self.edges() if t == target]

    def is_acyclic(self):
        """
        Test if the Graph is acyclic
        """
        # cycle over the graph removing a layer of exits each cycle
        # if we have nodes but no exists, we're cyclic

        # rebuild the edge information
        my_edges = list(self.edges())

        while len(my_edges) > 0:
            # find all of the exits
            sources = {source for source, target, direction in my_edges}
            exits = {
                target
                for source, target, direction in my_edges
                if target not in sources
            }

            if len(exits) == 0:
                return False

            # remove the exits
            new_edges = [
                (source, target, direction)
                for source, target, direction in my_edges
                if target not in exits
            ]
            my_edges = new_edges
        return True

    def get_entry_points(self):
        """
        Get nodes in the Graph with no incoming edges.
        """
        if len(self._nodes) == 1:
            return list(self._nodes.keys())
        targets = {target for source, target, direction in self.edges()}
        retval = (
            source
            for source, target, direction in self.edges()
            if source not in targets
        )
        return sorted(retval)

    def get_exit_points(self):
        """
        Get nodes in the Graph with no outgoing edges.
        """
        if len(self._nodes) == 1:  # pragma: no cover
            return list(self._nodes.keys())
        sources = self._edges.keys()
        retval = (
            target
            for source, target, direction in self.edges()
            if target not in sources
        )
        return sorted(retval)

    def remove_node(self, nid, heal: bool = False):
        """
        Remove a node.

        Parameters:
            heal: boolean
                Join the incoming and outgoing connections for the removed node
                to each other to keep the Graph intact
        """

        # remove the node
        self._nodes.pop(nid, None)

        if heal:
            # link the nodes each side of the node being removed
            out_going = self.outgoing_edges(nid)
            in_coming = self.ingoing_edges(nid)
            for out_nid in out_going:
                for in_nid in in_coming:
                    self.add_edge(in_nid[0], out_nid, in_nid[1])  # type:ignore

            self._edges = [
                (source, target, direction)
                for source, target, direction in self._edges
                if nid not in (source, target)
            ]

    def insert_node_before(self, nid, operator, before_nid):
        """rewrite the plan putting the new node before a given node"""
        # add the new node to the plan
        self.add_operator(nid, operator)
        # change all the edges that were going into the old nid to the new one
        self._edges = [
            (source, target if target != before_nid else nid, direction)
            for source, target, direction in self._edges
        ]
        # add an edge from the new nid to the old one
        self.add_edge(nid, before_nid)

    def insert_node_after(self, nid, operator, after_nid):
        """rewrite the plan putting the new node after a given node"""
        # add the new node to the plan
        self.add_operator(nid, operator)
        # change all the edges that were coming from the old nid to the new one
        self._edges = [
            (source if source != after_nid else nid, target, direction)
            for source, target, direction in self._edges
        ]
        # add an edge from the new nid to the old one
        self.add_edge(after_nid, nid)

    def copy(self):
        g = Graph()
        g._nodes = self._nodes.copy()
        g._edges = self._edges.copy()
        return g

    def to_networkx(self):
        """
        Convert a travers graph to a NetworkX graph
        """
        try:
            import networkx as nx  # type:ignore
        except ImportError:  # pragma: no cover
            raise MissingDependencyError(
                "`networx` is missing, please install or include in requirements.txt"
            )

        g = nx.DiGraph()
        for s, t, r in self.edges():
            g.add_edge(s, t, relationship=r)
        for node, attribs in self.nodes(True):
            g.add_node(node, **attribs)
        return g

    def epitomize(self):
        """
        Summarize a Graph by reducing to only the node_types and relationships
        """
        g = Graph()
        for s, t, r in self.edges():
            node1 = self[s]
            node2 = self[t]
            if node1 and node2:
                g.add_edge(node1.get("node_type"), node2.get("node_type"), r)
            if node1:
                g.add_node(
                    node1.get("node_type"), {"node_type": node1.get("node_type")}
                )
            if node2:
                g.add_node(
                    node2.get("node_type"), {"node_type": node2.get("node_type")}
                )
        return g

    def __repr__(self):
        return (
            f"Graph - {len(list(self.nodes()))} nodes, {len(list(self.edges()))} edges"
        )

    def __len__(self):
        return len(list(self.nodes()))

    def __getitem__(self, nid):
        return self._nodes.get(nid, {})