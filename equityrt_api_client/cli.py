from __future__ import annotations

import argparse
import json
import os
from typing import Sequence

from dotenv import load_dotenv

from .client import EquityRTClient
from .wrappers.function_wrapper import FunctionCall


def _extract_first_formula(populate_formula_grid_result: dict[str, object]) -> str | None:
    result = populate_formula_grid_result.get("Result")
    if not isinstance(result, dict):
        return None

    cells = result.get("c")
    if not isinstance(cells, list):
        return None

    for cell in cells:
        if isinstance(cell, dict):
            formula = cell.get("f")
            if isinstance(formula, str) and formula.strip():
                return formula
    return None

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="equityrt-function-search",
        description="Interactive CLI search for EquityRT functions.",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("EQUITYRT_TOKEN"),
        help="EquityRT token. If omitted, EQUITYRT_TOKEN env var is used.",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("EQUITYRT_USERNAME"),
        help="EquityRT username/email. If omitted, EQUITYRT_USERNAME env var is used.",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("EQUITYRT_PASSWORD"),
        help="EquityRT password. If omitted, EQUITYRT_PASSWORD env var is used.",
    )
    parser.add_argument(
        "--authentication-type",
        default=os.getenv("EQUITYRT_AUTHENTICATION_TYPE", "UsernamePassword"),
        help='Authentication type (default: "UsernamePassword").',
    )
    parser.add_argument(
        "--source-code",
        default=os.getenv("EQUITYRT_SOURCE_CODE", "PL"),
        help="Exchange/source code (default: PL or EQUITYRT_SOURCE_CODE env var).",
    )
    parser.add_argument(
        "--grid-type",
        default="Search",
        help='PopulateFormulaGrid type (default: "Search").',
    )
    parser.add_argument(
        "--initial-text",
        default="",
        help="Initial search text.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=12,
        help="Maximum number of displayed results (default: 12).",
    )
    parser.add_argument(
        "--min-query-len",
        type=int,
        default=1,
        help="Minimum query length before searching (default: 1).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout in seconds (default: 15.0).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full result as JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv(dotenv_path=".env", override=False)
    parser = _build_parser()
    args = parser.parse_args(argv)

    client = EquityRTClient(token=args.token, timeout=args.timeout)
    if not client.token:
        if not args.username or not args.password:
            parser.error(
                "Provide --token or credentials (--username and --password), "
                "or set them in .env / environment variables."
            )

        client.authenticate(
            username=args.username,
            password=args.password,
            authentication_type=args.authentication_type,
            set_as_default_token=True,
        )

    result = client.interactive_function_search(
        source_code=args.source_code,
        grid_type=args.grid_type,
        initial_text=args.initial_text,
        max_results=args.max_results,
        min_query_len=args.min_query_len,
    )

    if result is None:
        print("No selection.")
        return 0

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print(f"Selected function: {result['selected']['text']}")
    print(f"Description: {result['selected'].get('description', 'No description')}")
    grid_result = result["populate_formula_grid"]
    if not isinstance(grid_result, dict):
        print("PopulateFormulaGrid result is not a JSON object.")
        print(grid_result)
        return 0

    formula = _extract_first_formula(grid_result)
    if not formula:
        print("No formula found in PopulateFormulaGrid result.")
        print(json.dumps(grid_result, indent=2, ensure_ascii=False))
        return 0

    print(f"Excel formula: {formula}")
    try:
        parsed = FunctionCall.from_excel_function(client, formula)
        print("Parsed FunctionCall:")
        print(parsed)
    except Exception as exc:
        print(f"Could not parse formula with FunctionCall.from_excel_function: {exc}")
        print("PopulateFormulaGrid result:")
        print(json.dumps(grid_result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
