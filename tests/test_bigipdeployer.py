"""
Unit tests for BigipDeployer
"""

import argparse
import os
import posixpath

from pathlib import Path
from typing import Any, List, Optional, Tuple, Type

import pytest
import scp as paramiko_scp  # type: ignore

from invoke.exceptions import UnexpectedExit
from invoke.runners import Result

from certbot_deployer import (
    CERT,
    CERT_FILENAME,
    FULLCHAIN,
    FULLCHAIN_FILENAME,
    INTERMEDIATES_FILENAME,
    KEY_FILENAME,
)
from certbot_deployer import CertificateComponent, Deployer
from certbot_deployer.test_helpers import generate_self_signed_cert
import certbot_deployer_bigip._main as plugin_main
from certbot_deployer_bigip.certbot_deployer_bigip import (
    BigipCertificateBundle,
    BigipDeployer,
    BigipTask,
    CertProfile,
)


HOST: str = "something.domain.tld"
KEY: str = "key"
TEST_PROFILE: CertProfile = CertProfile(name="test_profile", type="client-ssl")
TEST_SYNC_GROUP: str = "test_sync_group"


@pytest.fixture(name="bigip_certificate_bundle", scope="function")
def fixture_bigip_certificate_bundle(tmp_path: Path) -> BigipCertificateBundle:
    """
    Create a temporary Certbot "certificate bundle" in a temp dir for testing.

    It generates the following files:
        - CERT_FILENAME
        - FULLCHAIN_FILENAME
        - INTERMEDIATES_FILENAME
        - KEY_FILENAME

    Note:
        This fixture creates a self-signed certificate. It need only be
        parseable - in production, its cryptographic validity should have just
        been verified by Certbot itself before this script is called.

        The other files are plaintext.

    Returns:
        BigipCertificateBundle: An instance wrapping the temporary certificate
        bundle directory.
    """
    with open(tmp_path / CERT_FILENAME, "w", encoding="utf-8") as certfile:
        certfile.write(generate_self_signed_cert())
    with open(tmp_path / FULLCHAIN_FILENAME, "w", encoding="utf-8") as certfile:
        certfile.write("fullchain")
    with open(tmp_path / INTERMEDIATES_FILENAME, "w", encoding="utf-8") as certfile:
        certfile.write("intermediates")
    with open(tmp_path / KEY_FILENAME, "w", encoding="utf-8") as certfile:
        certfile.write("key")
    return BigipCertificateBundle(path=str(tmp_path))


@pytest.fixture(name="bigip_deployer_base", scope="function")
def fixture_bigip_deployer(
    bigip_certificate_bundle: BigipCertificateBundle,
) -> BigipDeployer:
    """
    Return a BigipDeployer for testing.

    This fixture initializes a BigipDeployer with a temporary certificate bundle,
    but without a sync group or profile for simplicity.
    """
    deployer: BigipDeployer = BigipDeployer(
        host=HOST,
        dest_temp_dir="/remote/path/",
        certificate_bundle=bigip_certificate_bundle,
        sync_group=None,
        profile=None,
    )
    return deployer


@pytest.fixture(name="bigip_deployer_with_profile", scope="function")
def fixture_bigip_deployer_with_profile(
    bigip_certificate_bundle: BigipCertificateBundle,
) -> BigipDeployer:
    """
    Return a BigipDeployer for testing with a specified certificate profile.

    A sample CertProfile object (`TEST_PROFILE`) is assigned to the deployer.
    """
    deployer: BigipDeployer = BigipDeployer(
        host=HOST,
        dest_temp_dir="/remote/path/",
        certificate_bundle=bigip_certificate_bundle,
        sync_group=None,
        profile=TEST_PROFILE,
    )
    return deployer


@pytest.fixture(name="bigip_deployer_with_sync_group", scope="function")
def fixture_bigip_deployer_with_sync_group(
    bigip_certificate_bundle: BigipCertificateBundle,
) -> BigipDeployer:
    """
    Return a BigipDeployer for testing with a specified sync group.

    A sample sync group (`TEST_SYNC_GROUP`) is assigned to the deployer.
    """
    deployer: BigipDeployer = BigipDeployer(
        host=HOST,
        dest_temp_dir="/remote/path/",
        certificate_bundle=bigip_certificate_bundle,
        sync_group=TEST_SYNC_GROUP,
        profile=None,
    )
    return deployer


