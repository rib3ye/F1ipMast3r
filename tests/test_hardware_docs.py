import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HardwareDocsTest(unittest.TestCase):
    def test_skill_gpio_pinout_matches_flipper_header(self):
        skill = (ROOT / "SKILL.md").read_text()
        match = re.search(
            r"GPIO pinout \(top of device, looking at screen\):\n\n```(?P<table>.*?)```",
            skill,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "SKILL.md must contain the GPIO pinout table")

        rows = {}
        for line in match.group("table").strip().splitlines():
            parts = line.split()
            self.assertGreaterEqual(len(parts), 2, f"Malformed GPIO row: {line!r}")
            rows[int(parts[0])] = parts[1]

        self.assertEqual(
            rows,
            {
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
            },
        )

    def test_mousejack_nrf24_ce_uses_pc3_pin(self):
        host_side = (ROOT / "host-side.md").read_text()

        self.assertIn("NRF24 CE   -> pin 7   (PC3)", host_side.replace("→", "->"))
        self.assertNotIn("NRF24 CE   -> pin 14  (PC3)", host_side.replace("→", "->"))


if __name__ == "__main__":
    unittest.main()
