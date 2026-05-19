from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HardwareDocsTest(unittest.TestCase):
    def test_skill_gpio_pinout_matches_flipper_header(self):
        skill = (ROOT / "SKILL.md").read_text()

        expected_lines = [
            " 1  +5V",
            " 2  PA7",
            " 3  PA6",
            " 4  PA4",
            " 5  PB3",
            " 6  PB2",
            " 7  PC3",
            " 8  GND",
            " 9  +3V3",
            "10  PA14",
            "11  GND",
            "12  PA13",
            "13  PB6",
            "14  PB7",
            "15  PC1",
            "16  PC0",
            "17  PB14",
            "18  GND",
        ]

        for line in expected_lines:
            with self.subTest(line=line):
                self.assertIn(line, skill)

    def test_nrf24_ce_uses_physical_pc3_pin(self):
        host_side = (ROOT / "host-side.md").read_text()

        self.assertRegex(host_side, re.compile(r"NRF24 CE.*pin 7\s+\(PC3\)"))
        self.assertNotRegex(host_side, re.compile(r"NRF24 CE.*pin 14\s+\(PC3\)"))


if __name__ == "__main__":
    unittest.main()
