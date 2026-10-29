"""CLI for ingesting docs and querying the Knowledge Ops agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure src is importable when running as a script
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def cmd_ingest(args: argparse.Namespace) -> int:
    from knowledge_ops.ingest import ingest_documents

    result = ingest_documents(reset=args.reset)
    print(json.dumps(result, indent=2))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    from knowledge_ops.graph import run_query
    from knowledge_ops.llm import resolve_provider

    result = run_query(args.query, session_id=args.session)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0

    print(f"Provider: {resolve_provider()}")
    print(f"Run: {result.get('run_id')}")
    print("\n=== Answer ===\n")
    print(result.get("answer", ""))
    validation = result.get("validation") or {}
    print("\n=== Validation ===")
    print(
        f"grounded={validation.get('grounded')}  "
        f"confidence={validation.get('confidence')}  "
        f"flags={validation.get('flags')}"
    )
    print("\n=== Sources ===")
    for s in result.get("sources") or []:
        print(f"- {s.get('source')} (score={s.get('score')}): {s.get('excerpt', '')[:120]}...")
    print("\n=== Disclaimers ===")
    for d in result.get("disclaimers") or []:
        print(f"- {d}")
    print("\n=== Traces ===")
    for t in result.get("traces") or []:
        print(f"[{t.get('ts')}] {t.get('agent')}/{t.get('event')}: {t.get('detail')}")
    if result.get("trace_path"):
        print(f"\nTrace file: {result['trace_path']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="knowledge-ops",
        description="Enterprise Knowledge Ops Agent (LangGraph + Chroma)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Ingest sample/enterprise docs into Chroma")
    ingest.add_argument("--reset", action="store_true", help="Drop and recreate collection")
    ingest.set_defaults(func=cmd_ingest)

    query = sub.add_parser("query", help="Ask a question")
    query.add_argument("query", help="Natural-language question")
    query.add_argument("--session", default="default", help="Session id for memory")
    query.add_argument("--json", action="store_true", help="Emit full JSON response")
    query.set_defaults(func=cmd_query)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
