"""
Unit tests for the `BigipCertificateBundle` class
"""

from pathlib import Path

import pytest

from certbot_deployer import CERT_FILENAME
from certbot_deployer.test_helpers import COMMON_NAME, NOT_VALID_AFTER
from certbot_deployer_bigip.certbot_deployer_bigip import BigipCertificateBundle

# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=too-few-public-methods
# pylint: disable=attribute-defined-outside-init

STATIC_TEST_CERT: str = """-----BEGIN CERTIFICATE-----
MIIC2TCCAcGgAwIBAgIUD5bm1RAbxJ7dqTIlZL2GwF+B8FkwDQYJKoZIhvcNAQEL
BQAwGzEZMBcGA1UEAwwQdGVzdCBjb21tb24gbmFtZTAgFw0yMDAxMDEwMDAwMDBa
GA8yMDk5MDEwMTAwMDAwMFowGzEZMBcGA1UEAwwQdGVzdCBjb21tb24gbmFtZTCC
ASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMdnRQoxdW9vrQcXlH1MsDuA
Vi/mc/Tq6LJB6wKoaHLiT+aVa0Md1IQtlceL/Y9OMdjWiRR5xex2lsRZ0IdcMO+7
1txrG2u2NmZ6HSG8CyzMZmPbUClLYySwv7aLgj76Q3I3E/WVnatja9W1PQxSw0Sz
dDsC2L5jc4hiD/tCAR0PvGv8eiAnjYhIsKfU5Odcoe5dw4YGqmYRbcBYqRAisQgy
ekB1VXqsRlmqm+HQSwwon7rL0p4Nzaub7ZTM7qsc8dWs3RFZlWzFRrfrwo2Le7zh
gPZdul5rz9JUcBttOVqZVES8xKG3+6iLU6/RlGsWFyyaflxWjtU0GAJZWW/ho28C
AwEAAaMTMBEwDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAk5N/
c6nfPbCMzvs1SGzkTyN6gyY7dnZwuIPSbr0iN1+tWC3UJclGRPCMqD62/T+UjKYA
6VNyTkUqMmib0qbHo67kfidEGe+A1BV9v0MxdVaa8WAop7D6PtHMLNHiIQBYkc02
QvcY6OT8evsG6zbiR8+Tj4pMIBom0AHTt3HqSfoynEpyonwutVJxwQpAqs6ZxAGT
mgNgBLNbTLrwk5ScmaASmjl3Ua24QRT48oK16Gz/JjrRv1TgEl7NBX0fPuljjyhw
qSlAqJRr0ANRfarf+M62Cq9qV/JzKFDGlPvAY7aQemMaIXrqwEPuLRP3SvBL+NBm
ahH6YxA25wiuaynPpw==
-----END CERTIFICATE-----
"""
STATIC_TEST_CERT_FINGERPRINT: str = (
    # pylint: disable-next=line-too-long
    "SHA256/44:D6:7E:66:11:B4:16:8C:5A:FD:36:F1:24:8E:18:30:60:5F:98:47:7C:1C:B3:1B:9F:76:74:8F:A5:62:9D:92"
)


@pytest.fixture(name="setup_bundle_path", scope="function")
def fixture_setup_bundle_path(tmp_path: Path) -> Path:
    """
    Given a pytest temp folder, reate a "valid" certificate there for the
    BigipCertificateBundle class to operate upon
    """
    with open(tmp_path / CERT_FILENAME, "w", encoding="utf-8") as cert_file:
        cert_file.write(STATIC_TEST_CERT)
    return tmp_path


def test_bundle_fingerprint(setup_bundle_path: Path) -> None:
    """
    Test that the cert bundle creates its fingerprint as the f5 expects

    we'll use a hard-coded cert and fingerprint instead of jut re-implementing
    the fingerprint code from the module
    """
    bundle: BigipCertificateBundle = BigipCertificateBundle(path=str(setup_bundle_path))
    assert bundle.fingerprint == STATIC_TEST_CERT_FINGERPRINT


def test_bundle_autoname(setup_bundle_path: Path) -> None:
    """test"""
    bundle: BigipCertificateBundle = BigipCertificateBundle(path=str(setup_bundle_path))
    assert bundle.name == f"{COMMON_NAME}.{NOT_VALID_AFTER.isoformat()}"
