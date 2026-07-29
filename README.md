[![CI](https://github.com//fastcsflame/actions/workflows/ci.yml/badge.svg)](https://github.com//fastcsflame/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh//fastcsflame/branch/main/graph/badge.svg)](https://codecov.io/gh//fastcsflame)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# fastcsflame

EPICS driver for the OceanOptics Flame mini spectrometer

When started, the script connects to a spectrometer at a specific IP and port and interacts with it using the TelNet protocol. An IOC for interacting with this device is started. This allows users to interact with the device using channel access (controller name is FLAME) or through a Phoebus UI (opi files are generated in the opi directory). Users can create a file holding collected data by starting the a capture period (set Capture to 1). This will create a h5 file at the location specified by the FilePath PV with the value of the FileName PV as its name. Every time the SingleScan command is run scan data from the device will be added to this file. To end the capture period set Capture to 0 again. This will close the file and future scans will not be added.

What            | Where
:---:           | :---:
Source          | https://github.com/DiamondLightSource/fastcs-flame

# PVs of the Flame IOC
- IntegrationTime
- ScanData
- SingleScan
- ScanInProgress
- FilePath
- FileName
- Capture

Start the IOC:
`fastcsflame <ip> <port> <PV prefix>="BL21B-EA-FLAME-01"`
ip: IP of device the flame is connected to  as a string (NOT IP of the flame itself)
    Standard setup is to connect the flame to a port on a terminal server
    This field would be the IP of the terminal server
    Example: "172.23.91.5" (This is the IP of B21's terminal server, where their flame spectrometer is connected)
port: Port of the device that connects to the flame as an integer
    Example: 7016 (This is the port in B21's terminal server that their flame is connected to)
PV prefix: Optional argument, self explanatory

Set integration time to 10:
`caput BL21B-EA-FLAME-01:IntegrationTime 10`

Get the data from the last scan:
`caget BL21B-EA-FLAME-01:ScanData`

Trigger a scan on the Flame:
`caput BL21B-EA-FLAME-01:SingleScan 1`

Check if the last triggered scan has finished running:
`caget BL21B-EA-FLAME-01:ScanInProgress`

Start the capture period (creates the h5 file)
`caput BL21B-EA-FLAME-01:Capture 1`

Stop the capture period (closes the h5 file, allowing users to view it)
`caput BL21B-EA-FLAME-01:Capture 0`
