"""
scripts/seed_demo_data.py — Generates realistic synthetic criminal network data
for demonstration purposes.

Creates:
  - ~50 Person nodes across 4 criminal communities
  - Organisations, Locations, Phones, Vehicles, BankAccounts
  - CDR-style phone calls, financial transfers, surveillance sightings
  - FIR-style text documents for NLP testing

Usage (from project root):
  python scripts/seed_demo_data.py
"""

import asyncio
import uuid
import random
from datetime import datetime, timedelta, timezone

# ── Insert project root on path so backend modules are importable ─────────────
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from config import settings
from graph.neo4j_client import neo4j_client

# ── Seed Data ─────────────────────────────────────────────────────────────────

PERSONS = [
    # Community 0 — Mumbai drug syndicate
    {"name": "Rajan Sharma",    "community": 0, "role": "kingpin"},
    {"name": "Priya Desai",     "community": 0, "role": "handler"},
    {"name": "Mohan Pillai",    "community": 0, "role": "courier"},
    {"name": "Sunita Rao",      "community": 0, "role": "associate"},
    {"name": "Vikram Nair",     "community": 0, "role": "associate"},
    {"name": "Deepa Menon",     "community": 0, "role": "associate"},
    {"name": "Arun Kumar",      "community": 0, "role": "courier"},
    {"name": "Leela Iyer",      "community": 0, "role": "associate"},
    {"name": "Ramesh Gupta",    "community": 0, "role": "broker"},
    {"name": "Anita Joshi",     "community": 0, "role": "associate"},
    # Community 1 — Delhi extortion gang
    {"name": "Abdul Karim",     "community": 1, "role": "kingpin"},
    {"name": "Salim Khan",      "community": 1, "role": "enforcer"},
    {"name": "Mumtaz Ansari",   "community": 1, "role": "associate"},
    {"name": "Farhan Sheikh",   "community": 1, "role": "broker"},
    {"name": "Nasreen Begum",   "community": 1, "role": "associate"},
    {"name": "Irfan Qureshi",   "community": 1, "role": "associate"},
    {"name": "Zaid Hussain",    "community": 1, "role": "courier"},
    {"name": "Rashida Bano",    "community": 1, "role": "associate"},
    {"name": "Tahir Malik",     "community": 1, "role": "enforcer"},
    {"name": "Hina Siddiqui",   "community": 1, "role": "associate"},
    # Community 2 — Punjab hawala network
    {"name": "Gurpreet Singh",  "community": 2, "role": "kingpin"},
    {"name": "Harpreet Kaur",   "community": 2, "role": "handler"},
    {"name": "Balvinder Pal",   "community": 2, "role": "hawala"},
    {"name": "Manpreet Brar",   "community": 2, "role": "associate"},
    {"name": "Simranjit Mann",  "community": 2, "role": "associate"},
    {"name": "Jaspreet Gill",   "community": 2, "role": "courier"},
    {"name": "Navneet Dhaliwal","community": 2, "role": "associate"},
    {"name": "Kuldeep Sandhu",  "community": 2, "role": "enforcer"},
    {"name": "Amarjot Sekhon",  "community": 2, "role": "associate"},
    {"name": "Daljeet Virk",    "community": 2, "role": "associate"},
    # Community 3 — Hyderabad cybercrime cell
    {"name": "Kiran Reddy",     "community": 3, "role": "kingpin"},
    {"name": "Srinivas Rao",    "community": 3, "role": "techie"},
    {"name": "Padmavathi Devi", "community": 3, "role": "associate"},
    {"name": "Venkatesh Babu",  "community": 3, "role": "mule"},
    {"name": "Lalitha Krishna", "community": 3, "role": "associate"},
    {"name": "Mahesh Naidu",    "community": 3, "role": "techie"},
    {"name": "Swathi Varma",    "community": 3, "role": "associate"},
    {"name": "Ravi Chandra",    "community": 3, "role": "enforcer"},
    {"name": "Surekha Rao",     "community": 3, "role": "associate"},
    {"name": "Gopi Krishna",    "community": 3, "role": "associate"},
]

