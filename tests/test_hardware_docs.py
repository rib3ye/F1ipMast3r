import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class HardwareDocsTest(unittest.TestCase):
    def test_skill_gpio_pinout_matches_flipper_header(self):
        skill = (ROOT / "SKILL.md").read_text()
        block = re.search(
            r"GPIO pinout \(top of device, looking at screen\):\n\n```(.*?)```",
            skill,
            re.S,
        )
        self.assertIsNotNone(block, "GPIO pinout block not found")

        actual = {}
        for line in block.group(1).splitlines():
            match = re.match(r"\s*(\d+)\s+([A-Z0-9+]+)", line)
            if match:
                actual[int(match.group(1))] = match.group(2)

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
        self.assertEqual(actual, expected)

    def test_nrf24_ce_uses_pc3_header_pin(self):
        host_side = (ROOT / "host-side.md").read_text()
        self.assertIn("NRF24 CE   \u2192 pin 7   (PC3)", host_side)
        self.assertNotIn("NRF24 CE   \u2192 pin 14", host_side)


if __name__ == "__main__":
    unittest.main()
