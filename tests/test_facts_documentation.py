from pyinfra.facts.deb import DebPackage


def test_deb_package_documents_package_resolution():
    docstring = " ".join((DebPackage.__doc__ or "").split())

    assert "``*.deb``" in docstring
    assert "current working directory" in docstring
    assert "installed package database" in docstring
