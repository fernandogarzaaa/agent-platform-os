"""Command-line health verification for Agent Platform OS."""

from __future__ import annotations

import asyncio
import sys
from enum import Enum

from agent_platform_os.config import PlatformSettings
from agent_platform_os.health import HealthResult, check_all


class Ansi(str, Enum):
    """ANSI terminal colors used by the structured console reporter."""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


def print_result(result: HealthResult) -> None:
    """Print a single color-coded health result."""
    status = "OK" if result.ok else "FAIL"
    color = Ansi.GREEN if result.ok else Ansi.RED
    print(
        f"{color.value}{status:<4}{Ansi.RESET.value} "
        f"{Ansi.CYAN.value}{result.target.name:<18}{Ansi.RESET.value} "
        f"kind={result.target.kind.value:<5} "
        f"endpoint={result.target.host}:{result.target.port:<5} "
        f"latency_ms={result.latency_ms:8.2f} "
        f"detail={result.detail}",
        flush=True,
    )


async def run() -> int:
    """Run health checks and return a process exit code."""
    settings = PlatformSettings()
    results = await check_all(settings)
    exit_code = 0
    for item in results:
        if isinstance(item, BaseException):
            exit_code = 1
            print(
                f"{Ansi.RED.value}FAIL{Ansi.RESET.value} "
                f"{Ansi.CYAN.value}health_checker{Ansi.RESET.value} "
                f"detail={type(item).__name__}: {item}",
                flush=True,
            )
            continue
        print_result(item)
        if not item.ok:
            exit_code = 1

    if exit_code == 0:
        print(f"{Ansi.GREEN.value}Agent Platform OS health checks passed.{Ansi.RESET.value}")
    else:
        print(
            f"{Ansi.YELLOW.value}Agent Platform OS health checks reported failures."
            f"{Ansi.RESET.value}"
        )
    return exit_code


def main() -> None:
    """Execute the async health checker."""
    try:
        exit_code = asyncio.run(run())
    except KeyboardInterrupt:
        print(f"{Ansi.YELLOW.value}Health check interrupted by operator.{Ansi.RESET.value}")
        exit_code = 130
    except Exception as exc:
        print(
            f"{Ansi.RED.value}Unhandled health checker failure:{Ansi.RESET.value} "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
        exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
