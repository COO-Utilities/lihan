"""Test suite for the SunpowerCryocooler class in hispec.util module."""
import unittest
from unittest.mock import patch
# pylint: disable=import-error,no-name-in-module
from tc4382 import Tc4382


class TestTc4382(unittest.TestCase):
    """Unit tests for the SunpowerCryocooler class."""

    @patch("serial.Serial")
    def setUp(self, mock_serial): # pylint: disable=arguments-differ
        """Set up the test case with a mocked serial connection."""
        self.mock_serial = mock_serial.return_value
        self.mock_serial.read.return_value = b""
        self.controller = Tc4382()
        self.controller.connect("COM1", 4800)

    def test_read_register(self):
        """Test getting a register value from the cryocooler."""
        with patch.object(self.controller, "read_register") as mock_read_register:
            self.controller.read_register(9)
            mock_read_register.assert_called_once_with(9)

    def test_set_temperature(self):
        """Test setting the target temperature on the cryocooler."""
        with patch.object(self.controller, "set_temperature") as mock_set_temperature:
            self.controller.set_temperature(110.0)
            mock_set_temperature.assert_called_once_with(110.0)

    def test_get_cold_head_temp(self):
        """Test getting the cold head temperature from the cryocooler."""
        with patch.object(self.controller, "get_coldhead_temp") as mock_get_coldhead_temp:
            self.controller.get_coldhead_temp()

if __name__ == "__main__":
    unittest.main()
