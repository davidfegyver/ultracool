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


def test_prefixed_spiff_types_are_searchable():
    from app import ucd
    assert ucd.spt_num("d/sdT1") == 21 and ucd.spt_num("esdL8 pec") == 18 and ucd.spt_num("sdM9.5") == 9.5
    assert not any(v != v for v in ucd.SPT)  # every SPIFF autotype parses (275 subdwarf types used not to)
    assert any(r["spiff_autotype"].startswith("sdT4") for r in ucd.search("T4", "T4", limit=5000))
