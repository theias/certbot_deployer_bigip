"""
main

manipulates argv in order to pass the run on to the framework as
`certbot-deployer <subcommand>
"""

import sys

from certbot_deployer import main as framework_main
from ..certbot_deployer_bigip import BigipDeployer


def main(
    argv: list = sys.argv[1:],
) -> None:
    # pylint: disable=line-too-long
    """
    main
    """
    new_argv = [BigipDeployer.subcommand] + argv
    framework_main(deployers=[BigipDeployer], argv=new_argv)
