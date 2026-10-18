
"""
TraceShield AI - Operational Context Seeder

Adds project and team ownership relationships to FalkorDB.

Graph relationships:
    Project --CONTAINS--> Website
    Project --CONTAINS--> Service
    Team    --OWNS-----> Website
    Team    --OWNS-----> Service

Safe to run repeatedly because MERGE prevents duplicate
nodes and relationships with the same identifiers.
"""

from graph_db import get_graph


def seed_operational_context():
    graph = get_graph()

    # Step 1: Create the project node
    graph.query("""
        MERGE (p:Project {id: 'demoshop-project'})
        SET p.name = 'DemoShop Security Demo',
            p.environment = 'local-only'
    """)

    # Step 2: Create the Commerce Backend team
    graph.query("""
        MERGE (t:Team {id: 'commerce-backend'})
        SET t.name = 'Commerce Backend'
    """)

    # Step 3: Create the Web Platform team
    graph.query("""
        MERGE (t:Team {id: 'web-platform'})
        SET t.name = 'Web Platform'
    """)

    # Step 4: Connect the project and Web Platform
    # team to the DemoShop website.
    graph.query("""
        MATCH (p:Project {id: 'demoshop-project'})
        MATCH (t:Team {id: 'web-platform'})
        MATCH (w:Website)
        WHERE w.name = 'DemoShop'
           OR w.id = 'shop-demo'

        MERGE (p)-[:CONTAINS]->(w)
        MERGE (t)-[:OWNS]->(w)
    """)

    # Step 5: Connect the project and Commerce Backend
    # team to the Orders Service.
    graph.query("""
        MATCH (p:Project {id: 'demoshop-project'})
        MATCH (t:Team {id: 'commerce-backend'})
        MATCH (s:Service)
        WHERE s.name = 'Orders Service'
           OR s.id = 'orders'

        MERGE (p)-[:CONTAINS]->(s)
        MERGE (t)-[:OWNS]->(s)
    """)

    # Step 6: Verify seeded nodes
    projects = graph.ro_query("""
        MATCH (p:Project {id: 'demoshop-project'})
        RETURN p.name
    """).result_set

    teams = graph.ro_query("""
        MATCH (t:Team)
        WHERE t.id IN ['commerce-backend', 'web-platform']
        RETURN t.name
        ORDER BY t.name
    """).result_set

    ownership = graph.ro_query("""
        MATCH (t:Team)-[:OWNS]->(asset)
        RETURN t.name, labels(asset), asset.name
    """).result_set

    return {
        "status": "success",
        "project": projects[0][0] if projects else None,
        "teams": [row[0] for row in teams],
        "ownership": [
            {
                "team": row[0],
                "asset_type": row[1],
                "asset": row[2]
            }
            for row in ownership
        ],
        "note": "Synthetic ownership metadata for local DemoShop."
    }


if __name__ == "__main__":
    import json

    try:
        result = seed_operational_context()
        print(json.dumps(result, indent=2))

    except Exception as error:
        print(f"[ERROR] Failed to seed operational context: {error}")
        raise
