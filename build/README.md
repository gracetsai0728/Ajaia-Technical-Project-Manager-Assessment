# FreightWorks exception normalization

Requires Python 3.9+; no third-party dependencies.

From the parent assessment directory:

```bash
python3 build/normalize_exceptions.py build/exceptions.csv --out build/output
```

Outputs:
- `cleaned_exceptions.csv`: normalized terminals, carrier codes and ISO 8601 timestamp formatting.
- `event_summary.csv`: counts grouped by normalized event type.
- `data_quality_issues.json`: missing data and unknown-timezone issues.

Expected totals: missed_pickup=2, doc_mismatch=2, carrier_substitution=1 (5 records). `CPX-88216` lacks `carrier_code`; the script leaves it blank. Four date strings lack timezone offsets, so they are not silently converted to UTC. The UTC-suffixed record preserves `Z`.

This is a data-quality diagnostic, not a fix for Terminal 3's EDI field schema or urgency-scoring behavior.