ORGS = [
    {"name": "Galaxy Trading Co.",   "community": 0, "type": "shell_company"},
    {"name": "Mumbai Bhai Network",  "community": 0, "type": "gang"},
    {"name": "Capital Builders Ltd", "community": 1, "type": "shell_company"},
    {"name": "Delhi Daggers",        "community": 1, "type": "gang"},
    {"name": "Punjab Hawala House",  "community": 2, "type": "hawala"},
    {"name": "Golden Star Exports",  "community": 2, "type": "shell_company"},
    {"name": "TechFraud Solutions",  "community": 3, "type": "cybercrime"},
    {"name": "Hyderabad Syndicate",  "community": 3, "type": "gang"},
]

LOCATIONS = [
    {"name": "Dharavi, Mumbai",           "city": "Mumbai",    "type": "meeting_point"},
    {"name": "Kurla West Warehouse",      "city": "Mumbai",    "type": "storage"},
    {"name": "Andheri Safe House",        "city": "Mumbai",    "type": "residence"},
    {"name": "Old Delhi Market",          "city": "Delhi",     "type": "meeting_point"},
    {"name": "Jahangirpuri Area",         "city": "Delhi",     "type": "crime_scene"},
    {"name": "Azadpur Mandi",             "city": "Delhi",     "type": "meeting_point"},
    {"name": "Amritsar Border Zone",      "city": "Amritsar",  "type": "transit"},
    {"name": "Ludhiana Industrial Area",  "city": "Ludhiana",  "type": "storage"},
    {"name": "Chandigarh Safe House",     "city": "Chandigarh","type": "residence"},
    {"name": "Hitec City Cafe",           "city": "Hyderabad", "type": "meeting_point"},
    {"name": "Secunderabad Station",      "city": "Hyderabad", "type": "transit"},
    {"name": "Kukatpally Apartment",      "city": "Hyderabad", "type": "residence"},
]

COMMUNITY_ORGS    = {0: "Mumbai Bhai Network", 1: "Delhi Daggers", 2: "Punjab Hawala House", 3: "TechFraud Solutions"}
COMMUNITY_LOCS    = {0: [0, 1, 2], 1: [3, 4, 5], 2: [6, 7, 8], 3: [9, 10, 11]}
CROSS_COMM_PAIRS  = [(0, 1), (1, 2), (2, 3), (0, 3)]   # Inter-community broker edges


def random_phone():
    return f"9{random.randint(100000000, 999999999)}"


def random_account():
    return f"{random.randint(10000000000, 99999999999)}"


def random_plate():
    states = ["MH", "DL", "PB", "TS", "KA", "GJ"]
    st = random.choice(states)
    return f"{st}{random.randint(1, 99):02d}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.randint(1000, 9999)}"


def rand_ts(days_back=180):
    base = datetime.now(tz=timezone.utc) - timedelta(days=days_back)
    return (base + timedelta(seconds=random.randint(0, days_back * 86400))).isoformat()


# ── Core seeder ───────────────────────────────────────────────────────────────

