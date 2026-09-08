"""CLI subcommand wrapper: `python -m tools.timesfm.cli forecast|evaluate`."""

from __future__ import annotations

import argparse
import json
import sys


def cmd_forecast(args: argparse.Namespace) -> int:
    """Forward sang `run_forecast` và in JSON."""
    from .forecast import run_forecast
    from .model import ModelLoadError, get_availability_status

    if not args.device or args.device == "auto":
        device = None  # auto-detect
    else:
        device = args.device

    try:
        result = run_forecast(
            symbol=args.symbol,
            interval=args.interval,
            period=args.period,
            context_length=args.context,
            horizon=args.horizon,
            buy_threshold=args.buy_threshold,
            sell_threshold=args.sell_threshold,
            device=device,
        )
    except ModelLoadError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "availability": get_availability_status(),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1

    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Forward sang `run_evaluate` và in JSON."""
    from .evaluate import run_evaluate
    from .model import ModelLoadError, get_availability_status

    if not args.device or args.device == "auto":
        device = None
    else:
        device = args.device

    try:
        result = run_evaluate(
            symbol=args.symbol,
            interval=args.interval,
            period=args.period,
            context_length=args.context,
            horizons=args.horizons,
            step=args.step,
            max_samples=args.max_samples,
            device=device,
        )
    except ModelLoadError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "availability": get_availability_status(),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1

    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.timesfm.cli",
        description="TimesFM 3.0 forecast + walk-forward evaluation",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--symbol", type=str, default="GC=F")
    common.add_argument(
        "--interval",
        type=str,
        default="15m",
        choices=["1m", "5m", "15m", "30m", "60m", "90m", "1h", "1d"],
    )
    common.add_argument(
        "--period",
        type=str,
        default="60d",
        choices=["7d", "30d", "60d", "1mo", "3mo", "6mo", "1y", "2y", "max"],
    )
    common.add_argument("--context", type=int, default=256)
    common.add_argument("--device", type=str, default="auto", choices=["auto", "cuda", "cpu"])

    # forecast
    p_fc = sub.add_parser("forecast", parents=[common], help="Forecast N bước giá")
    p_fc.add_argument("--horizon", type=int, default=12)
    p_fc.add_argument("--buy-threshold", type=float, default=0.002)
    p_fc.add_argument("--sell-threshold", type=float, default=-0.002)
    p_fc.set_defaults(func=cmd_forecast)

    # evaluate
    p_ev = sub.add_parser(
        "evaluate", parents=[common], help="Walk-forward evaluation"
    )
    p_ev.add_argument("--horizons", type=int, nargs="+", default=[1, 3, 6, 12])
    p_ev.add_argument("--step", type=int, default=12)
    p_ev.add_argument("--max-samples", type=int, default=100)
    p_ev.set_defaults(func=cmd_evaluate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
