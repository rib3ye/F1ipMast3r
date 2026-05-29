import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HardwareDocsTest(unittest.TestCase):
    def test_skill_gpio_pinout_matches_flipper_header(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

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
            with self.subTest(line=line):
                self.assertIn(line, skill)

        stale_lines = [
            " 6  GND",
            " 7  PA14",
            " 8  PA13",
            "10  PA15",
            "12  PB6",
            "13  PB7",
            "14  PC3",
            "17  PB2",
        ]
        for line in stale_lines:
            with self.subTest(line=line):
                self.assertNotIn(f"\n{line}", skill)

    def test_mousejack_nrf24_ce_uses_pb2_pin_6(self):
        host_side = (ROOT / "host-side.md").read_text(encoding="utf-8")
        ce_line = re.search(r"^NRF24 CE\s+.*pin\s+(\d+)\s+\(([^)]+)\)", host_side, re.M)

        self.assertIsNotNone(ce_line)
        self.assertEqual(("6", "PB2"), ce_line.groups())


if __name__ == "__main__":
    unittest.main()
