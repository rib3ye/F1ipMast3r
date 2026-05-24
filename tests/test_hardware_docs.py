import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HardwareDocsTest(unittest.TestCase):
    def test_skill_gpio_pinout_matches_flipper_header(self):
        skill = (ROOT / "SKILL.md").read_text()
        block_match = re.search(
            r"GPIO pinout \(top of device, looking at screen\):\n\n```(?P<pinout>.*?)```",
            skill,
            flags=re.S,
        )
        self.assertIsNotNone(block_match, "SKILL.md must include the GPIO pinout block")

        rows = {}
        for line in block_match.group("pinout").splitlines():
            match = re.match(r"\s*(\d+)\s+(.+?)\s*$", line)
            if match:
                rows[int(match.group(1))] = match.group(2)

        expected = {
            1: "+5V (USB-C powered, only when host attached or backflow OK)",
            2: "PA7   SPI MOSI / GPIO",
            3: "PA6   SPI MISO / GPIO",
            4: "PA4   SPI CS   / GPIO",
            5: "PB3   SPI SCK  / GPIO",
            6: "PB2   GPIO",
            7: "PC3   GPIO",
            8: "GND",
            9: "+3V3",
            10: "PA14  SWCLK \u2190 Wi-Fi Devboard wires this to ESP32-S2 GPIO1",
            11: "GND",
            12: "PA13  SWDIO",
            13: "PB6   USART1 TX",
            14: "PB7   USART1 RX",
            15: "PC1   I2C SDA",
            16: "PC0   I2C SCL",
            17: "PB14  1-Wire / iButton",
            18: "GND",
        }
        self.assertEqual(rows, expected)

    def test_nrf24_mousejack_ce_uses_pc3_physical_pin(self):
        host_side = (ROOT / "host-side.md").read_text()
        self.assertIn("NRF24 CE   \u2192 pin 7   (PC3)", host_side)
        self.assertNotIn("NRF24 CE   \u2192 pin 14  (PC3)", host_side)


if __name__ == "__main__":
    unittest.main()
