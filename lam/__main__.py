from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lam",
        description="Linux Agent Manager — intelligent terminal multiplexer for AI agents",
    )
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--theme", help="Override theme (dark, light, dracula, etc.)")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    from lam.app import LAMApp

    app = LAMApp(config_path=args.config, theme_override=args.theme, verbose=args.verbose)
    app.run()


if __name__ == "__main__":
    main()
