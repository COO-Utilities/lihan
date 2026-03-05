"""Low Level Driver module for Lihan TC4382 Cryocooler"""
import time
from typing import Union
import serial
from serial.tools.list_ports import comports

from hardware_device_base import HardwareSensorBase

def find_port() -> str | None:
    """Find a Tc4382 Cryocooler device."""
    ports = comports()
    for port in ports:
        if port.manufacturer:
            if 'FTDI' in port.manufacturer or 'Silicon Labs' in port.manufacturer:
                return port.device
    return None

def calculate_crc16(data):
    """Calculate Modbus CRC16"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

class Tc4382(HardwareSensorBase):
    """A driver class for the Lihan TC4382 Cryocooler using pymodbus."""
    def __init__(self, log: bool = True, logfile: str = __name__.rsplit(".", 1)[-1],
                 read_timeout: float = 1.0):
        """Instantiate a Tc4382 driver object."""

        super().__init__(log, logfile)
        self.read_timeout: float = read_timeout
        self.ser = None
        self.port:str | None = None
        self.baudrate:int | None = None

    def connect(self, port: str, baud: int = 4800):  # pylint: disable=W0221
        """Connect to a Tc4382 Cryocooler device."""
        self.report_info(f"Connecting to Lihan on {port}...")
        self.port = port
        self.baudrate = baud
        self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.read_timeout)
        time.sleep(1)
        self.report_info("Lihan connected")
        self._set_connected(True)

    def disconnect(self):
        """Disconnect from a Tc4382 Cryocooler device."""
        if self.ser:
            if self.ser.is_open:
                self.ser.close()
            else:
                self.report_warning("Lihan not connected")
            self.ser = None
            self._set_connected(False)
        else:
            self.report_error("Lihan not connected")
            self._set_connected(False)

    def read_register(self, address):
        """Read a single input register"""
        cmd = bytes([0x01, 0x04, 0x00, address, 0x00, 0x01])
        crc = calculate_crc16(cmd)
        cmd += crc.to_bytes(2, 'little')

        self.ser.reset_input_buffer()
        write_response = self.ser.write(cmd)
        self.report_debug(f"read_register: write response: {write_response}")
        time.sleep(0.1)

        response = self.ser.read(100)
        self.report_debug(f"read_register: read response: {response}")
        if len(response) >= 5:
            return int.from_bytes(response[3:5], byteorder='big')
        return None

    def read_holding_register(self, address):
        """Read a single holding register (for setpoints)"""
        cmd = bytes([0x01, 0x03, 0x00, address, 0x00, 0x01])
        crc = calculate_crc16(cmd)
        cmd += crc.to_bytes(2, 'little')

        self.ser.reset_input_buffer()
        write_response = self.ser.write(cmd)
        self.report_debug(f"read_holding_register: write response: {write_response}")
        time.sleep(0.1)

        response = self.ser.read(100)
        self.report_debug(f"read_holding_register: read response: {response}")
        if len(response) >= 5:
            return int.from_bytes(response[3:5], byteorder='big')
        return None

    def write_holding_register(self, address, value):
        """Write single holding register"""
        cmd = bytes([0x01, 0x06]) + address.to_bytes(2, 'big') + value.to_bytes(2, 'big')
        crc = calculate_crc16(cmd)
        cmd += crc.to_bytes(2, 'little')

        self.ser.reset_input_buffer()
        self.ser.write(cmd)
        time.sleep(0.1)
        response = self.ser.read(100)
        return len(response) > 0

    def start(self):
        """Start the cryocooler"""
        cmd = bytes.fromhex('01050020FF008DF0')
        self.ser.write(cmd)
        time.sleep(0.5)
        return len(self.ser.read(100)) > 0

    def stop(self):
        """Stop the cryocooler"""
        cmd = bytes.fromhex('010500200000CC00')
        self.ser.write(cmd)
        time.sleep(0.5)
        return len(self.ser.read(100)) > 0

    def set_temperature(self, temp_k):
        """Set target temperature in Kelvin"""
        temp_raw = int(temp_k)  # Don't multiply by 10!
        return self.write_holding_register(2, temp_raw)

    def get_coldhead_temp(self):
        """Get coldhead temperature in Kelvin"""
        temp_raw = self.read_register(9)
        if temp_raw:
            return temp_raw / 10.0
        return None

    def get_setpoint(self):
        """Get temperature setpoint in Kelvin"""
        setpoint_raw = self.read_holding_register(2)
        if setpoint_raw:
            return setpoint_raw / 10.0
        return None

    def _send_command(self, *args, **kwargs):
        """Send a command to the Tc4382 Cryocooler device."""
        return None

    def _read_reply(self) -> Union[str, None]:
        """Read a reply from the Tc4382 Cryocooler device."""
        return None

    # pylint: disable=too-many-branches
    def get_atomic_value(self, item: str ="") -> Union[float, int, str, None]:
        """Read a value from the Tc4382 Cryocooler device."""
        retval = None
        if "cold_head_temp" in item:
            retval =  self.get_coldhead_temp()
        elif "reject_temp" in item:
            reject_temp = self.read_register(15)
            if reject_temp:
                retval = reject_temp / 10.0
        elif "motor_temp" in item:
            motor_temp = self.read_register(16)
            if motor_temp:
                retval = motor_temp / 10.0
        elif "controller_temp" in item:
            controller_temp = self.read_register(17)
            if controller_temp:
                retval = controller_temp / 10.0
        elif "ambient_temp" in item:
            ambient_temp = self.read_register(18)
            if ambient_temp:
                retval = ambient_temp / 10.0
        elif "voltage" in item:
            retval = self.read_register(10)
        elif "current" in item:
            retval = self.read_register(12)
        elif "power" in item:
            retval = self.read_register(13)
        elif "setpoint" in item:
            retval = self.get_setpoint()
        return retval
