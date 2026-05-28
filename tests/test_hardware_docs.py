import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HardwareDocsTest(unittest.TestCase):
    def test_skill_gpio_pinout_matches_firmware_header_numbers(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        match = re.search(
            r"GPIO pinout \(top of device, looking at screen\):\n\n```(?P<pinout>.*?)```",
            skill,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "SKILL.md GPIO pinout block not found")

        pinout = {
            int(pin): description.strip()
            for pin, description in re.findall(
                r"^\s*(\d+)\s+(.+)$", match.group("pinout"), re.MULTILINE
            )
        }

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

        for pin, signal in expected.items():
            self.assertIn(pin, pinout)
            self.assertTrue(
                pinout[pin].startswith(signal),
                f"pin {pin} should start with {signal!r}, got {pinout[pin]!r}",
            )

    def test_nrf24_mousejack_ce_uses_documented_mousejack_pin(self):
        host_side = (ROOT / "host-side.md").read_text(encoding="utf-8")

        self.assertIn("NRF24 CE   \u2192 pin 6   (PB2)", host_side)
        self.assertNotIn("NRF24 CE   \u2192 pin 14  (PC3)", host_side)
        self.assertNotIn("NRF24 CE   \u2192 pin 7   (PC3)", host_side)


if __name__ == "__main__":
    unittest.main()