@pytest.fixture(name="deployer_base_with_expected_tasks", scope="function")
def fixture_deployer_base_with_expected_tasks(
    bigip_deployer_base: BigipDeployer,
) -> Tuple[BigipDeployer, List[BigipTask]]:
    """
    Create a basic BigipDeployer instance with its associated workflow tasks.

    This fixture initializes a BigipDeployer configured with a temporary certificate bundle.
    It also constructs a list of expected BigipTask objects representing the
    deployment steps.

    Returns:
        Tuple[BigipDeployer, List[BigipTask]]: A tuple containing the
        BigipDeployer instance and the list of expected deployment tasks.
    """
    deployer = bigip_deployer_base
    tasks: List[BigipTask] = [
        BigipTask(
            exec_function=deployer.put_bigip_file,
            exec_kwargs={"component": deployer.certificate_bundle.fullchain},
        ),
        BigipTask(
            exec_function=deployer.install_cert,
            exec_kwargs={"component": deployer.certificate_bundle.fullchain},
        ),
        BigipTask(
            exec_function=deployer.verify_cert_installed,
            exec_kwargs={"component": deployer.certificate_bundle.fullchain},
        ),
        BigipTask(
            exec_function=deployer.put_bigip_file,
            exec_kwargs={"component": deployer.certificate_bundle.key},
        ),
        BigipTask(
            exec_function=deployer.install_cert,
            exec_kwargs={"component": deployer.certificate_bundle.key},
        ),
        BigipTask(
            exec_function=deployer.verify_cert_installed,
            exec_kwargs={"component": deployer.certificate_bundle.key},
        ),
        BigipTask(
            exec_function=deployer.zero_bigip_file,
            exec_kwargs={"component": deployer.certificate_bundle.fullchain},
        ),
        BigipTask(
            exec_function=deployer.zero_bigip_file,
            exec_kwargs={"component": deployer.certificate_bundle.key},
        ),
        BigipTask(
            exec_function=deployer.save,
        ),
    ]
    return (deployer, tasks)


@pytest.fixture(name="deployer_with_profile_and_expected_tasks", scope="function")
def fixture_deployer_with_profile_and_expected_tasks(
    deployer_base_with_expected_tasks: Tuple[BigipDeployer, List[BigipTask]],
) -> Tuple[BigipDeployer, List[BigipTask]]:
    """
    Extend the base BigipDeployer fixture with certificate profile configuration.

    This fixture builds upon the basic deployer by assigning a certification
    profile and appending the profile management task to the expected workflow.

    Returns:
        Tuple[BigipDeployer, List[BigipTask]]: A tuple containing the
        BigipDeployer instance with an assigned certificate profile and the
        updated task list.
    """
    deployer: BigipDeployer
    tasks: List[BigipTask]
    deployer, tasks = deployer_base_with_expected_tasks
    tasks.append(
        BigipTask(
            exec_function=deployer.manage_profile,
            exec_kwargs={"component": deployer.certificate_bundle.fullchain},
        )
    )
    deployer.profile = TEST_PROFILE
    return (deployer, tasks)


@pytest.fixture(name="deployer_with_sync_group_and_expected_tasks", scope="function")
def fixture_deployer_with_sync_group_and_expected_tasks(
    deployer_base_with_expected_tasks: Tuple[BigipDeployer, List[BigipTask]],
) -> Tuple[BigipDeployer, List[BigipTask]]:
    """
    Extend the base BigipDeployer with synchronization group configuration.

    This fixture sets a sync group for the deployer and adds sync-related tasks
    to the expected workflow.

    Returns:
        Tuple[BigipDeployer, List[BigipTask]]: A tuple containing the
        BigipDeployer instance with a configured sync group and the updated
        task list.
    """
    deployer: BigipDeployer
    tasks: List[BigipTask]
    deployer, tasks = deployer_base_with_expected_tasks
    tasks.insert(
        0,
        BigipTask(exec_function=deployer.verify_sync),
    )
    tasks.extend(
        [
            BigipTask(
                exec_function=deployer.sync,
            ),
        ]
    )
    deployer.sync_group = "mysyncgroup"
    return (deployer, tasks)


