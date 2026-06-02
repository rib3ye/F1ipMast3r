import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HardwareDocsTest(unittest.TestCase):
    def test_skill_gpio_pinout_matches_upstream_firmware(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        pinout = re.search(
            r"GPIO pinout \(top of device, looking at screen\):\n\n```(?P<table>.*?)```",
            skill,
            flags=re.S,
        )
        self.assertIsNotNone(pinout, "SKILL.md should include the GPIO pinout table")

        expected_lines = [
            " 1  +5V",
            " 2  PA7   SPI MOSI / GPIO",
            " 3  PA6   SPI MISO / GPIO",
            " 4  PA4   SPI CS   / GPIO",
            " 5  PB3   SPI SCK  / GPIO",
            " 6  PB2   GPIO",
            " 7  PC3   GPIO",
            " 8  GND",
            " 9  +3V3",
            "10  PA14  SWCLK",
            "11  GND",
            "12  PA13  SWDIO",
            "13  PB6   USART1 TX",
            "14  PB7   USART1 RX",
            "15  PC1   I2C SDA",
            "16  PC0   I2C SCL",
            "17  PB14  1-Wire / iButton",
            "18  GND",
        ]
        table = pinout.group("table")
        for line in expected_lines:
            self.assertIn(line, table)

    def test_mousejack_nrf24_wiring_uses_flipper_pb2_for_ce(self):
        host_side = (ROOT / "host-side.md").read_text(encoding="utf-8")
        host_side = host_side.replace("\u2192", "->")
        self.assertIn("NRF24 CE   -> pin 6   (PB2)", host_side)
        self.assertNotIn("NRF24 CE   -> pin 14", host_side)


if __name__ == "__main__":
    unittest.main()
