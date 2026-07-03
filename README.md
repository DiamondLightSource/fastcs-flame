[![CI](https://github.com//fastcsflame/actions/workflows/ci.yml/badge.svg)](https://github.com//fastcsflame/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh//fastcsflame/branch/main/graph/badge.svg)](https://codecov.io/gh//fastcsflame)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# fastcsflame

EPICS driver for the OceanOptics Flame mini spectrometer

When started, the script connects to a spectrometer at a specific IP and port and interacts with it using the TelNet protocol. An IOC for interacting with this device is started. This allows users to interact with the device using channel access (controller name is FLAME) or through a Phoebus UI (opi files are generated in the opi directory). Users can create a file holding collected data by starting the a capture period (set Capture to 1). This will create a h5 file at the location specified by the FilePath PV with the value of the FileName PV as its name. Every time the Scan command is run scan data from the device will be added to this file. To end the capture period set Capture to 0 again. This will close the file and future scans will not be added.

What            | Where
:---:           | :---:
Source          | <https://gitlab.diamond.ac.uk/controls/containers/beamline/fastcs-flame>

# PVs of the Flame IOC
- IntegrationTime
- LastScanData
- Scan
- FilePath
- FileName
- Capture

Start the IOC:
`fastcsflame`
(in future this will have options for the address and port to communicate to the device on) 

Set integration time to 10:
`caput FLAME:IntegrationTime 10`

Get the data from the last scan:
`caget FLAME:LastScanData`

Trigger a scan on the Flame:
`caput FLAME:Scan 1`

Start the capture period (creates the h5 file)
`caput FLAME:Capture 1`

Stop the capture period (closes the h5 file, allowing users to view it)
`caput FLAME:Capture 0`
