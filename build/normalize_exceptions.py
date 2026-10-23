#!/usr/bin/env python3
"""Normalize a FreightWorks CSV export and report data-quality exceptions.

Standardizes formatting without fabricating missing values or timezone offsets.
"""
import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

REQUIRED = ('exception_id', 'terminal', 'event_type', 'carrier_code', 'event_ts')
DATE_FORMATS = ('%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M', '%Y-%m-%dT%H:%M:%S%z')


def normalize_terminal(value):
    raw = value.strip()
    aliases = {'t3': 'Terminal 3', 'terminal 3': 'Terminal 3'}
    return aliases.get(raw.lower(), raw)


def normalize_timestamp(value):
    raw = value.strip()
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(raw.replace('Z', '+00:00') if fmt.endswith('%z') else raw, fmt)
            # Offset-naive timestamps remain offset-naive; the export does not identify their timezone.
            return parsed.isoformat(timespec='seconds').replace('+00:00', 'Z'), parsed.tzinfo is None
        except ValueError:
            continue
    raise ValueError(f'unrecognized timestamp: {raw!r}')


def clean_file(source, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    cleaned = []
    issues = []
    counts = Counter()
    with source.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or any(col not in reader.fieldnames for col in REQUIRED):
            raise ValueError(f'CSV must have columns: {", ".join(REQUIRED)}')
        for rownum, row in enumerate(reader, start=2):
            eid = (row.get('exception_id') or '').strip()
            entry = {key: (row.get(key) or '').strip() for key in REQUIRED}
            entry['terminal'] = normalize_terminal(entry['terminal'])
            entry['carrier_code'] = entry['carrier_code'].upper()
            entry['event_type'] = entry['event_type'].lower()
            if not eid:
                issues.append({'row': rownum, 'exception_id': '', 'field': 'exception_id', 'issue': 'Missing ID; cannot confidently identify record'})
            if not entry['terminal']:
                issues.append({'row': rownum, 'exception_id': eid, 'field': 'terminal', 'issue': 'Missing terminal; cannot infer'})
            if not entry['carrier_code']:
                issues.append({'row': rownum, 'exception_id': eid, 'field': 'carrier_code', 'issue': 'Missing carrier code; cannot infer from other shipments'})
            if not entry['event_type']:
                issues.append({'row': rownum, 'exception_id': eid, 'field': 'event_type', 'issue': 'Missing event type; excluded from type summary'})
            else:
                counts[entry['event_type']] += 1
            try:
                entry['event_ts'], tz_unknown = normalize_timestamp(entry['event_ts'])
                if tz_unknown:
                    issues.append({'row': rownum, 'exception_id': eid, 'field': 'event_ts', 'issue': 'Timezone not supplied; ISO formatting applied without assuming UTC'})
            except ValueError:
                issues.append({'row': rownum, 'exception_id': eid, 'field': 'event_ts', 'issue': f'Could not parse timestamp {entry["event_ts"]!r}'})
            cleaned.append(entry)

    with (output_dir / 'cleaned_exceptions.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED)
        writer.writeheader()
        writer.writerows(cleaned)
    with (output_dir / 'event_summary.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['event_type', 'count'])
        writer.writerows(sorted(counts.items()))
    (output_dir / 'data_quality_issues.json').write_text(json.dumps(issues, indent=2) + '\n', encoding='utf-8')
    return cleaned, counts, issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_path', type=Path, help='Source exception CSV')
    parser.add_argument('--out', type=Path, default=Path('output'), help='Output directory')
    args = parser.parse_args()
    cleaned, counts, issues = clean_file(args.csv_path, args.out)
    print(f'Processed {len(cleaned)} records')
    for event, count in sorted(counts.items()):
        print(f'{event}: {count}')
    print(f'Data-quality notices: {len(issues)} (including unknown timezone warnings)')
    print(f'Files: {args.out}/cleaned_exceptions.csv, event_summary.csv, data_quality_issues.json')


if __name__ == '__main__':
    main()