async def seed():
    print("🌱 Connecting to Neo4j…")
    await neo4j_client.connect()
    await neo4j_client.init_constraints()

    print("🧹 Clearing existing demo data…")
    await neo4j_client.run("MATCH (n) DETACH DELETE n")

    id_map = {}   # name → neo4j_id

    # ── 1. Person nodes ───────────────────────────────────────────────────────
    print(f"👤 Creating {len(PERSONS)} person nodes…")
    for p in PERSONS:
        pid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Person:{p['name']}"))
        await neo4j_client.upsert_entity("Person", {
            "id":              pid,
            "name":            p["name"],
            "role":            p["role"],
            "community_id":    p["community"],
            "phone_number":    random_phone(),
            "source_documents":["seed_data"],
            "criminal_history":["FIR 2022", "FIR 2023"] if p["role"] == "kingpin" else [],
        })
        id_map[p["name"]] = pid

    # ── 2. Organisation nodes ─────────────────────────────────────────────────
    print(f"🏢 Creating {len(ORGS)} organisation nodes…")
    for o in ORGS:
        oid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Org:{o['name']}"))
        await neo4j_client.upsert_entity("Organization", {
            "id":   oid, "name": o["name"],
            "org_type": o["type"], "community_id": o["community"],
            "source_documents": ["seed_data"],
        })
        id_map[o["name"]] = oid

    # ── 3. Location nodes ─────────────────────────────────────────────────────
    print(f"📍 Creating {len(LOCATIONS)} location nodes…")
    for loc in LOCATIONS:
        lid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Loc:{loc['name']}"))
        await neo4j_client.upsert_entity("Location", {
            "id": lid, "name": loc["name"],
            "city": loc["city"], "location_type": loc["type"],
            "source_documents": ["seed_data"],
        })
        id_map[loc["name"]] = lid

    # ── 4. Phone & Bank Account nodes ─────────────────────────────────────────
    print("📱 Creating phone & bank account nodes…")
    for p in PERSONS:
        phone = random_phone()
        phid  = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Phone:{phone}"))
        await neo4j_client.upsert_entity("PhoneNumber", {
            "id": phid, "name": phone, "number": phone, "source_documents": ["seed_data"],
        })
        id_map[f"phone_{p['name']}"] = phid
        await neo4j_client.upsert_relationship(id_map[p["name"]], phid, "USES")

        acct = random_account()
        acid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Account:{acct}"))
        await neo4j_client.upsert_entity("BankAccount", {
            "id": acid, "name": acct, "account_number": acct,
            "bank_name": random.choice(["SBI", "HDFC", "ICICI", "PNB", "Axis"]),
            "source_documents": ["seed_data"],
        })
        id_map[f"acct_{p['name']}"] = acid
        await neo4j_client.upsert_relationship(id_map[p["name"]], acid, "OWNS")

    # ── 5. Vehicle nodes ──────────────────────────────────────────────────────
    print("🚗 Creating vehicle nodes…")
    for p in PERSONS[:20]:  # subset owns vehicles
        plate = random_plate()
        vid   = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Veh:{plate}"))
        await neo4j_client.upsert_entity("Vehicle", {
            "id": vid, "name": plate, "plate_number": plate,
            "vehicle_type": random.choice(["Car", "Motorcycle", "Truck", "SUV"]),
            "color": random.choice(["Black", "White", "Silver", "Red"]),
            "source_documents": ["seed_data"],
        })
        await neo4j_client.upsert_relationship(id_map[p["name"]], vid, "OWNS")

    # ── 6. Intra-community relationships (MEMBER_OF + ASSOCIATED_WITH) ────────
    print("🔗 Building intra-community relationships…")
    for p in PERSONS:
        org_name = COMMUNITY_ORGS.get(p["community"])
        if org_name and org_name in id_map:
            await neo4j_client.upsert_relationship(id_map[p["name"]], id_map[org_name], "MEMBER_OF")
        # Random associations within same community
        peers = [x for x in PERSONS if x["community"] == p["community"] and x["name"] != p["name"]]
        for peer in random.sample(peers, min(3, len(peers))):
            await neo4j_client.upsert_relationship(
                id_map[p["name"]], id_map[peer["name"]], "ASSOCIATED_WITH",
                {"timestamp": rand_ts(), "source_doc": "seed_data"},
            )

    # ── 7. Inter-community BROKER edges ──────────────────────────────────────
    print("🌉 Building cross-community broker edges…")
    for c1, c2 in CROSS_COMM_PAIRS:
        broker1 = next(p for p in PERSONS if p["community"] == c1 and p["role"] in ("broker", "kingpin"))
        broker2 = next(p for p in PERSONS if p["community"] == c2 and p["role"] in ("broker", "kingpin"))
        await neo4j_client.upsert_relationship(
            id_map[broker1["name"]], id_map[broker2["name"]], "ASSOCIATED_WITH",
            {"timestamp": rand_ts(), "type": "inter_community", "source_doc": "seed_data"},
        )

    # ── 8. CALLED relationships (CDR simulation) ──────────────────────────────
    print("📞 Simulating 300 CDR call records…")
    for _ in range(300):
        caller  = random.choice(PERSONS)
        callee  = random.choice(PERSONS)
        if caller["name"] == callee["name"]:
            continue
        src_phone = id_map.get(f"phone_{caller['name']}")
        tgt_phone = id_map.get(f"phone_{callee['name']}")
        if src_phone and tgt_phone:
            await neo4j_client.upsert_relationship(
                src_phone, tgt_phone, "CALLED",
                {"timestamp": rand_ts(), "duration_sec": random.randint(30, 600),
                 "tower_location": random.choice(LOCATIONS)["city"], "source_doc": "CDR_seed"},
            )

    # ── 9. TRANSFERRED_TO relationships (financial) ───────────────────────────
    print("💰 Simulating 150 financial transactions…")
    for _ in range(150):
        sender   = random.choice(PERSONS)
        receiver = random.choice(PERSONS)
        if sender["name"] == receiver["name"]:
            continue
        src_acct = id_map.get(f"acct_{sender['name']}")
        tgt_acct = id_map.get(f"acct_{receiver['name']}")
        if src_acct and tgt_acct:
            amount = random.choice([10000, 25000, 50000, 100000, 500000]) + random.randint(0, 999)
            await neo4j_client.upsert_relationship(
                src_acct, tgt_acct, "TRANSFERRED_TO",
                {"amount": amount, "timestamp": rand_ts(),
                 "suspicious": amount >= 50000, "source_doc": "FINANCIAL_seed"},
            )

    # ── 10. PRESENT_AT relationships (surveillance) ───────────────────────────
    print("📍 Adding 200 surveillance sighting records…")
    for _ in range(200):
        person   = random.choice(PERSONS)
        comm_locs = COMMUNITY_LOCS.get(person["community"], [0])
        loc_idx  = random.choice(comm_locs)
        loc_name = LOCATIONS[loc_idx]["name"]
        if loc_name in id_map:
            await neo4j_client.upsert_relationship(
                id_map[person["name"]], id_map[loc_name], "PRESENT_AT",
                {"timestamp": rand_ts(), "source_doc": "SURVEILLANCE_seed"},
            )

    # ── 11. CO_ACCUSED_IN events ──────────────────────────────────────────────
    print("⚖️  Creating FIR/case events…")
    for community in range(4):
        fir_id = str(uuid.uuid4())
        fir_name = f"FIR {random.randint(100, 999)}/2024"
        await neo4j_client.upsert_entity("Event", {
            "id": fir_id, "name": fir_name, "event_type": "FIR",
            "fir_number": fir_name, "community_id": community,
            "source_documents": ["seed_data"],
        })
        id_map[fir_name] = fir_id
        accused = [p for p in PERSONS if p["community"] == community]
        for p in accused[:random.randint(2, 5)]:
            await neo4j_client.upsert_relationship(
                id_map[p["name"]], fir_id, "CO_ACCUSED_IN",
                {"timestamp": rand_ts(), "source_doc": "FIR_seed"},
            )

    # ── Summary ───────────────────────────────────────────────────────────────
    stats = await neo4j_client.run("MATCH (n) RETURN count(n) AS nodes")
    edges = await neo4j_client.run("MATCH ()-[r]->() RETURN count(r) AS edges")
    print(f"\n✅ Seed complete!")
    print(f"   Nodes: {stats[0]['nodes']}")
    print(f"   Edges: {edges[0]['edges']}")
    print("\n👉 Next: open the dashboard and click 'Run Analytics' to compute centrality + communities.")
    await neo4j_client.close()


if __name__ == "__main__":
    asyncio.run(seed())
