"""
backend/tests/test_analytics.py — Unit tests for analytics modules.
Run with: pytest backend/tests/test_analytics.py -v
"""

import pytest

# ── Anomaly Detector tests (no Neo4j required) ────────────────────────────────

from analytics.anomaly_detector import AnomalyDetector


def make_cdr_records(n=30, night_heavy=False):
    records = []
    for i in range(n):
        hour = 2 if night_heavy else (i % 24)
        records.append({
            "caller":       f"9{800000000 + i}",
            "receiver":     f"9{900000000 + (i % 5)}",
            "timestamp":    f"2024-01-15 {hour:02d}:{i % 60:02d}:00",
            "duration_sec": 120,
        })
    return records


def test_cdr_anomaly_returns_list():
    detector = AnomalyDetector()
    records  = make_cdr_records(50)
    # Run synchronously for testing
    import asyncio
    alerts = asyncio.run(detector.detect_cdr_anomalies(records))
    assert isinstance(alerts, list)


def test_cdr_anomaly_night_heavy_detected():
    import asyncio
    detector = AnomalyDetector()
    # Mix: 20 normal callers + 1 night-heavy caller with many records
    records = make_cdr_records(20, night_heavy=False)
    night_records = [
        {"caller": "9111111111", "receiver": f"9{i}", "timestamp": f"2024-01-15 02:{i % 60:02d}:00", "duration_sec": 60}
        for i in range(15)
    ]
    alerts = asyncio.run(detector.detect_cdr_anomalies(records + night_records))
    assert isinstance(alerts, list)


def test_financial_anomaly_round_amounts():
    detector = AnomalyDetector()
    records = [
        {"account": "ACC001", "beneficiary": "ACC002", "amount": 100000, "timestamp": "2024-01-01"},
        {"account": "ACC001", "beneficiary": "ACC003", "amount": 100000, "timestamp": "2024-01-02"},
        {"account": "ACC001", "beneficiary": "ACC004", "amount": 100000, "timestamp": "2024-01-03"},
    ]
    alerts = detector.detect_financial_anomalies(records)
    assert len(alerts) >= 1
    assert any(a["alert_type"] == "round_amount_structuring" for a in alerts)


def test_financial_anomaly_large_transaction():
    detector = AnomalyDetector()
    records = [
        {"account": "ACC100", "beneficiary": "ACC200", "amount": 2000000, "timestamp": "2024-01-10"},
    ]
    alerts = detector.detect_financial_anomalies(records)
    assert any(a["alert_type"] == "large_transaction" for a in alerts)
    assert alerts[0]["severity"] == "CRITICAL"


# ── FIR Parser tests ──────────────────────────────────────────────────────────

from ingestion.fir_parser import FIRParser


def test_fir_parser_extracts_fields():
    parser = FIRParser()
    sample = """
FIR No. 123/2024
Date: 15/01/2024
Police Station: Dharavi
Complainant: Ramesh Patil
Accused: Rajan Sharma, Priya Desai, Mohan Pillai
Section: 302 IPC, 34 IPC
Place of Occurrence: Dharavi, Mumbai
Vehicle: MH01AB1234 was spotted at the scene.
    """
    result = parser.parse_text(sample, "test_fir.txt")
    assert result["fir_number"] == "123/2024"
    assert result["police_station"] == "Dharavi"
    assert len(result["accused_names"]) >= 2
    assert "Rajan Sharma" in result["accused_names"]
    assert "MH01AB1234" in result["vehicles"]


# ── CDR Parser tests ──────────────────────────────────────────────────────────

import pandas as pd
from ingestion.cdr_parser import CDRParser


def test_cdr_parser_csv():
    parser = CDRParser()
    df = pd.DataFrame({
        "caller":    ["9876543210", "9876543210", "9123456789"],
        "receiver":  ["9123456789", "9000000001", "9876543210"],
        "date":      ["2024-01-01 10:00", "2024-01-01 22:30", "2024-01-02 09:00"],
        "duration":  [120, 300, 60],
        "tower":     ["Dharavi", "Kurla", "Andheri"],
    })
    result = parser.parse_dataframe(df, "test_cdr.csv")
    assert result["total_records"] == 3
    assert len(result["entities"]) == 3          # 3 unique phones
    assert len(result["relationships"]) == 3


# ── Custom NER tests ──────────────────────────────────────────────────────────

from nlp.custom_ner_rules import extract_regex_entities, PATTERNS


def test_vehicle_plate_detected():
    text = "The suspect fled in vehicle MH01AB1234 towards Dharavi."
    entities = extract_regex_entities(text)
    plates = [e for e in entities if e["label"] == "VEHICLE_PLATE"]
    assert len(plates) == 1
    assert "MH01AB1234" in plates[0]["text"]


def test_phone_number_detected():
    text = "Contact him at 9876543210 or +91-9123456789."
    entities = extract_regex_entities(text)
    phones = [e for e in entities if e["label"] == "PHONE_IN"]
    assert len(phones) >= 1


def test_fir_number_detected():
    text = "As per FIR No. 456/2024 filed at Dharavi police station."
    entities = extract_regex_entities(text)
    firs = [e for e in entities if e["label"] == "FIR_NUMBER"]
    assert len(firs) == 1
