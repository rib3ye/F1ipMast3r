import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_doc(name):
    return (ROOT / name).read_text(encoding="utf-8")


class HardwareDocsTest(unittest.TestCase):
    def test_flipper_gpio_header_matches_firmware_pin_records(self):
        skill = read_doc("SKILL.md")

        expected_lines = [
            " 2  PA7   SPI MOSI / GPIO",
            " 3  PA6   SPI MISO / GPIO",
            " 4  PA4   SPI CS   / GPIO",
            " 5  PB3   SPI SCK  / GPIO",
            " 6  PB2   GPIO",
            " 7  PC3   GPIO",
            " 8  GND",
            "10  PA14  SWCLK",
            "12  PA13  SWDIO",
            "13  PB6   USART1 TX",
            "14  PB7   USART1 RX",
            "15  PC1   I2C SDA",
            "16  PC0   I2C SCL",
            "17  PB14  1-Wire / iButton",
            "18  GND",
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
                self.assertNotIn(line, skill)

    def test_nrf24_mousejack_ce_uses_pb2_pin_6(self):
        host_side = read_doc("host-side.md")

        ce_lines = [
            line.strip().replace("→", "->")
            for line in host_side.splitlines()
            if line.strip().startswith("NRF24 CE")
        ]

        self.assertEqual(ce_lines, ["NRF24 CE   -> pin 6   (PB2)"])
        self.assertNotIn("NRF24 CE   -> pin 14  (PC3)", host_side.replace("→", "->"))

    def test_esp32_s2_flashing_guidance_preserves_bootloader_slot(self):
        wifi = read_doc("wifi-devboard.md")

        self.assertNotIn(
            "write_flash 0x1000 firmware.bin",
            wifi,
            "Do not tell users to write arbitrary app images over the bootloader slot.",
        )
        self.assertIn("0x1000 bootloader.bin", wifi)
        self.assertIn("0x8000 partitions.bin", wifi)
        self.assertIn("0xE000 boot_app0.bin", wifi)
        self.assertIn("0x10000 firmware.bin", wifi)

    def test_devboard_log_docs_do_not_confuse_flipper_and_blackmagic_ports(self):
        wifi = read_doc("wifi-devboard.md")
        fap = read_doc("fap-development.md")

        self.assertIn("/dev/cu.usbmodemblackmagic3", wifi)
        self.assertIn("/dev/cu.usbmodemblackmagic3", fap)

        confused_patterns = [
            r"Devboard.*usbmodemflip_\*\*?1.*logs",
            r"Devboard.*usbmodemflip_\*\*?3.*logs",
        ]

        for doc in (wifi, fap):
            for pattern in confused_patterns:
                with self.subTest(pattern=pattern):
                    self.assertIsNone(re.search(pattern, doc, flags=re.IGNORECASE))


if __name__ == "__main__":
    unittest.main()
