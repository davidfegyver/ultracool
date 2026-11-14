import pytest

from app.resolve import parse_designation


def test_designation_encodes_position_and_epoch():
    r = parse_designation("CWISE J201121.52-062438.1")
    assert r["ra"] == pytest.approx(302.8396667, abs=1e-6)
    assert r["dec"] == pytest.approx(-6.4105833, abs=1e-6)
    assert r["epoch_yr"] == 2015.4
    assert parse_designation("WISEA J153429.75-104303.3")["epoch_yr"] == 2010.5


def test_plain_names_are_not_designations():
    assert parse_designation("Barnard's Star") is None
