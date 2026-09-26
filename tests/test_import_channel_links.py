import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from import_channel_links import donation_account  # noqa: E402


def test_donation_account_normalization():
    assert donation_account("https://ezdn.app/Foo_VT") == ("easydonate", "foo_vt", "https://easydonate.app/foo_vt")
    assert donation_account("https://www.tipjai.com/abel_vt?x=1") == ("tipjai", "abel_vt", "https://tipjai.com/abel_vt")
    assert donation_account("https://tipnoi.app/kumo") == ("tipnoi", "kumo", "https://tipnoi.app/kumo")
    assert donation_account("https://streamlabs.com/someone/tip")[0] == "streamlabs"
    assert donation_account("https://streamlabs.com/someone") is None
    assert donation_account("https://tipjai.com/discover/vtuber") is None
    assert donation_account("https://tipme.in.th/3dc09395bff1976e") is None  # closed platform
    assert donation_account("https://x.com/someone") is None
