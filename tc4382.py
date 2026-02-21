"""Low Level Driver module for Lihan TC4382 Cryocooler"""
from pymodbus.client import ModbusSerialClient

from hardware_device_base import HardwareSensorBase

class Tc4382(HardwareSensorBase):
    """A driver class for the Lihan TC4382 Cryocooler using pymodbus."""
    def __init__(self, log: bool = True, logfile: str = __name__.rsplit(".", 1)[-1],
                 read_timeout: float = 1.0):
        """Instantiate a Tc4382 driver object."""

        super().__init__(log, logfile)
        self.read_timeout = read_timeout
        self.client = None
        self.port = None
        self.baudrate = None

    def connect(self, port: str, baud: int = 115200):  # pylint: disable=W0221
        """Connect to a Tc4382 Cryocooler device."""
        self.port = port
        self.baudrate = baud
        self.client = ModbusSerialClient(port=port, baudrate=baud, parity='N', stopbits=1,
                                         bytesize=8, timeout=self.read_timeout)
        if self.client.connect():
            self.report_info(f"Modbus connection opened to {port}")
            self._set_connected(True)
        else:
            self.report_error(f"Modbus connection failed to {port}")
            self._set_connected(False)

    def disconnect(self):
        """Disconnect from a Tc4382 Cryocooler device."""
        if self.client:
            self.client.close()
            self.client = None
            self._set_connected(False)
        else:
            self.report_error("Modbus not connected")
            self._set_connected(False)