@pytest.fixture(
    name="deployer_with_sync_group_and_profile_and_expected_tasks", scope="function"
)
def fixture_deployer_with_sync_group_and_profile_and_expected_tasks(
    deployer_with_sync_group_and_expected_tasks: Tuple[BigipDeployer, List[BigipTask]],
) -> Tuple[BigipDeployer, List[BigipTask]]:
    """
    Extend the base BigipDeployer with synchronization group configuration AND
    profile configuration.

    This fixture sets a sync group and profile for the deployer and appends the
    sync task to the expected workflow.

    Returns:
        Tuple[BigipDeployer, List[BigipTask]]: A tuple containing the
        BigipDeployer instance with a configured sync group and profile and the updated
        task list.
    """
    deployer: BigipDeployer
    tasks: List[BigipTask]
    deployer, tasks = deployer_with_sync_group_and_expected_tasks
    deployer.profile = TEST_PROFILE
    tasks.insert(
        len(tasks) - 1,
        BigipTask(
            exec_function=deployer.manage_profile,
            exec_kwargs={"component": deployer.certificate_bundle.fullchain},
        ),
    )
    return (deployer, tasks)


@pytest.fixture(name="deployer_and_expected_tasks", scope="function")
def fixture_deployer_and_expected_tasks(
    request: pytest.FixtureRequest,
) -> Tuple[BigipDeployer, List[BigipTask]]:
    """
    Dynamically load and return a BigipDeployer along with its expected workflow tasks.

    This fixture factory utilizes the parameterized fixture name passed by
    indirect pytest parametrization and returns the corresponding deployer
    instance and expected tasks.

    Returns:
        Tuple[BigipDeployer, List[BigipTask]]: The deployer configuration and
        its expected task list.
    """
    return request.getfixturevalue(request.param)


def test_subcommand() -> None:
    """
    Test that the BigipDeployer's subcommand class variable is correctly set.
    """
    assert BigipDeployer.subcommand == "bigip"


def test_static_argparse_post() -> None:
    """
    Test the argument validation logic in BigipDeployer.argparse_post().

    Verifies that:
        - An argparse.ArgumentTypeError is raised if exactly one of the
          following arguments is provided: profile or profile_type.
        - No exception is raised if both are provided or if neither is provided.
    """
    args: argparse.Namespace

    # Verify `--host` is "required" by validation in post
    args = argparse.Namespace()
    with pytest.raises(argparse.ArgumentTypeError):
        BigipDeployer.argparse_post(args=args)

    # Raise when only one of `profile_name` and `profile_type` given
    args = argparse.Namespace(host="val", profile_name=None, profile_type="val")
    with pytest.raises(argparse.ArgumentTypeError):
        BigipDeployer.argparse_post(args=args)
    args = argparse.Namespace(host="val", profile_name="val", profile_type=None)
    with pytest.raises(argparse.ArgumentTypeError):
        BigipDeployer.argparse_post(args=args)

    # Succeed otherwise
    args = argparse.Namespace(host="val", profile_name="val", profile_type="val")
    BigipDeployer.argparse_post(args=args)
    args = argparse.Namespace(host="val", profile_name=None, profile_type=None)
    BigipDeployer.argparse_post(args=args)


@pytest.mark.parametrize(
    # Parametrize fixtures that provide a BigipDeployer and a list of expected
    # workflow Tasks
    "deployer_and_expected_tasks",
    [
        "deployer_base_with_expected_tasks",
        "deployer_with_profile_and_expected_tasks",
        "deployer_with_sync_group_and_expected_tasks",
        "deployer_with_sync_group_and_profile_and_expected_tasks",
    ],
    indirect=True,
    ids=[
        "deployer_base_with_expected_tasks",
        "deployer_with_profile_and_expected_tasks",
        "deployer_with_sync_group_and_expected_tasks",
        "deployer_with_sync_group_and_profile_and_expected_tasks",
    ],
)
def test_workflow(
    deployer_and_expected_tasks: Tuple[BigipDeployer, List[BigipTask]],
) -> None:
    """
    Test that the deployer workflow matches the expected sequence of tasks.

    This test retrieves the workflow generated by BigipDeployer.get_workflow()
    and verifies it matches the expected task list.
    """
    deployer: BigipDeployer
    tasks: List[BigipTask]
    deployer, expected_tasks = deployer_and_expected_tasks
    tasks = deployer.get_workflow()
    assert len(tasks) == len(expected_tasks)
    for task, expected_task in zip(tasks, expected_tasks):
        assert task == expected_task


