# To Do list

## SpectrometerTelecommunicator

### Big Things
- Accept ascii communications from the device
- Maybe make a message queue so we dont send message that talk over each other and wait for each others responses
    (At the moment this should be handled for us by FastCS)

### Small Things
- Interpret metadata from scan messages more, dont just disregard it

## Hdf5FileBuilder
Sorted

## FlameControllerAttributes

### Big Things
- Combine DummyBoolIO and DummyStrIO into one class that uses generics
    (Same for Refs)

## FlameController
Looks fine??

## __main__
- Add CLI arguments for Controller arguments
- Change title
