"""
Module for queing telegrams.

When a device wants to sends a telegram to the KNX bus, it has to queue it to the TelegramQueue within XKNX.

The underlaying KNXIPInterface will poll the queue and send the packets to the correct KNX/IP abstraction (Tunneling or Routing).

You may register callbacks to be notified if a telegram was pushed to the queue.
"""
import asyncio
import traceback

from xknx.knx import TelegramDirection, TelegramType

class TelegramQueue():
    """Class for telegram queue."""

    def __init__(self, xknx):
        """Initialize TelegramQueue class."""
        self.xknx = xknx
        self.telegram_received_cbs = []
        self.queue_stopped = asyncio.Event()

    def register_telegram_received_cb(self, telegram_received_cb):
        """Register callback for a telegram beeing received from KNX bus."""
        self.telegram_received_cbs.append(telegram_received_cb)

    def unregister_telegram_received_cb(self, telegram_received_cb):
        """Unregister callback for a telegram beeing received from KNX bus."""
        self.telegram_received_cbs.remove(telegram_received_cb)

    @asyncio.coroutine
    def start(self):
        """Start telegram queue."""
        self.xknx.loop.create_task(self.run())

    @asyncio.coroutine
    def run(self):
        """Endless loop for processing telegrams."""
        while True:
            telegram = yield from self.xknx.telegrams.get()

            # Breaking up queue if None is pushed to the queue
            if telegram is None:
                break

            yield from self.process_telegram(telegram)
            self.xknx.telegrams.task_done()

            if telegram.direction == TelegramDirection.OUTGOING:
                # limit rate to knx bus to 20 per second
                yield from asyncio.sleep(1/20)

        self.queue_stopped.set()

    @asyncio.coroutine
    def stop(self):
        """Stop telegram queue."""
        print("STOPPING TelegramQueue")
        # If a None object is pushed to the queue, the queue stops
        yield from self.xknx.telegrams.put(None)
        yield from self.queue_stopped.wait()

    @asyncio.coroutine
    def process_all_telegrams(self):
        """Process all telegrams being queued."""
        while not self.xknx.telegrams.empty():
            telegram = self.xknx.telegrams.get_nowait()
            yield from self.process_telegram(telegram)
            self.xknx.telegrams.task_done()

    @asyncio.coroutine
    def process_telegram(self, telegram):
        """Process telegram."""
        try:
            if telegram.direction == TelegramDirection.INCOMING:
                yield from self.process_telegram_incoming(telegram)
            elif telegram.direction == TelegramDirection.OUTGOING:
                yield from self.process_telegram_outgoing(telegram)

        # pylint: disable=broad-except
        except Exception as exception:
            print("Exception while processing telegram:", exception)
            traceback.print_exc()


    @asyncio.coroutine
    def process_telegram_outgoing(self, telegram):
        """Process outgoing telegram."""
        if self.xknx.knxip_interface is not None:
            yield from self.xknx.knxip_interface.send_telegram(telegram)
        else:
            print("WARNING, NO KNXIP INTERFACE DEFINED")

    @asyncio.coroutine
    def process_telegram_incoming(self, telegram):
        """Process incoming telegram."""
        if telegram.telegramtype == TelegramType.GROUP_WRITE or \
                telegram.telegramtype == TelegramType.GROUP_RESPONSE:

            processed = False
            for telegram_received_cb in self.telegram_received_cbs:
                if telegram_received_cb(telegram):
                    processed = True

            if not processed:
                for device in self.xknx.devices.devices_by_group_address(
                        telegram.group_address):
                    device.process(telegram)

        elif telegram.telegramtype == TelegramType.GROUP_READ:
            #print("IGNORING GROUP READ FOR {0}".format(telegram.group_address))
            pass