def test_verify_sync(
    monkeypatch: pytest.MonkeyPatch,
    bigip_deployer_base: BigipDeployer,
) -> None:
    """
    Test the verify_sync function by simulating BIG-IP sync status via tmsh commands.
    """

    bigip_deployer = bigip_deployer_base

    # pylint: disable-next=too-few-public-methods
    class DummyResponse:
        """dummy"""

        def __init__(self, stdout: str) -> None:
            self.stdout: str = stdout

    monkeypatch.setattr(
        bigip_deployer.conn, "run", lambda cmd: DummyResponse("Status: In Sync")
    )
    # Expect no exception when sync status is "In Sync".
    bigip_deployer.verify_sync()

    monkeypatch.setattr(
        bigip_deployer.conn,
        "run",
        lambda cmd: DummyResponse("Status: Bad and not good"),
    )
    with pytest.raises(RuntimeError):
        bigip_deployer.verify_sync()


def test_put_file(
    monkeypatch: pytest.MonkeyPatch,
    bigip_deployer_base: BigipDeployer,
) -> None:
    """
    Test deploying files to the remote BIG-IP via scp.
    """
    bigip_deployer = bigip_deployer_base
    calls: List[Tuple[str, str]] = []

    def fake_scp(localpath: str, remotepath: str) -> None:
        nonlocal calls
        calls.append((localpath, remotepath))

    monkeypatch.setattr(bigip_deployer, "_scp", fake_scp)
    component: CertificateComponent = bigip_deployer.certificate_bundle.cert
    bigip_deployer.put_bigip_file(component=component)
    assert len(calls) == 1
    assert calls[0] == (
        component.path,
        posixpath.join(bigip_deployer.dest_temp_dir, component.filename),
    )


@pytest.mark.parametrize(
    "transport_ready",
    [
        True,
        False,
    ],
    ids=[
        "Transport not created yet before `_scp` is called",
        "Transport already created before `_scp` is called",
    ],
)
def test_scp(
    monkeypatch: pytest.MonkeyPatch,
    bigip_deployer_base: BigipDeployer,
    transport_ready: bool,
) -> None:
    """
    Mock the paramiko scp and ensure our scp method tries to
    upload the right files to the right host

    additionally verify that the connection transport is opened when transport
    is not ready
    """
    bigip_deployer = bigip_deployer_base
    localfile: str = "LOCALFILE"
    remotefile: str = "REMOTEFILE"
    put_count: int = 0
    transport_open_count: int = 0

    monkeypatch.setattr(bigip_deployer.conn, "transport", transport_ready)

    def mock_conn_open() -> None:
        nonlocal transport_open_count
        transport_open_count += 1

    # pylint: disable=missing-function-docstring
    # pylint: disable=missing-class-docstring
    # pylint: disable=too-few-public-methods
    class MockSCPClient:
        def __init__(self, transport: str) -> None:
            pass

        # pylint: disable-next=unused-argument
        def put(self, localpath: str, remotepath: str) -> None:
            nonlocal put_count
            put_count += 1
            assert localpath == localfile
            assert remotepath == remotefile

        def close(self) -> None:
            pass

    # pylint: enable=too-few-public-methods
    # pylint: enable=missing-class-docstring
    # pylint: enable=missing-function-docstring

    monkeypatch.setattr(paramiko_scp, "SCPClient", MockSCPClient)
    monkeypatch.setattr(bigip_deployer.conn, "open", mock_conn_open)
    # pylint: disable-next=protected-access
    bigip_deployer._scp(localfile, remotefile)
    assert put_count == 1
    if not transport_ready:
        assert (
            transport_open_count == 1
        ), "Connection was not yet opened and should have been opened before doing SCP"
    else:
        assert (
            transport_open_count == 0
        ), "Connection was already opened and should not have been opened before doing SCP"


