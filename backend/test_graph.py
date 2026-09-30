import asyncio
from graph.neo4j_client import neo4j_client

async def test():
    await neo4j_client.connect()
    graph = await neo4j_client.get_full_graph(limit=100)
    node_count = len(graph["nodes"])
    edge_count = len(graph["edges"])
    print(f'Nodes: {node_count}')
    print(f'Edges: {edge_count}')
    print('Sample nodes:')
    for n in graph["nodes"][:5]:
        print(f'  - {n}')
    print('Sample edges:')
    for e in graph["edges"][:5]:
        print(f'  - {e}')
    await neo4j_client.close()

asyncio.run(test())
