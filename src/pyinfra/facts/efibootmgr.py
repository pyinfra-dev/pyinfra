from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple, TypedDict

from typing_extensions import override

from pyinfra.api import FactBase

BootEntry = Tuple[bool, str]
EFIBootMgrInfoDict = TypedDict(
    "EFIBootMgrInfoDict",
    {
        "BootNext": Optional[int],
        "BootCurrent": Optional[int],
        "Timeout": Optional[int],
        "BootOrder": Optional[List[int]],
        "Entries": Dict[int, BootEntry],
    },
)


class EFIBootMgr(FactBase[Optional[EFIBootMgrInfoDict]]):
    """
    Returns information about the UEFI boot variables:

    .. code:: python

        {
            "BootNext": 6,
            "BootCurrent": 6,
            "Timeout": 0,
            "BootOrder": [1,4,3],
            "Entries": {
                1: (True, "myefi1"),
                2: (False, "myefi2.efi"),
                3: (True, "myefi3.efi"),
                4: (True, "grub2.efi"),
            },
        }
    """

    @override
    def requires_command(self, *args: Any, **kwargs: Any) -> str:
        return "efibootmgr"

    @override
    def command(self) -> str:
        # FIXME: Use '|| true' to properly handle the case where
        #        'efibootmgr' is run on a non-UEFI system
        return "efibootmgr || true"

    @override
    def process(self, output: Iterable[str]) -> Optional[EFIBootMgrInfoDict]:
        # This parsing code closely follows the printing code of efibootmgr
        # at <https://github.com/rhboot/efibootmgr/blob/main/src/efibootmgr.c#L2020-L2048>

        info: EFIBootMgrInfoDict = {
            "BootNext": None,
            "BootCurrent": None,
            "Timeout": None,
            "BootOrder": [],
            "Entries": {},
        }

        output = iter(output)

        line: Optional[str] = next(output, None)

        if line is None:
            # efibootmgr run on a non-UEFI system, likely printed
            # "EFI variables are not supported on this system."
            # to stderr
            return None

        # 1. Maybe have BootNext
        if line and line.startswith("BootNext: "):
            info["BootNext"] = int(line[len("BootNext: ") :], 16)
            line = next(output, None)

        # 2. Maybe have BootCurrent
        if line and line.startswith("BootCurrent: "):
            info["BootCurrent"] = int(line[len("BootCurrent: ") :], 16)
            line = next(output, None)

        # 3. Maybe have Timeout
        if line and line.startswith("Timeout: "):
            info["Timeout"] = int(line[len("Timeout: ") : -len(" seconds")])
            line = next(output, None)

        # 4. `show_order`
        if line and line.startswith("BootOrder: "):
            entries = line[len("BootOrder: ") :]
            info["BootOrder"] = list(map(lambda x: int(x, 16), entries.split(",")))
            line = next(output, None)

        # 5. `show_vars`: The actual boot entries
        while line is not None and line.startswith("Boot"):
            number = int(line[4:8], 16)

            # Entries marked with a * are active
            active = line[8:9] == "*"

            # TODO: Maybe split and parse (name vs. arguments ?), might require --verbose ?
            entry = line[10:]
            info["Entries"][number] = (active, entry)
            line = next(output, None)

        # 6. `show_mirror`
        # Currently not implemented, since I haven't actually encountered this in the wild.
        if line is not None:
            raise ValueError(f"Unexpected line '{line}' while parsing")

        return info