@pytest.mark.parametrize(
    # Parametrize to test the different types of certificate file that we try
    # to install on the BIG-IP
    "component_label, bigip_cert_type",
    [
        (CERT, CERT),
        (FULLCHAIN, CERT),
        (KEY, KEY),
    ],
    ids=[
        "Install CERT as a certificate",
        "Install FULLCHAIN as a certificate",
        "Install KEY as a key",
    ],
)
def test_install_cert(
    monkeypatch: pytest.MonkeyPatch,
    bigip_deployer_base: BigipDeployer,
    component_label: str,
    bigip_cert_type: str,
) -> None:
    """
    Test installing certificates on the remote BIG-IP via tmsh commands.
    """
    bigip_deployer = bigip_deployer_base
    commands: List[str] = []

    def fake_run(cmd: str) -> None:
        nonlocal commands
        commands.append(cmd)

    monkeypatch.setattr(bigip_deployer.conn, "run", fake_run)
    component: CertificateComponent = getattr(
        bigip_deployer.certificate_bundle, component_label
    )
    remote_path: str = posixpath.join(bigip_deployer.dest_temp_dir, component.filename)
    expected_cmd: str = (
        f"install /sys crypto {bigip_cert_type} {bigip_deployer.certificate_bundle.name} "
        f"from-local-file {remote_path}"
    )
    bigip_deployer.install_cert(component=component)
    assert len(commands) == 1
    assert commands[0] == expected_cmd

    def fake_run_fail(cmd: str) -> None:
        raise UnexpectedExit(Result())

    monkeypatch.setattr(bigip_deployer.conn, "run", fake_run_fail)
    with pytest.raises(RuntimeError):
        bigip_deployer.install_cert(component=component)


@pytest.mark.parametrize(
    # Parametrize to test the different types of certificate file that we try
    # to install on the BIG-IP
    "component_label, bigip_cert_type",
    [
        (CERT, CERT),
        (FULLCHAIN, CERT),
        (KEY, KEY),
    ],
    ids=[
        "Verify CERT as a certificate",
        "Verify FULLCHAIN as a certificate",
        "Verify KEY as a key",
    ],
)
def test_verify_cert_installed(
    monkeypatch: pytest.MonkeyPatch,
    bigip_deployer_base: BigipDeployer,
    component_label: str,
    bigip_cert_type: str,
) -> None:
    """
    Test verifying certs on the BIG-IP
    """
    bigip_deployer = bigip_deployer_base
    commands: List[str] = []

    component: CertificateComponent = getattr(
        bigip_deployer.certificate_bundle, component_label
    )
    expected_cmd: str = (
        f"list /sys crypto {bigip_cert_type} {bigip_deployer.certificate_bundle.name}"
    )

    # pylint: disable-next=too-few-public-methods
    class FakeResult:
        """Fake the results from invoke's run()"""

        def __init__(self, stdout: str) -> None:
            self.stdout: str = stdout

    def fake_run(cmd: str) -> FakeResult:
        nonlocal commands
        commands.append(cmd)
        return FakeResult(bigip_deployer.certificate_bundle.fingerprint)

    monkeypatch.setattr(bigip_deployer.conn, "run", fake_run)
    bigip_deployer.verify_cert_installed(component=component)
    assert len(commands) == 1
    assert commands[0] == expected_cmd

    def fake_run_no_fingerprint_in_output(_: str) -> FakeResult:
        return FakeResult("no fingerprints to be found here")

    monkeypatch.setattr(bigip_deployer.conn, "run", fake_run_no_fingerprint_in_output)
    if bigip_cert_type == CERT:
        with pytest.raises(RuntimeError):
            bigip_deployer.verify_cert_installed(component=component)

    def fake_run_unexpected_exit(cmd: str) -> None:
        raise UnexpectedExit(Result())

    monkeypatch.setattr(bigip_deployer.conn, "run", fake_run_unexpected_exit)
    with pytest.raises(RuntimeError):
        bigip_deployer.verify_cert_installed(component=component)


