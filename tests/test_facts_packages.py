import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from pyinfra.facts.pkg import PkgPackages
from pyinfra.facts.util.packages import (
    PackageInfo,
    PackageStatus,
    _version_sort_key,
    build_package_map,
)
from pyinfra_cli.util import json_encode


class TestVersionSortKey(TestCase):
    def test_numeric_run_compares_as_int_not_lexicographic(self):
        # Lexicographically "5.10" < "5.2" because '1' < '2'; natural order
        # must rank 5.10 above 5.2.
        assert _version_sort_key("5.2") < _version_sort_key("5.10")
        assert sorted(["5.10", "5.2"], key=_version_sort_key) == ["5.2", "5.10"]

    def test_trailing_revision_sorts_after_base(self):
        assert _version_sort_key("9.0") < _version_sort_key("9.0-1")

    def test_equal_versions_have_equal_keys(self):
        assert _version_sort_key("1.2.3") == _version_sort_key("1.2.3")

    def test_shorter_version_sorts_before_its_extension(self):
        assert _version_sort_key("1.2") < _version_sort_key("1.2.3")

    def test_orders_a_mixed_list(self):
        versions = ["1.10", "1.2", "1.9", "1.10-1"]
        assert sorted(versions, key=_version_sort_key) == ["1.2", "1.9", "1.10", "1.10-1"]


class TestPackageInfo(TestCase):
    def test_defaults_to_installed_status(self):
        info = PackageInfo(name="vim", installed_versions=("9.0",))
        assert info.status == PackageStatus.INSTALLED
        assert info.available_version is None

    def test_is_frozen(self):
        info = PackageInfo(name="vim", installed_versions=("9.0",))
        with self.assertRaises(Exception):
            info.installed_versions = ("9.1",)  # type: ignore[misc]

    def test_installed_version_returns_last_version(self):
        info = PackageInfo(name="kernel", installed_versions=("5.10.0-26", "6.1.0-13"))
        assert info.installed_version == "6.1.0-13"

    def test_installed_version_none_when_no_versions(self):
        info = PackageInfo(name="foo")
        assert info.installed_versions == ()
        assert info.installed_version is None

    def test_from_dict_requires_explicit_upgradeable_status(self):
        with self.assertRaisesRegex(ValueError, "available_version requires"):
            PackageInfo.from_dict(
                {
                    "name": "vim",
                    "installed_versions": ["9.0"],
                    "available_version": "9.1",
                }
            )

    def test_from_dict_defaults_to_installed_without_available_version(self):
        info = PackageInfo.from_dict({"name": "vim", "installed_versions": ["9.0"]})
        assert info.status is PackageStatus.INSTALLED

    def test_rejects_installed_status_with_available_version(self):
        with self.assertRaisesRegex(ValueError, "available_version requires"):
            PackageInfo.from_dict(
                {
                    "name": "vim",
                    "available_version": "9.1",
                    "status": "installed",
                }
            )

    def test_rejects_upgradeable_status_without_available_version(self):
        with self.assertRaisesRegex(ValueError, "requires available_version"):
            PackageInfo(name="vim", status=PackageStatus.UPGRADEABLE)


class TestPkgPackagesCommand(TestCase):
    def test_remote_version_failure_is_not_masked(self):
        # The YAML fact harness cannot assert shell exit statuses.
        with TemporaryDirectory() as temp_dir:
            pkg_path = Path(temp_dir, "pkg")
            pkg_path.write_text(
                "#!/bin/sh\ncase \"$1\" in\nquery) echo 'vim 9.0 0' ;;\nversion) exit 1 ;;\nesac\n",
                encoding="utf-8",
            )
            pkg_path.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{temp_dir}:{env.get('PATH', '')}"
            result = subprocess.run(
                PkgPackages().command(),
                shell=True,
                executable="/bin/sh",
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )

        assert result.returncode == 1


class TestBuildPackageMap(TestCase):
    def test_only_installed(self):
        result = build_package_map({"vim": {"9.0"}, "git": {"2.40"}})
        assert set(result.keys()) == {"vim", "git"}
        assert result["vim"] == PackageInfo(
            name="vim", installed_versions=("9.0",), status=PackageStatus.INSTALLED
        )
        assert result["git"] == PackageInfo(
            name="git", installed_versions=("2.40",), status=PackageStatus.INSTALLED
        )

    def test_marks_upgradeable(self):
        result = build_package_map(
            installed={"vim": {"9.0"}, "git": {"2.40"}},
            upgradeable={"vim": "9.1"},
        )
        assert result["vim"].status == PackageStatus.UPGRADEABLE
        assert result["vim"].available_version == "9.1"
        assert result["git"].status == PackageStatus.INSTALLED
        assert result["git"].available_version is None

    def test_marks_held(self):
        result = build_package_map(
            installed={"vim": {"9.0"}, "git": {"2.40"}},
            held={"vim"},
        )
        assert result["vim"].status == PackageStatus.HELD

    def test_held_takes_precedence_over_upgradeable(self):
        result = build_package_map(
            installed={"vim": {"9.0"}},
            upgradeable={"vim": "9.1"},
            held={"vim"},
        )
        assert result["vim"].status == PackageStatus.HELD
        assert result["vim"].available_version == "9.1"

    def test_handles_empty_versions(self):
        result = build_package_map({"foo": set()})
        assert result["foo"].installed_versions == ()
        assert result["foo"].installed_version is None

    def test_multiple_versions_sorted_natural_order(self):
        # Sets are hash-randomized; build_package_map sorts versions ascending
        # with a natural-order key. Lexicographically this set sorts to
        # ("5.10.0-26", "5.10.0-9", ...) because '2' < '9'; natural order must
        # rank -9 below -26 and put the natural-sort maximum last.
        result = build_package_map(
            {"linux-image": {"6.1.0-13", "6.1.0-12", "5.10.0-26", "5.10.0-9"}}
        )
        info = result["linux-image"]
        assert info.installed_versions == ("5.10.0-9", "5.10.0-26", "6.1.0-12", "6.1.0-13")
        assert info.installed_version == "6.1.0-13"

    def test_multiple_versions_natural_order_beats_lexicographic(self):
        # Lexicographic sort of this set is ["1.10", "1.2", "1.9"]; the
        # natural-order key must instead yield 1.2 < 1.9 < 1.10.
        result = build_package_map({"libfoo": {"1.10", "1.2", "1.9"}})
        info = result["libfoo"]
        assert info.installed_versions == ("1.2", "1.9", "1.10")
        assert info.installed_version == "1.10"

    def test_json_encode_round_trip(self):
        info = build_package_map({"vim": {"9.0"}}, upgradeable={"vim": "9.1"})["vim"]
        assert json.loads(json.dumps(info, default=json_encode)) == {
            "name": "vim",
            "installed_versions": ["9.0"],
            "available_version": "9.1",
            "status": "upgradeable",
        }

    def test_asdict_uses_enum(self):
        info = build_package_map({"vim": {"9.0"}}, upgradeable={"vim": "9.1"})["vim"]
        data = asdict(info)
        assert data["name"] == "vim"
        assert data["status"] == PackageStatus.UPGRADEABLE
