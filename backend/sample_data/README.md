# Sample Data for CrimNet Ingestion

This directory contains sample criminal data files for testing the CrimNet ingestion pipeline.

## Sample Data Files

### `sample_fir.json`
First Information Report (FIR) - primary complaint filing document with:
- Case metadata (ID, date, status, severity)
- Crime classification
- Location data with coordinates
- Primary and co-suspects with contact information
- Description and evidence file references

### `sample_cdr.json`
Call Detail Records (CDR) - telecommunications data with:
- Call timestamps and duration
- Caller/callee phone numbers
- Cell tower information with GPS coordinates
- Service provider metadata
- Multiple call instances to demonstrate network patterns

### `sample_financial.json`
Financial transaction records with:
- Wire transfers (international and domestic)
- Cash withdrawals and deposits
- Account holder information
- Risk flags and suspicious activity indicators
- Beneficiary/sender details

### `sample_surveillance.json`
Surveillance footage metadata and AI-detected events with:
- Camera locations with coordinates
- Person detection with face matching confidence
- Object detection (luggage, etc.)
- Group interactions and meetings
- Timeline of events

## Ingestion Usage

Use these files to test the backend ingestion endpoints:

```bash
# Ingest FIR data
curl -X POST http://localhost:8000/api/ingest/fir \
  -H "Content-Type: application/json" \
  -d @sample_fir.json

# Ingest CDR records
curl -X POST http://localhost:8000/api/ingest/cdr \
  -H "Content-Type: application/json" \
  -d @sample_cdr.json

# Ingest financial data
curl -X POST http://localhost:8000/api/ingest/financial \
  -H "Content-Type: application/json" \
  -d @sample_financial.json

# Ingest surveillance data
curl -X POST http://localhost:8000/api/ingest/surveillance \
  -H "Content-Type: application/json" \
  -d @sample_surveillance.json
```

## Data Model Notes

- All timestamps are in ISO 8601 UTC format
- Phone numbers use E.164 format (+country-number)
- Coordinates are WGS84 (latitude, longitude)
- Amounts are in the specified currency (primarily INR for Indian transactions)
- Risk flags indicate anomaly detection: `high`, `medium`, `low`
- Confidence scores are decimal 0-1 for AI detection models
