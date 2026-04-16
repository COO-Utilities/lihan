"""Low Level Driver module for Lihan TC4382 Cryocooler"""
import time
from typing import Union
import serial
from serial.tools.list_ports import comports

from hardware_device_base import HardwareSensorBase

REGISTER_ITEMS = {
    # Input registers
    "mode": {"hold_reg": False, "register": 3, "factor": None},
    "controller_status": {"hold_reg": False, "register": 4, "factor": None},
    "motor_status": {"hold_reg": False, "register": 5, "factor": None},
    "cold_head_status": {"hold_reg": False, "register": 6, "factor": None},
    "cold_head_temp": {"hold_reg": False, "register": 9, "factor": 10.0},
    "output_voltage": {"hold_reg": False, "register": 10, "factor": 10.0},
    "output_current": {"hold_reg": False, "register": 12, "factor": 100.0},
    "output_power": {"hold_reg": False, "register": 13, "factor": 1.0},
    "power_factor": {"hold_reg": False, "register": 14, "factor": 1.0},
    "bus_voltage": {"hold_reg": False, "register": 15, "factor": 10.0},
    "temperature_status": {"hold_reg": False, "register": 16, "factor": None},
    "reject_temp": {"hold_reg": False, "register": 17, "factor": 10.0},
    "motor_temp": {"hold_reg": False, "register": 18, "factor": 10.0},
    "controller_temp": {"hold_reg": False, "register": 19, "factor": 10.0},
    "ambient_temp": {"hold_reg": False, "register": 20, "factor": 10.0},
    "fan_status": {"hold_reg": False, "register": 21, "factor": None},
    "fan_speed_a": {"hold_reg": False, "register": 22, "factor": None},
    "fan_speed_b": {"hold_reg": False, "register": 23, "factor": None},
    "fan_speed_c": {"hold_reg": False, "register": 24, "factor": None},
    "fan_speed_d": {"hold_reg": False, "register": 25, "factor": None},
    "uptime": {"hold_reg": False, "register": 26, "factor": 1.0},
    "total_uptime": {"hold_reg": False, "register": 27, "factor": 1.0},
    # Holding registers
    "setpoint": {"hold_reg": True, "register": 2, "factor": 10.0},
    "set_voltage": {"hold_reg": True, "register": 3, "factor": 10.0},
    "cooling_rate": {"hold_reg": True, "register": 11, "factor": 100.0},
    "comm_address": {"hold_reg": True, "register": 28, "factor": None},
    "comm_baudrate": {"hold_reg": True, "register": 29, "factor": None},
    "configuration": {"hold_reg": True, "register": 30, "factor": None},
    "pid_p": {"hold_reg": True, "register": 32, "factor": 100.0},
    "pid_i": {"hold_reg": True, "register": 33, "factor": 1000.0},
    "pid_d": {"hold_reg": True, "register": 34, "factor": 1000.0},
    "hc_pid_p": {"hold_reg": True, "register": 35, "factor": 100.0},
    "hc_pid_i": {"hold_reg": True, "register": 36, "factor": 1000.0},
    "hc_pid_d": {"hold_reg": True, "register": 37, "factor": 1000.0},
}

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
        self.configuration: int | None = None

    def connect(self, port: str, baud: int = 4800):  # pylint: disable=W0221
        """Connect to a Tc4382 Cryocooler device."""
        self.report_info(f"Connecting to Lihan on {port}...")
        self.port = port
        self.baudrate = baud
        self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.read_timeout)
        time.sleep(1)
        # clear input buffer
        self.ser.reset_input_buffer()
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

    def read_register(self, address) -> int | None:
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

    def read_holding_register(self, address) -> int | None:
        """Read a single holding register (for setpoints)"""
        cmd = bytes([0x01, 0x03, 0x00, address, 0x00, 0x01])
        crc = calculate_crc16(cmd)
        cmd += crc.to_bytes(2, 'little')

        self.ser.reset_input_buffer()
        time.sleep(0.1)
        write_response = self.ser.write(cmd)
        self.report_debug(f"read_holding_register: write response: {write_response}")
        time.sleep(0.5)

        response = self.ser.read(100)
        self.report_debug(f"read_holding_register: read response: {response}")
        if len(response) >= 5:
            return int.from_bytes(response[3:5], byteorder='big')
        return None

    def write_holding_register(self, address, value) -> bool:
        """Write single holding register"""
        cmd = bytes([0x01, 0x06]) + address.to_bytes(2, 'big') + value.to_bytes(2, 'big')
        crc = calculate_crc16(cmd)
        cmd += crc.to_bytes(2, 'little')

        self.ser.reset_input_buffer()
        time.sleep(0.1)
        write_response = self.ser.write(cmd)
        self.report_debug(f"write_holding_register: write response: {write_response}")
        time.sleep(0.5)

        response = self.ser.read(100)
        self.report_debug(f"write_holding_register: read response: {response}")
        return len(response) > 0

    def start(self) -> bool:
        """Start the cryocooler"""
        cmd = bytes.fromhex('01050020FF008DF0')
        write_response = self.ser.write(cmd)
        self.report_debug(f"start: write response: {write_response}")
        time.sleep(0.5)

        response = self.ser.read(100)
        self.report_debug(f"start: read response: {response}")
        return len(response) > 0

    def stop(self) -> bool:
        """Stop the cryocooler"""
        cmd = bytes.fromhex('010500200000CC00')
        write_response = self.ser.write(cmd)
        self.report_debug(f"stop: write response: {write_response}")
        time.sleep(0.5)

        response = self.ser.read(100)
        self.report_debug(f"stop: read response: {response}")
        return len(response) > 0

    def set_power_mode(self) -> bool:
        """Set power mode"""
        new_config = 0 & self.configuration
        return self.set_configuration(new_config)

    def set_temperature_mode(self) -> bool:
        """Set temperature mode"""
        new_config = 1 & self.configuration
        return self.set_configuration(new_config)

    def set_configuration(self, new_config: int) -> bool:
        """Set configuration"""
        write_response = self.write_holding_register(30, new_config)
        self.report_debug(f"set_temperature_mode: write response: {write_response}")
        time.sleep(0.5)

        response = self.ser.read(100)
        self.report_debug(f"set_temperature_mode: read response: {response}")
        self.get_device_configuration()
        return len(response) > 0

    def set_temperature(self, temp_k) -> bool:
        """Set target temperature in Kelvin"""
        temp_raw = int(temp_k) * 10
        return self.write_holding_register(2, temp_raw)

    def set_voltage(self, voltage) -> bool:
        """Set target voltage in volts"""
        voltage_raw = int(voltage) * 10
        return self.write_holding_register(3, voltage_raw)

    def get_coldhead_temp(self) -> float | None:
        """Get coldhead temperature in Kelvin"""
        temp_raw = self.read_register(9)
        self.report_debug(f"get_coldhead_temp raw value: {temp_raw}")
        if temp_raw:
            return temp_raw / 10.0
        return None

    def get_setpoint(self):
        """Get temperature setpoint in Kelvin"""
        setpoint_raw = self.read_holding_register(2)
        self.report_debug(f"get_setpoint raw value: {setpoint_raw}")
        if setpoint_raw:
            return setpoint_raw / 10.0
        return None

    def get_device_status(self):
        """Get controller status"""
        status = self.read_register(2)
        self.report_debug(f"status raw: {status}")
        stat = []
        stat_no = 0
        if status is not None:
            # bit 0
            if status & (1 << 0) != 0:
                stat.append("Running")
            if status & (1 << 1) != 0:
                stat.append("Fault")
            if status & (1 << 2) != 0:
                stat.append("Control stability")
            if status & (1 << 3) != 0:
                stat.append("Power off")
            if "Fault" in stat or "Control stability" in stat or "Power off" in stat:
                stat_no = -1
            if stat:
                stat_str = ",".join(stat)
                self._set_status((stat_no, stat_str))
                return stat_str
            return None
        return None

    def get_device_configuration(self):
        """Get controller configuration"""
        config = self.read_holding_register(30)
        self.report_debug(f"config raw: {config}")
        conf = []
        if config is not None:
            self.configuration = config
            # bit 0
            if config & (1 << 0) != 0:
                conf.append("Temp PID enable")
            if config & (1 << 1) != 0:
                conf.append("Temp cooling rate control")
            if config & (1 << 2) != 0:
                conf.append("Htr compensation")
            if config & (1 << 3) != 0:
                conf.append("Rej/Motor temp detect")
            if config & (1 << 4) != 0:
                conf.append("Power On recovery")
            if config & (1 << 5) != 0:
                conf.append("Power On autostart")
            if config & (1 << 6) != 0:
                conf.append("Pressure PID control")
            if config & (1 << 7) != 0:
                conf.append("Overtemp reduction")
            if conf:
                conf_str = ",".join(conf)
                return conf_str
            return None
        return None

    def _send_command(self, *args, **kwargs):
        """Send a command to the Tc4382 Cryocooler device."""
        self.report_warning("Not implemented")

    def _read_reply(self) -> Union[str, None]:
        """Read a reply from the Tc4382 Cryocooler device."""
        self.report_warning("Not implemented")

    # pylint: disable=too-many-branches
    def get_atomic_value(self, item: str ="") -> Union[float, int, str, None]:
        """Read a value from the Tc4382 Cryocooler device."""
        self.report_debug(f"Geting {item}")
        retval = None
        if "help" in item:
            print("Available items:\n")
            for its in REGISTER_ITEMS:
                print(its)
            return retval
        if "configuration" in item:
            retval = self.get_device_configuration()
        elif "controller_status" in item:
            retval = self.get_device_status()
        elif item in REGISTER_ITEMS:
            reg = REGISTER_ITEMS[item]["register"]
            hreg = REGISTER_ITEMS[item]["hold_reg"]
            factor = REGISTER_ITEMS[item]["factor"]
            if hreg:
                retval = self.read_holding_register(reg)
            else:
                retval = self.read_register(reg)
            if retval:
                if factor is not None:
                    retval = retval / factor
        else:
            self.report_warning(f"Not a legal item: {item}")
        return retval
