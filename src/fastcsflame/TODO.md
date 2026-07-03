# To Do list

## SpectrometerTelecommunicator

### Big Things
- Accept ascii communications from the device
- Maybe make a message queue so we dont send message that talk over each other and wait for each others responses
    (At the moment this should be handled for us by FastCS)

### Small Things
- Could use a general clean up in some areas
- In `connect` method make a new case for if the device is in binary mode. Maybe change to ascii mode too??
- `big_query` and `small_query` methods can be combined
- Interpret metadata from scan messages more, dont just disregard it

## Hdf5FileBuilder

### Big Things
- Ask Dom if file format is correct (send example)
    (Everything in DATA is correct)
    (What needs to be included in INSTRUMENT)
- Add exceptions
- Add documentation

### Small Things
- Maybe change the name?

## FlameControllerAttributes

### Big Things
- Combine DummyBoolIO and DummyStrIO into one class that uses generics
    (Same for Refs)

## FlameController
Looks fine??

## __main__
- Add CLI arguments for Controller arguments
- Change title
