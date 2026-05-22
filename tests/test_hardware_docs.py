import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HardwareDocsTest(unittest.TestCase):
    def test_skill_gpio_pinout_matches_flipper_header(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        block_match = re.search(
            r"GPIO pinout \(top of device, looking at screen\):\n\n```(.*?)```",
            text,
            re.S,
        )
        self.assertIsNotNone(block_match, "GPIO pinout block missing from SKILL.md")

        lines = [
            line.strip()
            for line in block_match.group(1).splitlines()
            if line.strip()
        ]
        pinout = {}
        for line in lines:
            match = re.match(r"^(\d+)\s+(\S+)(?:\s+(.*))?$", line)
            self.assertIsNotNone(match, f"Unparseable pinout line: {line}")
            pinout[int(match.group(1))] = (
                match.group(2),
                match.group(3) or "",
            )

        expected = {
            1: "+5V",
            2: "PA7",
            3: "PA6",
            4: "PA4",
            5: "PB3",
            6: "PB2",
            7: "PC3",
            8: "GND",
            9: "+3V3",
            10: "PA14",
            11: "GND",
            12: "PA13",
            13: "PB6",
            14: "PB7",
            15: "PC1",
            16: "PC0",
            17: "PB14",
            18: "GND",
        }
        self.assertEqual({pin: value for pin, (value, _) in pinout.items()}, expected)
        self.assertIn("SWCLK", pinout[10][1])
        self.assertIn("SWDIO", pinout[12][1])
        self.assertIn("1-Wire", pinout[17][1])

    def test_nrf24_ce_uses_physical_pc3_pin(self):
        text = (ROOT / "host-side.md").read_text(encoding="utf-8")
        self.assertIn("NRF24 CE   -> pin 7   (PC3)", text.replace("→", "->"))
        self.assertNotIn("NRF24 CE   -> pin 14  (PC3)", text.replace("→", "->"))


if __name__ == "__main__":
    unittest.main()
