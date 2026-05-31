import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class HardwareDocsTest(unittest.TestCase):
    def test_skill_gpio_pinout_matches_flipper_header(self):
        skill = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.search(
            r"GPIO pinout \(top of device, looking at screen\):\n\n```(?P<table>.*?)```",
            skill,
            re.S,
        )
        self.assertIsNotNone(match, "SKILL.md should document the Flipper GPIO pinout")
        table = match.group("table")

        expected_lines = [
            " 1  +5V (USB-C powered, only when host attached or backflow OK)",
            " 2  PA7   SPI MOSI / GPIO",
            " 3  PA6   SPI MISO / GPIO",
            " 4  PA4   SPI CS   / GPIO",
            " 5  PB3   SPI SCK  / GPIO",
            " 6  PB2   GPIO",
            " 7  PC3   GPIO",
            " 8  GND",
            " 9  +3V3",
            "10  PA14  SWCLK (also used by Wi-Fi Devboard for SWD into target)",
            "11  GND",
            "12  PA13  SWDIO",
            "13  PB6   USART1 TX",
            "14  PB7   USART1 RX",
            "15  PC1   I2C SDA",
            "16  PC0   I2C SCL",
            "17  PB14  1-Wire / iButton",
            "18  GND",
        ]
        for line in expected_lines:
            self.assertIn(line, table)

    def test_mousejack_nrf24_ce_uses_pb2_pin_6(self):
        host_side = (REPO_ROOT / "host-side.md").read_text(encoding="utf-8")
        self.assertIn("NRF24 CE   \u2192 pin 6   (PB2)", host_side)
        self.assertNotIn("NRF24 CE   \u2192 pin 14  (PC3)", host_side)


if __name__ == "__main__":
    unittest.main()
