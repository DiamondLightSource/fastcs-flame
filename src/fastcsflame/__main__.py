"""Interface for ``python -m fastcsflame``."""

from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from fastcs.launch import FastCS
from fastcs.logging import configure_logging
from fastcs.transports.epics import EpicsGUIOptions
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

    configure_logging()

    gui_options = EpicsGUIOptions(
        output_dir=Path("./opi"), title="Flame Spectrometer Controller"
    )
    epics_ca = EpicsCATransport(gui=gui_options)

    flame_controller = FlameController(
        "172.23.91.5",
        7016,
        default_file_path="/dls/science/b21",
        default_file_name="data",
    )
    flame_controller.set_path(["FLAME"])

    fastcs = FastCS(flame_controller, [epics_ca])

    fastcs.run()


if __name__ == "__main__":
    main()
