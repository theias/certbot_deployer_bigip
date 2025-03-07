"""
Unit tests for misc bits
"""

import subprocess

from typing import List

import pytest

from certbot_deployer_bigip.certbot_deployer_bigip import scp

HOST: str = "something.domain.tld"
LOCALFILE: str = "LOCALFILE"
REMOTEFILE: str = "REMOTEFILE"
PROCERR: subprocess.CalledProcessError = subprocess.CalledProcessError(
    returncode=255,
    cmd=["cmd", "arg", "arg"],
    output="",
    stderr="",
)


def test_scp_lt90(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Mock the external command `scp` to behave as scp from openssh-client <9.0
    and NOT accept `-O`
    Should fail when `-O` is passed and then fall back to without
    so we should see `scp` called in that order
    """
    called: List[str] = []

    def scp_fail_dash_o(
        cmd: List[str],
        # pylint: disable-next=unused-argument
        capture_output: bool = True,
        # pylint: disable-next=unused-argument
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Simulate `scp` <9.0
        """
        nonlocal called
        called.append(" ".join(cmd))
        if "-O" in cmd:
            raise PROCERR
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="scp success something something",
            stderr="scp stderr something something",
        )

    monkeypatch.setattr(subprocess, "run", scp_fail_dash_o)
    scp(HOST, LOCALFILE, REMOTEFILE)
    assert called[0] == f"scp -O {LOCALFILE} {HOST}:{REMOTEFILE}"
    assert called[1] == f"scp {LOCALFILE} {HOST}:{REMOTEFILE}"


def test_scp_gt90(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Mock the external command `scp` to behave as scp from openssh-client >9.0
    and accept `-O`
    and let it succeed in one go
    """
    called: List[str] = []

    def scp_succeed_dash_o(
        cmd: List[str],
        # pylint: disable-next=unused-argument
        capture_output: bool = True,
        # pylint: disable-next=unused-argument
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        nonlocal called
        called.append(" ".join(cmd))
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="scp success something something",
            stderr="scp stderr something something",
        )

    monkeypatch.setattr(subprocess, "run", scp_succeed_dash_o)
    scp(HOST, LOCALFILE, REMOTEFILE)
    assert called[0] == f"scp -O {LOCALFILE} {HOST}:{REMOTEFILE}"


def test_scp_raises_on_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Mock the external command `scp` fail and ensure our tested function raises
    appropriately
    """

    def scp_always_fail(
        cmd: List[str],
        # pylint: disable-next=unused-argument
        capture_output: bool = True,
        # pylint: disable-next=unused-argument
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        raise PROCERR

    monkeypatch.setattr(subprocess, "run", scp_always_fail)
    with pytest.raises(RuntimeError):
        scp(HOST, LOCALFILE, REMOTEFILE)