def test_zero_file(
    monkeypatch: pytest.MonkeyPatch,
    bigip_deployer_base: BigipDeployer,
) -> None:
    """
    Test deploying empty files to the remote BIG-IP via scp.
    """
    bigip_deployer = bigip_deployer_base
    calls: List[Tuple[str, str]] = []

    def fake_scp(localpath: str, remotepath: str) -> None:
        assert os.path.getsize(localpath) == 0
        nonlocal calls
        calls.append((localpath, remotepath))

    monkeypatch.setattr(bigip_deployer, "_scp", fake_scp)

    component: CertificateComponent = bigip_deployer.certificate_bundle.cert
    bigip_deployer.zero_bigip_file(component=component)
    assert len(calls) == 1
    call: Tuple[str, str] = calls[0]
    called_remote_filepath: str
    _, called_remote_filepath = call
    assert called_remote_filepath == posixpath.join(
        bigip_deployer.dest_temp_dir, component.filename
    )


@pytest.mark.parametrize(
    # The method being tested will `run()` to check if the profile exists, and
    # *then* run either `create` or `modify`
    # Parametrize to tell the test which steps to raise on, and what operations
    # to expect
    "runs_to_raise_on, expected_operations, expect_exception",
    [
        # Successes
        ([], ["list", "modify"], False),
        ([0], ["list", "create"], False),
        # Failures
        ([1], ["list", "modify"], True),
        ([0, 1], ["list", "create"], True),
    ],
    ids=[
        "`list` to see if profile exists, and then succeed at `modify`",
        "`list` to see if profile exists (nope), and then succeed at `create`",
        #
        "`list` to see if profile exists, and then raise when attempting `modify`",
        "`list` to see if profile exists, and then raise when attempting `create`",
    ],
)
def test_manage_profile(
    monkeypatch: pytest.MonkeyPatch,
    bigip_deployer_with_profile: BigipDeployer,
    runs_to_raise_on: List[int],
    expected_operations: List[str],
    expect_exception: bool,
) -> None:
    """
    Test managing (creating or modifying) profiles on BIG-IP.

    This test verifies the behavior of the `manage_profile` method, which
    checks if a profile exists on the BIG-IP device and either modifies it
    or creates it if it does not exist.

    Parameters:
        runs_to_raise_on (List[int]): Indices of commands on which to simulate failure
        expected_operations (List[str]): Expected sequence of operations
        expect_exception (bool): Whether an exception is expected on `run()`
    """
    bigip_deployer = bigip_deployer_with_profile
    commands: List[str] = []

    def fake_run(cmd: str) -> None:
        nonlocal commands
        commands.append(cmd)
        run_count: int = len(commands) - 1
        if run_count in runs_to_raise_on:
            raise UnexpectedExit(Result())

    monkeypatch.setattr(bigip_deployer.conn, "run", fake_run)
    if expect_exception:
        with pytest.raises(RuntimeError):
            bigip_deployer.manage_profile()
    else:
        bigip_deployer.manage_profile()

    assert len(expected_operations) == len(commands)

    for command, expected_operation in zip(commands, expected_operations):
        operation: str
        args: str
        operation, args = command.split(" ", 1)
        assert operation == expected_operation
        assert bigip_deployer.profile is not None
        if operation == "list":
            assert args == (
                f"/ltm profile {bigip_deployer.profile.type} "
                f"{bigip_deployer.profile.name}"
            )
        else:
            assert args == (
                f"/ltm profile {bigip_deployer.profile.type} "
                f"{bigip_deployer.profile.name} cert "
                f"{bigip_deployer.certificate_bundle.name} key "
                f"{bigip_deployer.certificate_bundle.name}"
            )


