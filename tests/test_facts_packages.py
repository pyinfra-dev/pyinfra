from unittest import TestCase

from pyinfra.facts.util.packages import PackageInfo, PackageStatus, build_package_map


class TestPackageInfo(TestCase):
    def test_defaults_to_installed_status(self):
        info = PackageInfo(name="vim", installed_versions=("9.0",))
        assert info.status == PackageStatus.INSTALLED
        assert info.available_version is None

    def test_is_frozen(self):
        info = PackageInfo(name="vim", installed_versions=("9.0",))
        with self.assertRaises(Exception):
            info.installed_versions = ("9.1",)  # type: ignore[misc]

    def test_installed_version_returns_highest(self):
        info = PackageInfo(name="kernel", installed_versions=("5.10.0-26", "6.1.0-13"))
        assert info.installed_version == "6.1.0-13"

    def test_installed_version_empty_when_no_versions(self):
        info = PackageInfo(name="foo")
        assert info.installed_versions == ()
        assert info.installed_version == ""


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
        assert result["foo"].installed_version == ""

    def test_multiple_versions_sorted_natural_order(self):
        # Sets are hash-randomized; build_package_map sorts versions ascending
        # using a natural-order key, so 5.10 sorts below 6.1 (not above as it
        # would lexicographically), and the highest version is last.
        result = build_package_map({"linux-image": {"6.1.0-13", "6.1.0-12", "5.10.0-26"}})
        info = result["linux-image"]
        assert info.installed_versions == ("5.10.0-26", "6.1.0-12", "6.1.0-13")
        assert info.installed_version == "6.1.0-13"
