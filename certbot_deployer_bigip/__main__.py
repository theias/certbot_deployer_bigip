#!/usr/bin/env python3
"""
Certbot Deployer plugin for deploying certificates to F5 BIG-IP devices

Uses `scp` to copy files to the BIG-IP and `ssh` (via Fabric) to run remote
shell commands for deploying Certbot certificates
"""

import sys

from certbot_deployer import main as framework_main
from .certbot_deployer_bigip import BigipDeployer


def main(
    argv: list = sys.argv[1:],
) -> None:
    # pylint: disable=line-too-long
    """
    main
    """
    with open("/tmp/delme.txt", "w", encoding="utf-8") as myfile:
        myfile.write(str(argv))
    new_argv = [BigipDeployer.subcommand] + argv
    framework_main(deployers=[BigipDeployer], argv=new_argv)


if __name__ == "__main__":
    main()
