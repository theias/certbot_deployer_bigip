"""
BIG-IP specific deployer code
"""

import argparse
import logging
import os
import posixpath
import re
import sys
import subprocess
import tempfile
import textwrap

# import sys
import warnings


from collections import namedtuple
from typing import Any, Callable, ClassVar, Dict, Iterable, List, Optional

import paramiko  # type: ignore
import scp as paramiko_scp  # type: ignore

# Suppress warnings thanks to old Python and fabric
# pylint: disable-next=duplicate-code
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=UserWarning)
    from cryptography.utils import CryptographyDeprecationWarning
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from fabric import Config, Connection  # type:ignore
from invoke.exceptions import UnexpectedExit

from certbot_deployer import main as framework_main
from certbot_deployer import Deployer, CertificateBundle, CertificateComponent
from certbot_deployer_bigip.meta import __description__

BIGIP_FINGERPRINT_ALGO: str = "SHA256"
BIGIP_FINGERPRINT_ALGO_FUNC: Callable = hashes.SHA256


CertProfile = namedtuple("CertProfile", "name type")


# pylint: disable-next=too-few-public-methods
class BigipCertificateBundle(CertificateBundle):
    """
    CertificateBundle but with the specific fingerprint format used by the F5
    """

    def __init__(self, *args: Any, name: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        safe_name: str = re.sub(r"[^.a-zA-Z0-9_-]", "_", self.common_name)
        self.name = f"{safe_name}.{self.expires}" if name is None else name
        self.fingerprint: str = self._fingerprint(self.certdata)

    @staticmethod
    def _fingerprint(certdata: x509.Certificate) -> str:
        """
        Take an x509 cert obj and return the fingerprint in the format used by
        the BIG-IP
        """
        fingerprint: str = (
            certdata.fingerprint(BIGIP_FINGERPRINT_ALGO_FUNC()).hex().upper()
        )
        fingerprint = f"{BIGIP_FINGERPRINT_ALGO}/" + ":".join(
            fingerprint[i : i + 2] for i in range(0, len(fingerprint), 2)
        )
        return fingerprint


class BigipTask:
    """
    @ single BIG-IP task for the deployer to run
    """

    # pylint: disable-next=too-many-arguments
    def __init__(
        self,
        exec_function: Callable,
        name: Optional[str] = None,
        exec_args: Optional[Iterable[Any]] = None,
        exec_kwargs: Optional[Dict[str, Any]] = None,
        revert_function: Optional[Callable] = None,
        revert_args: Optional[Iterable[Any]] = None,
        revert_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """init"""
        self.name: Optional[str] = name
        self.exec_function: Callable = exec_function
        self.exec_kwargs: Dict[str, Any] = (
            exec_kwargs if exec_kwargs is not None else {}
        )
        self.exec_args: Iterable[Any] = exec_args if exec_args is not None else []
        self.revert_function: Optional[Callable] = revert_function
        self.revert_kwargs: Iterable[Any] = (
            revert_kwargs if revert_kwargs is not None else []
        )
        self.revert_args: Iterable[Any] = revert_args if revert_args is not None else []

    def __eq__(self, othertask: object) -> bool:
        if not isinstance(othertask, BigipTask):
            return NotImplemented
        res: bool
        try:
            res = (
                self.exec_args,
                self.exec_function,
                self.exec_kwargs,
                self.revert_args,
                self.revert_function,
                self.revert_kwargs,
            ) == (
                othertask.exec_args,  # type:ignore
                othertask.exec_function,  # type:ignore
                othertask.exec_kwargs,  # type:ignore
                othertask.revert_args,  # type:ignore
                othertask.revert_function,  # type:ignore
                othertask.revert_kwargs,  # type:ignore
            )
        except AttributeError:
            res = False
        return res

    def execute(self, *args: Any, **kwargs: Any) -> None:
        """
        Entrypoint for this task to actually run
        """
        modargs: list = list(args)
        modargs.extend(self.exec_args)
        modkwargs = dict(kwargs)
        modkwargs.update(self.exec_kwargs)
        self.exec_function(*modargs, **modkwargs)

    def revert(self, *args: Any, **kwargs: Any) -> None:
        """
        Revert the corresponding changes if possible
        """
        if self.revert_function is not None:
            self.revert_function(*args, **kwargs)


# pylint: disable-next=too-many-instance-attributes
class BigipDeployer(Deployer):
    """
    BigIP cert deployer
    """

    subcommand: ClassVar[str] = "bigip"

    # pylint: disable-next=too-many-arguments
    def __init__(
        self,
        *,
        host: str,
        dest_temp_dir: str,
        certificate_bundle: BigipCertificateBundle,
        sync_group: Optional[str],
        profile: Optional[CertProfile],
    ) -> None:
        self.host: str = host
        self.dest_temp_dir: str = dest_temp_dir
        self.sync_group: Optional[str] = sync_group
        self.certificate_bundle: BigipCertificateBundle = certificate_bundle
        self.profile: Optional[CertProfile] = profile
        logging.debug("BigIp config initialized as: `%s`", str(self))
        self.operations: list = []

        self.conn: Connection = Connection(
            host=self.host,
            config=Config(
                overrides={
                    "run": {"hide": True},
                }
            ),
        )

    @staticmethod
    def register_args(*, parser: argparse.ArgumentParser) -> None:
        """
        Modify argparse subparser for this deployer target
        """
        parser.formatter_class = argparse.RawDescriptionHelpFormatter
        parser.description = f"""BIG-IP subcommand
        {__description__}
        """
        parser.epilog = textwrap.dedent(
            """
        Examples:

        All examples assume the tool is being run as a Certbot deploy hook, and
        the environment variable `RENEWED_LINEAGE` points to the live
        certificate directory just updated by Certbot.

            # Install certificate on the BIG-IP device named with its expiry timestamp
            # as `host.domain.tld.YYY-MM-DDTHH:MM:SS` (the default)

            %(prog)s --host bigip.domain.tld

            # Install certificate on the BIG-IP device and then synchronize
            # device changes to a device group

            %(prog)s --host bigip.domain.tld --sync-group yoursyncgroup

            # Install certificate on the BIG-IP device and then associate it
            # with a client-ssl profile. If the profile does not exist, it will be created.

            %(prog)s --host bigip.domain.tld --profile-name yourprofile \\
                --profile-type client-ssl

            # Print out the deployment tasks that would be taken, but do not run them

            %(prog)s --host bigip.domain.tld --dry-run

        """
        )

        parser.add_argument(
            "--host",
            "-H",
            default=os.environ.get("HOST", None),
            help=("BIG-IP host to target with changes."),
            type=str,
        )

        parser.add_argument(
            "--dest-temp-dir",
            "-t",
            default=os.environ.get("DEST_TEMP_DIR", "/var/tmp"),
            help=(
                "The temp path on the BIG-IP to use when uploading the certificates for "
                "installation. This tool will try to zero out the certificates at the end "
                "of the run once they are ingested into the BIG-IP config, but you should "
                'probably try to put them in a "safe" place. Default: `/var/tmp`'
            ),
            type=str,
        )

        parser.add_argument(
            "--cert-name",
            "-c",
            default=None,
            help=(
                "The name to give the certificate objects on the BIG-IP. If not given, "
                "this tool will use the Common Name from the certificate with the "
                "ISO8601-formatted `Not After` value appended, e.g. "
                "`host.domain.tld.YYY-MM-DDTHH:MM:SS`"
            ),
            type=str,
        )

        parser.add_argument(
            "--profile-name",
            "-p",
            help=(
                "The name of the profile to modify/create to use the deployed certificate"
                "If given, the corresponding `--profile-type` is also required. If "
                "neither are given, this tool will not create/modify any profiles."
            ),
            type=str,
        )

        parser.add_argument(
            "--profile-type",
            "-r",
            help=(
                "The type of profile to create if necessary e.g. `client-ssl`. See "
                "BIG-IP docs for details on all profile types. If given, the "
                "corresponding `--profile-name` is also required. If neither are given, "
                "this tool will not create/modify any profiles."
            ),
            type=str,
        )

        parser.add_argument(
            "--sync-group",
            "-s",
            help=(
                "The sync-group to synchronize to after the certificates are deployed. "
                "This tool will not try to sync the BIG-IP node if this argument is not "
                "given"
            ),
            type=str,
        )

        parser.add_argument(
            "--dry-run",
            "-d",
            action="store_true",
            default=False,
            help=(
                "Report the workflow steps that would run without actually running them"
            ),
        )

    def __str__(self) -> str:
        """represent self"""
        return str(vars(self))

    @staticmethod
    def argparse_post(*, args: argparse.Namespace) -> None:
        """
        Checks for after arguments are otherwise fully processed
        """
        args_vars: Dict[str, Any] = vars(args)
        if [
            args_vars.get("profile_name"),
            args_vars.get("profile_type"),
        ].count(None) == 1:
            raise argparse.ArgumentTypeError(
                "If either `--profile` or `--profile-type` are passed, both are required."
            )
        if not args_vars.get("host"):
            raise argparse.ArgumentTypeError("`--host/H is required")

    def get_workflow(self) -> List[BigipTask]:
        """
        Return workflow for this deployer
        """
        tasks: List[BigipTask] = []
        if self.sync_group is not None:
            tasks.append(BigipTask(name="Verify Sync", exec_function=self.verify_sync))
        tasks.extend(
            [
                BigipTask(
                    name="Put cert file to remote",
                    exec_function=self.put_bigip_file,
                    exec_kwargs={"component": self.certificate_bundle.fullchain},
                ),
                BigipTask(
                    name="Install cert",
                    exec_function=self.install_cert,
                    exec_kwargs={"component": self.certificate_bundle.fullchain},
                ),
                BigipTask(
                    name="Verify cert installed",
                    exec_function=self.verify_cert_installed,
                    exec_kwargs={"component": self.certificate_bundle.fullchain},
                ),
                BigipTask(
                    name="Put key file to remote",
                    exec_function=self.put_bigip_file,
                    exec_kwargs={"component": self.certificate_bundle.key},
                ),
                BigipTask(
                    name="Install key",
                    exec_function=self.install_cert,
                    exec_kwargs={"component": self.certificate_bundle.key},
                ),
                BigipTask(
                    name="Verify key installed",
                    exec_function=self.verify_cert_installed,
                    exec_kwargs={"component": self.certificate_bundle.key},
                ),
                BigipTask(
                    name="Zero out cert file on remote",
                    exec_function=self.zero_bigip_file,
                    exec_kwargs={"component": self.certificate_bundle.fullchain},
                ),
                BigipTask(
                    name="Zero out key file on remote",
                    exec_function=self.zero_bigip_file,
                    exec_kwargs={"component": self.certificate_bundle.key},
                ),
                BigipTask(
                    name="Save running config to disk",
                    exec_function=self.save,
                ),
            ]
        )
        if self.profile is not None:
            tasks.append(
                BigipTask(
                    name="Create/modify profile",
                    exec_function=self.manage_profile,
                    exec_kwargs={"component": self.certificate_bundle.fullchain},
                )
            )
        if self.sync_group is not None:
            tasks.append(
                BigipTask(
                    name="Sync",
                    exec_function=self.sync,
                ),
            )
        return tasks

    # pylint: disable-next=unused-argument
    def verify_sync(self, *args: Any, **kwargs: Any) -> None:
        """
        Ensure in sync
        """
        try:
            # Check node sync status
            logging.info("Checking sync status on remote...")
            cmd: str = "show /cm sync-status"
            logging.debug("`%s`", cmd)
            res = self.conn.run(cmd)
            if not re.search("^Status.*In Sync$", res.stdout, re.I | re.MULTILINE):
                raise RuntimeError(
                    (
                        "BIG-IP configuration out of sync. Cannot continue. All "
                        "further operations aborted."
                    )
                )
        except UnexpectedExit as err:
            raise RuntimeError(
                "Failed checking sync status. Aborting all further operations."
            ) from err

    def _scp(self, localpath: str, remotepath: str) -> None:
        """
        Send a file via SCP.

        In general these days, SCP tools actually use the SFTP protocol. This
        includes the Fabric module on which we rely for running remote
        commands.

        For our target F5 BIG-IP devices, the opposite is true - *only* the SCP
        protocol (such as it is) is supported for `tmsh` users:

        https://my.f5.com/manage/s/article/K22885182

        So this method utilizes the separate `scp` module to implement the SCP
        protocol which requires a tiny bit of extra handling.
        """
        if not self.conn.transport:
            # The connection "transport," which we need for our scp client, may
            # not exist yet if no commands have yet run over than connection
            self.conn.open()
        # Avoiding `with ..as` here because though it would be more elegant, it
        # would make testing a bit more complex, requiring it to implement a
        # context manager and meh let's not
        scp_client = paramiko_scp.SCPClient(self.conn.transport)
        scp_client.put(localpath, remotepath)
        scp_client.close()

    def put_bigip_file(
        # pylint: disable-next=unused-argument
        self,
        component: CertificateComponent,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Put the cert or key on the remote
        """
        logging.info(
            "Putting %s `%s` over scp to `%s`",
            component.label,
            component.path,
            self.dest_temp_dir,
        )
        self._scp(
            localpath=component.path,
            remotepath=posixpath.join(self.dest_temp_dir, component.filename),
        )

    def install_cert(
        # pylint: disable-next=unused-argument
        self,
        component: CertificateComponent,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Install cert

        Note that any cert, full-chain or leaf, is still given the type `cert`
        in the TMSH install command
        """
        remote_filepath: str = posixpath.join(self.dest_temp_dir, component.filename)
        bigip_cert_type = "cert" if component.label in ["cert", "fullchain"] else "key"
        try:
            # Install the cert
            logging.info("Installing %s", bigip_cert_type)
            cmd: str = (
                f"install /sys crypto {bigip_cert_type} {self.certificate_bundle.name} "
                f"from-local-file {remote_filepath}"
            )
            logging.debug("`%s`", cmd)
            self.conn.run(cmd)
        except UnexpectedExit as err:
            raise RuntimeError(
                f"Failed installing {component.label} `{self.certificate_bundle.name}` "
                "on remote"
            ) from err

    def verify_cert_installed(
        # pylint: disable-next=unused-argument
        self,
        component: CertificateComponent,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Verify cert
        """
        bigip_cert_type = "cert" if component.label in ["cert", "fullchain"] else "key"
        try:
            # Verify the cert installed
            cmd: str = (
                f"list /sys crypto {bigip_cert_type} {self.certificate_bundle.name}"
            )
            logging.debug("`%s`", cmd)
            res = self.conn.run(cmd)
            if (
                bigip_cert_type == "cert"
                and not self.certificate_bundle.fingerprint in res.stdout
            ):
                # Unfortunately we don't really have a way to verify the state
                # of the key via `tmsh` other than that it is present by name,
                # but at least we can verify the cert
                raise RuntimeError(
                    "Failed to match certificate fingerprint in "
                    f"`{self.certificate_bundle.name}` on remote"
                )
        except UnexpectedExit as err:
            raise RuntimeError(
                f"Failed verifying {bigip_cert_type} `{self.certificate_bundle.name}` "
                "present on remote"
            ) from err

    def zero_bigip_file(
        # pylint: disable-next=unused-argument
        self,
        component: CertificateComponent,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        "Wipe" file on remote by zeroing it out, for inability to just remove the
        file without admin
        """
        remote_filepath: str = posixpath.join(self.dest_temp_dir, component.filename)
        with tempfile.NamedTemporaryFile(mode="r") as emptyfile:
            logging.info(
                "Putting empty file `%s` to remote `%s` over scp...",
                emptyfile.name,
                remote_filepath,
            )
            self._scp(
                localpath=emptyfile.name,
                remotepath=remote_filepath,
            )

    # pylint: disable-next=unused-argument
    def manage_profile(self, *args: Any, **kwargs: Any) -> None:
        """
        Modify or, failing that, create profile to include the certs
        """
        cmd: str
        if self.profile is None:
            raise RuntimeError(
                "This method cannot modify or create a remote profile unless its details "
                "are provided"
            )
        try:
            logging.info("Checking for existing profile on BIG-IP..")
            # This tmsh command exits nonzero if the object is not found
            cmd = f"list /ltm profile {self.profile.type} {self.profile.name}"
            logging.debug("`%s`", cmd)
            self.conn.run(cmd)
        except UnexpectedExit:
            try:
                cmd = (
                    f"create /ltm profile {self.profile.type} {self.profile.name} "
                    f"cert {self.certificate_bundle.name} key {self.certificate_bundle.name}"
                )
                logging.debug("`%s`", cmd)
                self.conn.run(cmd)
            except UnexpectedExit as ierr:
                raise RuntimeError(
                    f"Failed to create profile `{self.profile.name}` on remote"
                ) from ierr
        else:
            try:
                cmd = (
                    f"modify /ltm profile {self.profile.type} {self.profile.name} cert "
                    f"{self.certificate_bundle.name} key {self.certificate_bundle.name}"
                )
                logging.debug("`%s`", cmd)
                self.conn.run(cmd)
            except UnexpectedExit as err:
                raise RuntimeError(
                    "Unexpected failure when trying to update the profile "
                    f"`{self.profile.name}` to use the new cert"
                ) from err

    # pylint: disable-next=unused-argument
    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Save new running config to disk (`bigip.conf`)
        """
        try:
            cmd: str = "save /sys config"
            logging.debug("`%s`", cmd)
            self.conn.run(cmd)
        except UnexpectedExit as err:
            raise RuntimeError("Failed to save running config to disk") from err

    # pylint: disable-next=unused-argument
    def sync(self, *args: Any, **kwargs: Any) -> None:
        """
        Sync BIG-IP node
        """
        try:
            cmd: str = f"run /cm config-sync to-group {self.sync_group}"
            logging.debug("`%s`", cmd)
            self.conn.run(cmd)
        except UnexpectedExit as err:
            raise RuntimeError(
                f"Failed to sync to device group `{self.sync_group}`"
            ) from err

    @staticmethod
    def entrypoint(
        *, args: argparse.Namespace, certificate_bundle: CertificateBundle
    ) -> None:
        """
        Run tasks for this deployer
        """
        bigip_certificate_bundle: BigipCertificateBundle = BigipCertificateBundle(
            path=args.renewed_lineage, name=args.cert_name
        )
        profile: Optional[CertProfile]
        if args.profile_name is not None and args.profile_type is not None:
            profile = CertProfile(name=args.profile_name, type=args.profile_type)
        else:
            profile = None

        deployer: BigipDeployer = BigipDeployer(
            certificate_bundle=bigip_certificate_bundle,
            dest_temp_dir=args.dest_temp_dir,
            host=args.host,
            profile=profile,
            sync_group=args.sync_group,
        )
        workflow = deployer.get_workflow()
        if args.dry_run:
            print("# Running in dry run mode. Will not run actual deployment tasks.")
        for task in workflow:
            if args.dry_run:
                print(f"Would run task: {task.name}")
            else:
                logging.info("Running workflow step: %s", task.name)
                task.execute()
