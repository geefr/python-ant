# -*- coding: utf-8 -*-
"""ANT+ Heart Rate Device Profile

"""
# pylint: disable=not-context-manager,protected-access
##############################################################################
#
# Copyright (c) 2017, Matt Hughes
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

from __future__ import print_function

from threading import Lock

from plus import _EventHandler

class HeartRateCallback(object):
    """Receives heart rate events.
    """

    def device_found(self, device_number, transmission_type):
        """Called when a device is first detected.

        The callback receives the device number and transmission type.
        When instantiating the HeartRate class, these can be supplied
        in the device_id and transmission_type keyword parameters to
        pair with the specific device.
        """
        pass

    def heartrate_data(self, computed_heartrate, beat_count, rr_interval_ms):
        """Called when heart rate data is received.

        Currently only computed heart rate is returned.
        TODO: R-R interval data.
        """
        pass


class HeartRate(object):
    """ANT+ Heart Rate

    """
    def __init__(self, node, device_id=0, transmission_type=0, callback=None):
        """Open a channel for heart rate data

        Device pairing is performed by using a device_id and transmission_type
        of 0. Once a device has been identified for pairing, a new channel
        should be created for the identified device.
        """
        self._event_handler = _EventHandler(self, node)

        self.callback = callback

        self.lock = Lock()
        self._computed_heart_rate = None
        self._beat_count = 0
        self._previous_beat_count = 0
        self._previous_event_time = 0
        self._detected_device = None

        CHANNEL_FREQUENCY = 0x39
        CHANNEL_PERIOD = 8070
        DEVICE_TYPE = 0x78
        SEARCH_TIMEOUT = 30
        self._event_handler.open_channel(CHANNEL_FREQUENCY, CHANNEL_PERIOD,
                                         transmission_type, DEVICE_TYPE,
                                         device_id, SEARCH_TIMEOUT)


    def _set_data(self, data):
        # ChannelMessage prepends the channel number to the message data
        # (Incorrectly IMO)
        data_size = 9
        payload_offset = 1
        event_time_lsb_index = 4 + payload_offset
        event_time_msb_index = 5 + payload_offset
        heart_beat_count_index = 6 + payload_offset
        computed_heart_rate_index = 7 + payload_offset

        if len(data) != data_size:
            return

        with self.lock:
            self._computed_heart_rate = data[computed_heart_rate_index]

            beat_count = data[heart_beat_count_index]
            difference = 0
            if self._previous_beat_count > beat_count:
                correction = beat_count + 256
                difference = correction - self._previous_beat_count
            else:
                difference = beat_count - self._previous_beat_count
            self._previous_beat_count = beat_count

            # TODO this will still wrap...
            self._beat_count += difference

            event_time = (data[event_time_msb_index] << 8) + (data[event_time_lsb_index])
            if difference == 1:
                rr_interval = (event_time - self.previous_event_time) * 1000 / 1024
            else:
                rr_interval = 0

            self.previous_event_time = event_time

        if (self.callback):
            heartrate_data = getattr(self.callback, 'heartrate_data', None)
            if heartrate_data:
                heartrate_data(self._computed_heart_rate, self._beat_count, rr_interval)

    def _set_detected_device(self, device_num, trans_type):
        with self.lock:
            self._detected_device = (device_num, trans_type)

        if (self.callback):
            device_found = getattr(self.callback, 'device_found', None)
            if device_found:
                device_found(device_num, trans_type)


    @property
    def computed_heart_rate(self):
        """The computed heart rate calculated by the connected monitor.
        """
        rate = None
        with self.lock:
            rate = self._computed_heart_rate
        return rate

    @property
    def detected_device(self):
        """A tuple representing the detected device.

        This is of the form (device_number, transmission_type). This should
        be accessed when pairing to identify the monitor that is connected.
        To specifically connect to that monitor in the future, provide the
        result to the HeartRate constructor:

        HeartRate(node, device_number, transmission_type)
        """
        return self._detected_device

    @property
    def state(self):
        """Returns the current state of the connection. Only when this is
        STATE_RUNNING can the data from the monitor be relied upon.
        """
        return self._event_handler._state

    @property
    def channel(self):
        """Temporary until refactoring unit tests.
        """
        return self._event_handler.channel
