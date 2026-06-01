import re
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class HardwareDocsTest(unittest.TestCase):
    def test_flipper_gpio_pinout_matches_canonical_header(self):
        skill = (REPO_ROOT / "SKILL.md").read_text()
        pinout_match = re.search(
            r"GPIO pinout \(top of device, looking at screen\):\n\n```(?P<table>.*?)```",
            skill,
            flags=re.S,
        )
        self.assertIsNotNone(pinout_match)

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
        actual_lines = [line.rstrip() for line in pinout_match.group("table").splitlines() if line.strip()]

        self.assertEqual(actual_lines, expected_lines)

    def test_mousejack_nrf24_ce_uses_pb2_pin_6(self):
        host_side = (REPO_ROOT / "host-side.md").read_text()
        normalized_host_side = host_side.replace("\u2192", "->")
        wiring_match = re.search(
            r"Wiring \(NRF24 module -> Flipper GPIO\):\n\n```(?P<table>.*?)```",
            normalized_host_side,
            flags=re.S,
        )
        self.assertIsNotNone(wiring_match)
        wiring_table = wiring_match.group("table")
        self.assertIn("NRF24 CE   -> pin 6   (PB2)", wiring_table)
        self.assertNotIn("NRF24 CE   -> pin 14", wiring_table)


if __name__ == "__main__":
    unittest.main()
