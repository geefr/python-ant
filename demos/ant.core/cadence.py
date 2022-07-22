"""
Initialize a basic broadcast slave channel for listening to
an ANT+ combined speed/cadence sensor (e.g. Garmin GSC10)

Based heavily on https://gist.github.com/ramunasd/a2e40cd13dd4cacf5685
"""
from __future__ import print_function


import sys
import time

from ant.core import driver, node, event, message
from ant.core.constants import *

from config import *


def convertSB(raw):
    value = int(raw[1]) << 8
    value += int(raw[0])
    return value


class CadenceListener(event.EventCallback):
    lastC = 0
    lastW = 0
    wheelSpeed = 0

    def process(self, msg):
        if isinstance(msg, message.ChannelBroadcastDataMessage):

            cadenceTime = convertSB(msg.payload[1:3])
            speedTime = convertSB(msg.payload[5:7])
            if cadenceTime == self.lastC and speedTime == self.lastW:
                return
            crankRevolutions = convertSB(msg.payload[3:5])
            wheelRevolutions =  convertSB(msg.payload[7:9])
            if speedTime > self.lastW:
                self.wheelSpeed = 3.6 * 2105.0 / (speedTime - self.lastW)
            self.lastW = speedTime
            self.lastC = cadenceTime
            print(cadenceTime, ' ', speedTime, ':', crankRevolutions, self.wheelSpeed)


NETKEY = b'\xB9\xA5\x21\xFB\xBD\x72\xC3\x45'

# Initialize
stick = driver.USB1Driver(SERIAL, log=LOG)# , debug=DEBUG)
antnode = node.Node(stick)
antnode.registerEventListener(CadenceListener())
antnode.start(False)

# Set network key
network = node.Network(key=NETKEY, name='N:ANT+')
antnode.setNetworkKey(0, network)

# Get the first unused channel. Returns an instance of the node.Channel class.
channel = antnode.getFreeChannel()

# Initialize it as a receiving channel using our network key
channel.assign(network, CHANNEL_TYPE_TWOWAY_RECEIVE)

# https://infocenter.nordicsemi.com/index.jsp?topic=%2Fcom.nordic.infocenter.sdk5.v14.0.0%2Fant_examples_bicycle_spd_cad.html
# Set the channel ID to "0, 123, 0" for a speed receiver, "0, 122, 0" for a cadence receiver, or "0, 121, 0" for a combined receiver.
channel.setID(121, 0, 0)


# Listen forever and ever (not really, but for a long time)
channel.searchTimeout = TIMEOUT_NEVER

# set the radio frequency to 2457 MHz and the channel period to 8118 cycles (4,036 Hz) for a speed receiver, 8102 cycles (4,044 Hz) for a cadence receiver, or 8086 cycles (4,052 Hz) for a combined receiver.
channel.period = 8086

# And ANT frequency 57
channel.frequency = 57

try:
    # Time to go live
    channel.open()

    print("Listening for events...")
    while True:
        time.sleep(60)
finally:
    # Shutdown channel
    channel.close()
    channel.unassign()

    # Shutdown
    antnode.stop()
