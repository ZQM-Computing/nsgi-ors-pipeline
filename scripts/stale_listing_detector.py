#!/usr/bin/env python3
"""
Stale Listing Detector for NSGI-ORS Pipeline
Cross-references master enumeration against verification pass to find inconsistencies.
"""
import argparse
import json
import re
from pathlib import Path
from datetime import datetime


def extract_removed_ids_from_verification(path):
    """Extract opportunity IDs marked as removed in verification pass."""
    content = path.read_text(encoding='utf-8')
    results = {}

    for m in re.finditer(r'(?:EX-(\d+))\s*[.:\-]\s*([^\n]+)', content, re.IGNORECASE):
        ex_block = m.group(2)
        if not re.search(r'\b(?:INACTIVE|CANCELED|WITHDRAWN|PAST\s+DUE|EXCLUDE|WRONG\s+NOTICE|INTENT\s+TO\s+SOLE\s+SOURCE)\b', ex_block, re.IGNORECASE):
            continue
        candidates = re.findall(r'\b(?:[0-9a-f]{32}|[A-Z]{2,}-[A-Z0-9-]{2,}-[A-Z0-9-]{2,}|[A-Z0-9]{4,}-[A-Z0-9]{2,}-[A-Z0-9-]+)\b', ex_block, re.IGNORECASE)
        for c in candidates:
            results[c.upper()] = 'REMOVED'

    for line in content.splitlines():
        if not re.search(r'\b(?:CONFIRMED INACTIVE|EXCLUDE)\b', line, re.IGNORECASE):
            continue
        candidates = re.findall(r'\b(?:[0-9a-f]{32}|[A-Z]{2,}-[A-Z0-9-]{2,}-[A-Z0-9-]{2,}|[A-Z0-9]{4,}-[A-Z0-9]{2,}-[A-Z0-9-]+)\b', line, re.IGNORECASE)
        for c in candidates:
            results[c.upper()] = 'REMOVED'

    return results


def check_ids_in_enumeration(enumeration_path, target_ids):
    enumeration_content = enumeration_path.read_text(encoding='utf-8').upper()
    return {opp_id: opp_id in enumeration_content for opp_id in target_ids}


def detect_stale_listings(enumeration_path, verification_path):
    removed_ids = extract_removed_ids_from_verification(verification_path)
    presence = check_ids_in_enumeration(enumeration_path, removed_ids.keys())

    stale = []
    for opp_id, is_present in presence.items():
        if is_present:
            stale.append({
                'id': opp_id,
                'status': 'REMOVED',
                'issue': 'Listed in enumeration but marked as removed in verification pass',
                'recommendation': 'Remove from master enumeration or update verification pass'
            })

    return {
        'stale_listings': stale,
        'removed_count': len(removed_ids),
        'present_in_enumeration_count': sum(1 for v in presence.values() if v)
    }


def main():
    parser = argparse.ArgumentParser(description='Detect stale listings in NSGI-ORS pipeline')
    parser.add_argument('--enum', required=True, help='Path to master enumeration markdown')
    parser.add_argument('--verification', required=True, help='Path to verification pass markdown')
    parser.add_argument('--output', default='stale_listings_report.json', help='Output JSON path')
    args = parser.parse_args()

    report = detect_stale_listings(Path(args.enum), Path(args.verification))
    report['generated_at'] = datetime.utcnow().isoformat() + 'Z'
    report['enumeration_file'] = str(args.enum)
    report['verification_file'] = str(args.verification)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Report written to {}'.format(output_path))
    print('Removed IDs from verification: {}'.format(report['removed_count']))
    print('Removed IDs still in enumeration: {}'.format(report['present_in_enumeration_count']))
    print('Stale listings found: {}'.format(len(report['stale_listings'])))
    if report['stale_listings']:
        print('Stale listings:')
        for item in report['stale_listings']:
            print('  - {}: {} ({})'.format(item['id'], item['status'], item['issue']))
    else:
        print('No inconsistencies detected')


if __name__ == '__main__':
    main()
