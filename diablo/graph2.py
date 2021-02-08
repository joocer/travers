class Graph(object):

    __slots__ = ('_nodes', '_edges')

    def __init__(self):
        self._nodes = {}
        self._edges = {}

    def _make_a_list(self, obj):
        if isinstance(obj, list):
            return obj
        return [obj]

    def load_graphml(self, xml_file):
        import xmltodict

        # load the file into a dom
        with open(xml_file, 'r') as fd:
            xml_dom = xmltodict.parse(fd.read())

        # load the keys
        keys = {}
        for key in xml_dom['graphml'].get('key', {}):
            keys[key['@id']] = key['@attr.name']

        # load the nodes
        index = -1
        for index, node in enumerate(xml_dom['graphml']['graph'].get('node', {})):
            data = {}
            for key in self._make_a_list(node.get('data', {})):
                data[keys[key['@key']]] = key['#text']
            self._nodes[node.get('@id')] = data

        # load the edges
        index = -1
        for index, edge in enumerate(xml_dom['graphml']['graph'].get('edge', {})):
            source = edge['@source']
            target = edge['@target']
            relationship = self._edges.get(edge['data'].get('#text'), [])
            relationship.append((source, target))
            self._edges[edge['data'].get('#text')] = relationship

    def load(self, json_file):
        import ujson as json
        reader = inner_file_reader(json_file)
        for row in reader:
            record = json.loads(row)
            if record['type'] == 'node':
                self._nodes[record['id']] = record['attributes']
            if record['type'] == 'edge':
                relationship = self._edges.get(record['relationship'], [])
                relationship.append((record['source'], record['target']))
                self._edges[record['relationship']] = relationship

    def save(self, json_file):
        import ujson as json
        with open(json_file, 'w') as json_file:
            for node_id, attribs in self.nodes(data=True):
                record = {
                        'type': 'node',
                        'id': node_id,
                        'attributes': attribs
                    }
                json_file.write(json.dumps(record) + '\n')
            for relationship, edges in self._edges.items():
                for source, target in edges:
                    record = {
                            'type': 'edge',
                            'source': source,
                            'target': target,
                            'relationship': relationship
                        }
                    json_file.write(json.dumps(record) + '\n')

    def add_edge(self, source, target, relationship):
        # add the edge to the doc, if the node doesn't exist create it
        rel = self._edges.get(relationship, [])
        rel.append((source, target))
        self._edges[relationship] = rel

    def remove_edge(self, source, target):
        edge = (source, target)
        for rel in self._edges:
            if edge in self._edges[rel]:
                self._edges[rel].remove(edge)
                return True
        return False

    def add_node(self, node_id, **kwargs):
        self._nodes[node_id] = kwargs

    def remove_node(self, node_id):
        try:
            del self._nodes[node_id]
            return True
        except:
            return False

    def nodes(self, data=False):
        if data:
            return [(ids, details) for ids, details in self._nodes.items()]
        return [ids for ids, details in self._nodes.items()]

    def edges(self):
        result = []
        for rel in self._edges:
            result += self._edges[rel]
        return result

    def copy(self):
        new_graph = Graph()
        new_graph._edges = self._edges.copy()
        new_graph._nodes = self._nodes.copy()
        return new_graph

    def walk_tree(
            self,
            source: str,
            depth: int = 5):
        sources = set([source])
        loops = 0

        visited_edges = []
        while loops <= depth:
            cycle_visited_edges = []
            for rel in self._edges:
                cycle_visited_edges += [(s, t, rel) for (s, t) in self._edges[rel] if s in sources]
            sources = {t for (s, t, r) in visited_edges}
            visited_edges += cycle_visited_edges
            loops += 1

        # select the nodes associated with the edges
        # return a graph
        return visited_edges

def inner_file_reader(
        file_name: str,
        chunk_size: int = 64*1024*1024,
        delimiter: str = "\n"):
    """
    This is the guts of the reader - it opens a file and reads through it
    chunk by chunk. This allows huge files to be processed as only a chunk
    at a time is in memory.
    """
    with open(file_name, 'r', encoding="utf8") as f:
        carry_forward = ""
        chunk = "INITIALIZED"
        while len(chunk) > 0:
            chunk = f.read(chunk_size)
            augmented_chunk = carry_forward + chunk
            lines = augmented_chunk.split(delimiter)
            carry_forward = lines.pop()
            yield from lines
        if carry_forward:
            yield carry_forward

if __name__ == "__main__":

    from pprint import pprint

    g = Graph()
#    g.add_node('abc', variable=123)
#    g.add_edge('a', 'b', relationship=456)
#    g.add_node('a', variable=789)
    g.load_graphml(r'graph/mitre-data.graphml')

#    g.load('test2.jsonl')

    #g.remove_edge('ASVS-14.5.4', 'CWE-306')
    #g.remove_node('ASVS-14.5.4')

    s = g.walk_tree('ASVS-14.5.4', 2)
    print(s)

    #pprint(g.nodes())
    #pprint(g.edges())

#    print(type(g._nodes['a']))

    g.save(r'graph/mitre-graph2.jsonl')