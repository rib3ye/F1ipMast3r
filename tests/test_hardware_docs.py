from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class HardwareDocsTest(unittest.TestCase):
    def test_skill_gpio_pinout_matches_flipper_header(self) -> None:
        skill = _read("SKILL.md")

        expected_rows = [
            " 1  +5V",
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

        for row in expected_rows:
            self.assertIn(row, skill)

        bad_rows = [
            " 6  GND",
            " 7  PA14",
            " 8  PA13",
            "10  PA15",
            "12  PB6",
            "13  PB7",
            "14  PC3",
            "17  PB2   1-Wire / iButton",
        ]

        for row in bad_rows:
            self.assertNotIn(row, skill)

    def test_mousejack_nrf24_ce_uses_pc3_header_pin(self) -> None:
        host_side = _read("host-side.md")

        self.assertIn("NRF24 CE   \u2192 pin 7   (PC3)", host_side)
        self.assertNotIn("NRF24 CE   \u2192 pin 14  (PC3)", host_side)


if __name__ == "__main__":
    unittest.main()
