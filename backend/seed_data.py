"""
Seed script to populate CrimNet with sample cases, persons, and relationships.
Run from backend directory: python seed_data.py
"""

import asyncio
import uuid
from datetime import datetime
from graph.neo4j_client import neo4j_client

async def seed_data():
    """Populate database with sample criminal network data."""
    
    print("🌱 Seeding CrimNet database...")
    
    # ─── Sample Persons ───────────────────────────────────────────────────────
    persons = [
        {
            "id": str(uuid.uuid4()),
            "name": "Marcus Torres",
            "role": "Drug Kingpin",
            "status": "ACTIVE",
            "aliases": ["El Padrino", "MT"],
            "location": "Miami, FL",
            "risk_level": "CRITICAL",
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Elena Rossi",
            "role": "Money Launderer",
            "status": "ACTIVE",
            "aliases": ["ER", "The Accountant"],
            "location": "New York, NY",
            "risk_level": "HIGH",
        },
        {
            "id": str(uuid.uuid4()),
            "name": "James Chen",
            "role": "Distributor",
            "status": "ACTIVE",
            "aliases": ["JC", "Chen"],
            "location": "Los Angeles, CA",
            "risk_level": "HIGH",
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Viktor Sokolov",
            "role": "Enforcer",
            "status": "INACTIVE",
            "aliases": ["Big V", "Sokolov"],
            "location": "Chicago, IL",
            "risk_level": "CRITICAL",
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Sophia Mendez",
            "role": "Courier",
            "status": "ACTIVE",
            "aliases": ["Soph", "SM"],
            "location": "Miami, FL",
            "risk_level": "MEDIUM",
        },
    ]
    
    # ─── Sample Organizations ─────────────────────────────────────────────────
    orgs = [
        {
            "id": str(uuid.uuid4()),
            "name": "Torres Cartel",
            "type": "CRIMINAL_GROUP",
            "status": "ACTIVE",
            "description": "Major international drug trafficking organization",
            "location": "Miami, FL",
            "size": 150,
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Eastern European Syndicate",
            "type": "CRIMINAL_GROUP",
            "status": "ACTIVE",
            "description": "Human trafficking and weapons smuggling",
            "location": "Chicago, IL",
            "size": 80,
        },
    ]
    
    # Create persons
    print(f"  Adding {len(persons)} persons...")
    for person in persons:
        await neo4j_client.upsert_entity("Person", person)
    
    # Create organizations
    print(f"  Adding {len(orgs)} organizations...")
    for org in orgs:
        await neo4j_client.upsert_entity("Organization", org)
    
    # ─── Create Relationships ─────────────────────────────────────────────────
    print("  Creating relationships...")
    
    # Marcus Torres (boss) -> Elena Rossi (money launderer)
    await neo4j_client.run(
        """
        MATCH (m:Person {name: 'Marcus Torres'}), (e:Person {name: 'Elena Rossi'})
        MERGE (m)-[r:EMPLOYS {role: 'Financial Operator', since: '2018-01-15'}]->(e)
        """,
    )
    
    # Marcus Torres -> James Chen (distributor)
    await neo4j_client.run(
        """
        MATCH (m:Person {name: 'Marcus Torres'}), (j:Person {name: 'James Chen'})
        MERGE (m)-[r:EMPLOYS {role: 'West Coast Distributor', since: '2019-06-10'}]->(j)
        """,
    )
    
    # Marcus Torres -> Sophia Mendez (courier)
    await neo4j_client.run(
        """
        MATCH (m:Person {name: 'Marcus Torres'}), (s:Person {name: 'Sophia Mendez'})
        MERGE (m)-[r:EMPLOYS {role: 'Courier', since: '2022-03-01'}]->(s)
        """,
    )
    
    # James Chen -> Sophia Mendez (works with)
    await neo4j_client.run(
        """
        MATCH (j:Person {name: 'James Chen'}), (s:Person {name: 'Sophia Mendez'})
        MERGE (j)-[r:COLLABORATES_WITH {type: 'Distribution Network', since: '2022-05-12'}]->(s)
        """,
    )
    
    # Viktor Sokolov -> Eastern European Syndicate (member)
    await neo4j_client.run(
        """
        MATCH (v:Person {name: 'Viktor Sokolov'}), (o:Organization {name: 'Eastern European Syndicate'})
        MERGE (v)-[r:MEMBER_OF {rank: 'Enforcer', joined: '2015-08-20'}]->(o)
        """,
    )
    
    # Marcus Torres -> Torres Cartel (leads)
    await neo4j_client.run(
        """
        MATCH (m:Person {name: 'Marcus Torres'}), (o:Organization {name: 'Torres Cartel'})
        MERGE (m)-[r:LEADS {since: '2010-01-01', role: 'Boss'}]->(o)
        """,
    )
    
    # ─── Sample Cases ────────────────────────────────────────────────────────
    cases = [
        {
            "id": str(uuid.uuid4()),
            "name": "Operation Apex",
            "description": "Investigation into Torres Cartel drug trafficking network across North America",
            "status": "OPEN",
            "priority": "CRITICAL",
            "assigned_to": "Special Agent Williams",
            "tags": ["NARCOTICS", "TRAFFICKING", "ORGANIZED_CRIME"],
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Operation Exodus",
            "description": "Financial crimes investigation targeting money laundering operations",
            "status": "OPEN",
            "priority": "HIGH",
            "assigned_to": "Special Agent Chen",
            "tags": ["MONEY_LAUNDERING", "FINANCIAL_CRIME", "WHITE_COLLAR"],
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Operation Ghost Protocol",
            "description": "Surveillance and intelligence gathering on Eastern European Syndicate",
            "status": "ACTIVE",
            "priority": "CRITICAL",
            "assigned_to": "Detective Rodriguez",
            "tags": ["HUMAN_TRAFFICKING", "WEAPONS_SMUGGLING", "INTERNATIONAL"],
        },
    ]
    
    print(f"  Adding {len(cases)} cases...")
    for case in cases:
        await neo4j_client.upsert_entity("Case", case)
    
    # ─── Link Persons to Cases ───────────────────────────────────────────────
    print("  Linking entities to cases...")
    
    # Operation Apex: Marcus Torres, Elena Rossi, James Chen, Sophia Mendez
    for name in ["Marcus Torres", "Elena Rossi", "James Chen", "Sophia Mendez"]:
        await neo4j_client.run(
            """
            MATCH (c:Case {name: 'Operation Apex'}), (p:Person {name: $name})
            MERGE (c)-[r:INCLUDES]->(p)
            """,
            {"name": name},
        )
    
    # Operation Exodus: Elena Rossi, Torres Cartel
    await neo4j_client.run(
        """
        MATCH (c:Case {name: 'Operation Exodus'}), (p:Person {name: 'Elena Rossi'})
        MERGE (c)-[r:INCLUDES]->(p)
        """,
    )
    
    await neo4j_client.run(
        """
        MATCH (c:Case {name: 'Operation Exodus'}), (o:Organization {name: 'Torres Cartel'})
        MERGE (c)-[r:INCLUDES]->(o)
        """,
    )
    
    # Operation Ghost Protocol: Viktor Sokolov, Eastern European Syndicate
    await neo4j_client.run(
        """
        MATCH (c:Case {name: 'Operation Ghost Protocol'}), (p:Person {name: 'Viktor Sokolov'})
        MERGE (c)-[r:INCLUDES]->(p)
        """,
    )
    
    await neo4j_client.run(
        """
        MATCH (c:Case {name: 'Operation Ghost Protocol'}), (o:Organization {name: 'Eastern European Syndicate'})
        MERGE (c)-[r:INCLUDES]->(o)
        """,
    )
    
    print("✅ Seeding complete!")
    print(f"  • {len(persons)} persons")
    print(f"  • {len(orgs)} organizations")
    print(f"  • {len(cases)} cases")
    print(f"  • Multiple relationships and case linkages")
    

if __name__ == "__main__":
    from config import settings
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    # Initialize Neo4j client
    async def init_and_seed():
        await neo4j_client.connect()
        await seed_data()
        await neo4j_client.close()
    
    asyncio.run(init_and_seed())
