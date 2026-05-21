import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_doc(name):
    return (ROOT / name).read_text(encoding="utf-8")


class HardwareDocsTest(unittest.TestCase):
    def test_flipper_gpio_pinout_matches_canonical_physical_header(self):
        skill = read_doc("SKILL.md")

        expected_lines = [
            " 6  PB2   GPIO",
            " 7  PC3   GPIO",
            " 8  GND",
            "10  PA14  SWCLK",
            "12  PA13  SWDIO",
            "13  PB6   USART1 TX",
            "14  PB7   USART1 RX",
            "17  PB14  1-Wire / iButton",
        ]

        for line in expected_lines:
            self.assertIn(line, skill)

    def test_nrf24_ce_uses_pc3_on_physical_pin_7(self):
        host_side = read_doc("host-side.md")

        self.assertNotIn("NRF24 CE   \u2192 pin 14", host_side)
        self.assertIn("NRF24 CE   \u2192 pin 7   (PC3)", host_side)


if __name__ == "__main__":
    unittest.main()