def test_sync(
    monkeypatch: pytest.MonkeyPatch,
    bigip_deployer_with_sync_group: BigipDeployer,
) -> None:
    """
    Test the `sync` method of BigipDeployer.

    This test verifies that the `sync` method correctly runs the appropriate
    command to synchronize the BIG-IP configuration and handles errors
    appropriately.
    """
    commands: List[str] = []
    bigip_deployer = bigip_deployer_with_sync_group

    def fake_run(cmd: str) -> None:
        nonlocal commands
        commands.append(cmd)

    monkeypatch.setattr(bigip_deployer.conn, "run", fake_run)
    expected_cmd: str = f"run /cm config-sync to-group {bigip_deployer.sync_group}"

    # Test for a successful run
    bigip_deployer.sync()
    assert len(commands) == 1
    assert commands[0] == expected_cmd

    commands = []

    def fake_run_fail(cmd: str) -> None:
        raise UnexpectedExit(Result())

    monkeypatch.setattr(bigip_deployer.conn, "run", fake_run_fail)
    with pytest.raises(RuntimeError):
        bigip_deployer.sync()


def test_static_entrypoint(
    monkeypatch: pytest.MonkeyPatch,
    bigip_certificate_bundle: BigipCertificateBundle,
) -> None:
    """
    Test the `entrypoint` method of BigipDeployer.

    This test ensures that the `entrypoint` method correctly executes the
    workflow tasks defined for the deployer.
    """
    run_count: int = 0

    def fake_task() -> None:
        nonlocal run_count
        run_count += 1

    tasks: List[BigipTask] = [
        BigipTask(exec_function=fake_task),
        BigipTask(exec_function=fake_task),
    ]

    def fake_get_workflow(_: Any) -> List[BigipTask]:
        return tasks

    monkeypatch.setattr(BigipDeployer, "get_workflow", fake_get_workflow)
    args: argparse.Namespace = argparse.Namespace(
        cert_name=None,
        dest_temp_dir=None,
        dry_run=False,
        host="somewhere.domain.tld",
        profile_name=None,
        profile_type=None,
        renewed_lineage=bigip_certificate_bundle.path,
        sync_group=None,
        user=None,
    )
    BigipDeployer.entrypoint(args=args, certificate_bundle=bigip_certificate_bundle)
    assert run_count == len(tasks)


def test_dry_run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: Any,
    bigip_certificate_bundle: BigipCertificateBundle,
) -> None:
    """
    Verify that our entrypoint prints out what it *would* do and does not run anything
    """
    run_count: int = 0

    def fake_task() -> None:
        nonlocal run_count
        run_count += 1

    task_names: List[str] = [
        "mytask1",
        "mytask2",
    ]
    tasks: List[BigipTask] = []
    for task_name in task_names:
        tasks.append(BigipTask(exec_function=fake_task, name=task_name))

    def fake_get_workflow(_: Any) -> List[BigipTask]:
        return tasks

    monkeypatch.setattr(BigipDeployer, "get_workflow", fake_get_workflow)
    args: argparse.Namespace = argparse.Namespace(
        cert_name=None,
        dest_temp_dir=None,
        dry_run=True,
        host="somewhere.domain.tld",
        profile_name=None,
        profile_type=None,
        renewed_lineage=bigip_certificate_bundle.path,
        sync_group=None,
        user=None,
    )
    BigipDeployer.entrypoint(args=args, certificate_bundle=bigip_certificate_bundle)

    assert run_count == 0
    stdout: str = capsys.readouterr().out
    for task_name in task_names:
        assert task_name in stdout
    print(stdout)


def test_main_delegation(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify that our `main()` hands control off to the framework when called
    directly by mocking the framework's `main()` and comparing the passed
    args/deployers
    """
    called_argv: list = []
    called_deployers: Optional[List[Type[Deployer]]]

    def fake_framework_main(
        argv: list, deployers: Optional[List[Type[Deployer]]] = None
    ) -> None:
        nonlocal called_argv
        nonlocal called_deployers
        called_argv = argv
        called_deployers = deployers

    argv: List[str] = ["-h"]
    expected_argv: List[str] = [BigipDeployer.subcommand, "-h"]
    expected_deployers: Optional[List[Type[Deployer]]] = [BigipDeployer]

    monkeypatch.setattr(
        plugin_main,
        "framework_main",
        fake_framework_main,
    )
    plugin_main.main(argv=argv)
    assert called_argv == expected_argv
    assert called_deployers == expected_deployers
