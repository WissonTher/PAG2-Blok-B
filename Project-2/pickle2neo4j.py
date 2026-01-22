import pickle
from neo4j import GraphDatabase, basic_auth

with open('szy_wierzcholki.pickle', 'rb') as f:
    nodes = pickle.load(f)
with open('szy_lista_sasiedztwa.pickle', 'rb') as f:
    adj = pickle.load(f)

driver = GraphDatabase.driver(
    "bolt://3.239.108.52:7687",
    auth=basic_auth("neo4j", "fireballs-enemies-print")
)

with driver.session() as session:
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Point) REQUIRE p.id IS UNIQUE")

    nodedict = [
        {'id': int(node_id), 'x': float(x), 'y': float(y)}
        for node_id, (x, y, kod) in nodes.items()
    ]

    for i in range(0, len(nodedict), 5000):
        batch = nodedict[i:i + 5000]
        session.run("""
            UNWIND $batch AS row
            CREATE (:Point {id: row.id, x: row.x, y: row.y})
        """, batch=batch)

    edgesdict = []
    for start_node, sasiad_list in adj.items():
        for sasiad in sasiad_list:
            end_node, dist, time, edge_id = sasiad
            edgesdict.append({
                'u': int(start_node),
                'v': int(end_node),
                'dist': float(dist),
                'time': float(time)
            })

    for i in range(0, len(edgesdict), 2000):
        batch = edgesdict[i:i + 2000]
        session.run("""
            UNWIND $batch AS row
            MATCH (u:Point {id: row.u})
            MATCH (v:Point {id: row.v})
            CREATE (u)-[:ROAD {time: row.time, distance: row.dist}]->(v)
            CREATE (v)-[:ROAD {time: row.time, distance: row.dist}]->(u)
        """, batch=batch)

driver.close()
