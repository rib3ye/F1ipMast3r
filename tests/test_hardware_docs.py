from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_doc(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _gpio_pinout_block() -> str:
    text = _read_doc("SKILL.md")
    marker = "GPIO pinout (top of device, looking at screen):"
    return text.split(marker, 1)[1].split("```", 2)[1]


def _pin_lines() -> dict[str, str]:
    lines = {}
    for raw_line in _gpio_pinout_block().splitlines():
        fields = raw_line.split()
        if fields and fields[0].isdigit():
            lines[fields[0]] = raw_line
    return lines


def test_flipper_gpio_pinout_matches_firmware_header_mapping():
    pins = _pin_lines()

    expected_fragments = {
        "6": ("PB2", "GPIO"),
        "7": ("PC3", "GPIO"),
        "8": ("GND",),
        "10": ("PA14", "SWCLK"),
        "12": ("PA13", "SWDIO"),
        "13": ("PB6", "USART1", "TX"),
        "14": ("PB7", "USART1", "RX"),
        "17": ("PB14", "1-Wire", "iButton"),
    }

    for pin, fragments in expected_fragments.items():
        line = pins[pin]
        for fragment in fragments:
            assert fragment in line


def test_nrf24_ce_wire_uses_pc3_on_pin_7():
    host_side = _read_doc("host-side.md")
    ce_line = next(line for line in host_side.splitlines() if line.startswith("NRF24 CE"))

    assert "pin 7" in ce_line
    assert "(PC3)" in ce_line
    assert "pin 14" not in ce_line


if __name__ == "__main__":
    test_flipper_gpio_pinout_matches_firmware_header_mapping()
    test_nrf24_ce_wire_uses_pc3_on_pin_7()
