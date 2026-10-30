#!/usr/bin/env python3
"""Portable project records and optional global instructions (Python 3.9+, standard library)."""
import argparse
import json
import os
from pathlib import Path
import sys

from toolkit_integration import integrate
from toolkit_records import Records


def main():
    # Use portable UTF-8 streams even on Windows hosts with a legacy console code page.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--codex-home', type=Path, default=Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')))
    commands = parser.add_subparsers(dest='command', required=True)
    initialize = commands.add_parser('init', help='Initialize portable records after project identity is confirmed')
    initialize.add_argument('--name', required=True)
    initialize.add_argument('--actor', required=True)
    for name in ('publish', 'track'):
        command = commands.add_parser(name, help='Version a UTF-8 document; publish reads new content from stdin')
        command.add_argument('--path', required=True)
        command.add_argument('--actor', required=True)
        command.add_argument('--reason', required=True)
        if name == 'publish':
            command.add_argument('--expected', help='Current recorded SHA-256; required for updates')
    decision = commands.add_parser('decide', help='Append a sourced decision from a JSON object on stdin')
    decision.add_argument('--actor', required=True)
    review = commands.add_parser('review', help='Read-only record integrity, changes, and explicit decision conflicts')
    review.add_argument('--history', action='store_true', help='Also verify archived content hashes')
    commands.add_parser('install-integration', help='Explicitly merge toolkit instructions into user-level AGENTS.md')
    commands.add_parser('remove-integration', help='Remove only the toolkit instruction block; retain backups and project records')
    args = parser.parse_args()
    try:
        if args.command in ('install-integration', 'remove-integration'):
            result = integrate(args.codex_home, Path(__file__).resolve().parents[1], args.command == 'remove-integration')
        else:
            records = Records(args.project)
            if args.command == 'init':
                result = records.initialize(args.name, args.actor)
            elif args.command == 'publish':
                result = records.publish(args.path, sys.stdin.read(), args.actor, args.reason, args.expected)
            elif args.command == 'track':
                result = records.track(args.path, args.actor, args.reason)
            elif args.command == 'decide':
                result = records.decide(json.load(sys.stdin), args.actor)
            else:
                result = records.review(args.history)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('Toolkit: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
