"""Interface for ``python -m fastcsflame``."""

from argparse import ArgumentParser
from collections.abc import Sequence

from fastcs.launch import FastCS
from fastcs.transports.epics.ca import EpicsCATransport

from fastcsflame.flame_controller import FlameController
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)

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

    spec_tel_obj = SpecTel("172.23.91.5", 7016)

    epics_ca = EpicsCATransport()

    flame_controller = FlameController(spec_tel_obj)
    flame_controller.set_path(["FLAME"])

    fastcs = FastCS(flame_controller, [epics_ca])

    fastcs.run()


if __name__ == "__main__":
    main()
