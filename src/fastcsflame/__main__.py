"""Interface for ``python -m fastcsflame``."""

from argparse import ArgumentParser
from collections.abc import Sequence

from fastcs.launch import FastCS
from fastcs.transports.epics.ca import EpicsCATransport

from fastcsflame.flame_controller import FlameController

from . import __version__

__all__ = ["main"]


def main(args: Sequence[str] | None = None) -> None:
    """Argument parser for the CLI."""
    parser = ArgumentParser()
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
    )
    parser.parse_args(args)

    epics_ca = EpicsCATransport()

    flame_controller = FlameController("172.23.91.5", 7016)
    flame_controller.set_path(["FLAME"])

    fastcs = FastCS(flame_controller, [epics_ca])

    fastcs.run()


if __name__ == "__main__":
    main()
