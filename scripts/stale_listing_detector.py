#!/usr/bin/env python3
"""
Stale Listing Detector for NSGI-ORS Pipeline
Cross-references master enumeration against verification pass to find inconsistencies.

Only flags IDs that are marked ACTIVE in the master enumeration but have confirmed
removal context in the verification pass.
"""
import argparse
import json
import re
from pathlib import Path
from datetime import datetime


REMOVAL_PATTERNS = [
    r'CONFIRMED\s+INACTIVE',
    r'CANCELED',
    r'EXCLUDE\s+FROM\s+ACTIVE\s+PIPELINE',
    r'VERDICT:\s*INACTIVE',
    r'VERDICT:\s*CANCELED',
    r'WRONG\s+NOTICE\s+ID',
    r'WITHDRAWN',
    r'\bEXCLUDE\b',
]

REMOVAL_BLOCK_PATTERN = re.compile('|'.join(REMOVAL_PATTERNS), re.IGNORECASE)

ID_PATTERN = re.compile(
    r'(?:'
    r'\b[A-Z]{2,}[0-9]{2,}(?:-[A-Z0-9-]+)*\b|'
    r'\b[0-9a-f]{32}\b'
    r')',
    re.IGNORECASE
)

PHONE_PATTERN = re.compile(r'\b\d{3}-\d{3}-\d{4}\b')
DATE_PATTERN = re.compile(r'\b(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b')
GENERIC_TERMS = {
    'RE-VERIFICATION', 'MICRO-PURCHASE', 'SET-ASIDE', 'SOURCES-SOUGHT',
    'FOLLOW-ON', 'SOLE-SOURCE', 'VERIFICATION', 'STATUS', 'ACTIVE',
    'CONFIRMED', 'INACTIVE', 'CANCELED', 'WITHDRAWN', 'PAST', 'DUE',
    'VERIFIED', 'REMOVED', 'EXCLUDE', 'WRONG', 'NOTICE', 'INTENT',
    'EXPIRED', 'LISTED', 'RE-COMPETE', 'DEADLINE', 'RESPONSE', 'DATE',
    'PUBLISHED', 'INACTIVE', 'PLACE', 'PERFORMANCE', 'CLEARANCE',
    'AGENCY', 'CONTACT', 'ADDRESS', 'ATTACHMENTS', 'TYPE', 'VALUE',
    'CONTRACT', 'EASY', 'PROJECTS', 'PROJECT', 'MAY', 'JUN', 'JUL',
    'AUG', 'SEP', 'OCT', 'NOV', 'DEC', 'JAN', 'FEB', 'MAR', 'APR',
    'JUNE', 'AUTHORITATIVE', 'SOURCE', 'VERDICT', 'ACTION', 'REQUIRED'
}


def _is_removal_context(text: str) -> bool:
    return bool(REMOVAL_BLOCK_PATTERN.search(text))


def _candidate_ids(text: str) -> set[str]:
    return set(
        m.group(0).upper()
        for m in ID_PATTERN.finditer(text)
        if m.group(0).upper() not in GENERIC_TERMS
        and not PHONE_PATTERN.match(m.group(0))
        and not DATE_PATTERN.match(m.group(0))
    )


def extract_removed_ids_from_verification(path: Path) -> dict[str, str]:
    content = path.read_text(encoding='utf-8')
    lines = content.splitlines()
    removed: dict[str, str] = {}

    context_window = 12
    for idx, line in enumerate(lines):
        if not _is_removal_context(line):
            continue
        window = '\n'.join(lines[idx:min(idx + context_window, len(lines))])
        opp_ids = _candidate_ids(window)
        for opp_id in opp_ids:
            if opp_id not in removed:
                removed[opp_id] = line.strip()

    return removed


def extract_active_ids_from_enumeration(path: Path) -> dict[str, str]:
    content = path.read_text(encoding='utf-8')
    lines = content.splitlines()
    active_ids: dict[str, str] = {}

    context_window = 8
    for idx, line in enumerate(lines):
        if not re.search(r'\bVERIFIED\s+ACTIVE\b|\bCONFIRMED\s+ACTIVE\b|\bACTIVE\s*\*?\b', line, re.IGNORECASE):
            continue
        window = '\n'.join(lines[max(0, idx - context_window):idx + 1])
        opp_ids = _candidate_ids(window)
        for opp_id in opp_ids:
            if opp_id not in active_ids:
                active_ids[opp_id] = line.strip()

    return active_ids


def detect_stale_listings(enumeration_path: Path, verification_path: Path):
    removed_ids = extract_removed_ids_from_verification(verification_path)
    active_ids = extract_active_ids_from_enumeration(enumeration_path)

    stale = []
    for opp_id, evidence in removed_ids.items():
        if opp_id in active_ids:
            stale.append({
                'id': opp_id,
                'status': 'REMOVED',
                'evidence': evidence,
                'issue': 'Listed as ACTIVE in master enumeration but marked as removed in verification pass',
                'recommendation': 'Remove from master enumeration or update verification pass'
            })

    return {
        'stale_listings': stale,
        'removed_count': len(removed_ids),
        'active_ids_count': len(active_ids),
        'present_in_enumeration_count': sum(1 for item in stale if item['id'] in active_ids)
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
    print('Active IDs in master enumeration: {}'.format(report['active_ids_count']))
    print('Removed IDs from verification: {}'.format(report['removed_count']))
    print('Active IDs with removal context: {}'.format(report['present_in_enumeration_count']))
    print('Stale listings found: {}'.format(len(report['stale_listings'])))
    if report['stale_listings']:
        print('Stale listings:')
        for item in report['stale_listings']:
            print('  - {}: {} ({})'.format(item['id'], item['status'], item['issue']))
    else:
        print('No inconsistencies detected')


if __name__ == '__main__':
    main()
