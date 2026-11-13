# Host data that isn't JSON serialisable, which debug-inventory must still print (#2025)
import dataclasses


@dataclasses.dataclass
class Complex:
    id: int
    addr: str = dataclasses.field(init=False)

    def __post_init__(self):
        self.addr = f"192.168.0.{self.id}"


class Opaque:
    def __repr__(self):
        return "<Opaque>"


extra = Complex(id=42)
opaque = Opaque()
simple = "still shown"
