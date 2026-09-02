"""
ingestion/financial_parser.py — Parser for bank transaction records.
Handles CSV / Excel bank statements and identifies suspicious transactions.
"""

import logging
import io
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)

COLUMN_ALIASES = {
    "account":     ["account", "account_no", "account_number", "acct_no", "sender_account"],
    "beneficiary": ["beneficiary", "recipient", "receiver", "to_account", "credited_to"],
    "amount":      ["amount", "transaction_amount", "debit", "credit", "value", "txn_amount"],
    "timestamp":   ["date", "txn_date", "transaction_date", "value_date", "timestamp"],
    "type":        ["type", "txn_type", "transaction_type", "mode", "channel"],
    "reference":   ["reference", "ref_no", "txn_id", "utr", "narration", "remarks"],
}

# Thresholds for suspicious transaction flagging
SUSPICIOUS_AMOUNT   = 50_000     # INR
ROUND_AMOUNT_MOD    = 10_000     # Round-number transactions
HIGH_FREQ_THRESHOLD = 10         # >10 transactions/day from same account


class FinancialParser:
    """Parses financial transaction records and flags suspicious activity."""

    def parse_dataframe(self, df: pd.DataFrame, source_name: str = "FINANCIAL") -> Dict[str, Any]:
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        mapping = {}
        for std, aliases in COLUMN_ALIASES.items():
            for alias in aliases:
                if alias in df.columns:
                    mapping[std] = alias
                    break

        records = []
        for _, row in df.iterrows():
            acct    = str(row.get(mapping.get("account", ""), "")).strip()
            benef   = str(row.get(mapping.get("beneficiary", ""), "")).strip()
            amount  = float(row.get(mapping.get("amount", ""), 0) or 0)
            ts      = str(row.get(mapping.get("timestamp", ""), "")).strip()
            txn_ref = str(row.get(mapping.get("reference", ""), "")).strip()
            txn_type = str(row.get(mapping.get("type", ""), "transfer")).strip()

            is_suspicious = (
                amount >= SUSPICIOUS_AMOUNT
                or amount % ROUND_AMOUNT_MOD == 0
            )

            records.append({
                "account": acct,
                "beneficiary": benef,
                "amount": amount,
                "timestamp": ts,
                "txn_type": txn_type,
                "reference": txn_ref,
                "is_suspicious": is_suspicious,
                "source_doc": source_name,
            })

        suspicious = [r for r in records if r["is_suspicious"]]
        logger.info(
            f"Parsed {len(records)} transactions from '{source_name}' "
            f"({len(suspicious)} suspicious)"
        )
        return {
            "source_type": "FINANCIAL",
            "source_name": source_name,
            "total_records": len(records),
            "suspicious_count": len(suspicious),
            "records": records,
            "entities": self._derive_entities(records),
            "relationships": self._derive_relationships(records),
        }

    def parse_csv(self, file_bytes: bytes, filename: str = "transactions.csv") -> Dict[str, Any]:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes))
        except Exception as e:
            return {"error": str(e)}
        return self.parse_dataframe(df, filename)

    def parse_excel(self, file_bytes: bytes, filename: str = "transactions.xlsx") -> Dict[str, Any]:
        try:
            df = pd.read_excel(io.BytesIO(file_bytes))
        except Exception as e:
            return {"error": str(e)}
        return self.parse_dataframe(df, filename)

    def _derive_entities(self, records: List[Dict]) -> List[Dict]:
        accounts = set()
        for r in records:
            if r["account"]:    accounts.add(r["account"])
            if r["beneficiary"]: accounts.add(r["beneficiary"])
        return [{"name": a, "entity_type": "BankAccount", "account_number": a} for a in accounts]

    def _derive_relationships(self, records: List[Dict]) -> List[Dict]:
        rels = []
        for r in records:
            if r["account"] and r["beneficiary"]:
                rels.append({
                    "source_name": r["account"],
                    "target_name": r["beneficiary"],
                    "relation_type": "TRANSFERRED_TO",
                    "properties": {
                        "amount": r["amount"],
                        "timestamp": r["timestamp"],
                        "txn_type": r["txn_type"],
                        "reference": r["reference"],
                        "suspicious": r["is_suspicious"],
                    },
                })
        return rels


# ── Singleton ─────────────────────────────────────────────────────────────────
financial_parser = FinancialParser()
