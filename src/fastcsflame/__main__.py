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
        "ip",
        type=str,
        help="IP Address of the terminal server (or other device) "
        "the flame spectrometer is connect to",
    )
    parser.add_argument(
        "port",
        type=int,
        help="The port of the terminal server (or other device) "
        "the flame spectrometer is connected to",
    )
    parser.add_argument(
        "mount-path",
        type=str,
        help="The path in the container to the mounted filesystem for saving data",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
    )
    arguments_object = parser.parse_args(args)

    configure_logging()

    gui_options = EpicsGUIOptions(
        output_dir=Path("epics/opi"), title="Flame Spectrometer Controller"
    )
    epics_ca = EpicsCATransport(gui=gui_options)

    flame_controller = FlameController(
        arguments_object.ip,
        arguments_object.port,
        mount_path="/",
        default_file_path="dls/b21/data",
        default_file_name="data",
    )
    flame_controller.set_path(["FLAME"])

    fastcs = FastCS(flame_controller, [epics_ca])

    fastcs.run()


if __name__ == "__main__":
    main()
