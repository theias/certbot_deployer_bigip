"""
Unit tests for BigipTask class
"""

from typing import Any, Dict, List, Optional

import pytest

from certbot_deployer_bigip.certbot_deployer_bigip import BigipTask


@pytest.mark.parametrize(
    "args, passed_args",
    [
        ({"arg1": "arg1_value", "arg2": "arg2_value"}, ["arg1_value", "arg2_value"]),
        ({}, [None, None]),
    ],
)
def test_bigiptask_exec(args: Dict[str, str], passed_args: List[str]) -> None:
    """
    Verify that a task calls `exec_function` with `exec_args`
    """
    called: bool = False
    called_args: list = []

    def some_callable(
        *, arg1: Optional[Any] = None, arg2: Optional[Any] = None
    ) -> None:
        # pylint: disable-next=unused-variable
        nonlocal called
        called = True
        called_args.extend((arg1, arg2))

    # pylint: disable-next=unused-variable
    task = BigipTask(
        exec_function=some_callable,
        exec_kwargs=args,
    )
    task.execute()
    assert called is not False
    assert called_args == passed_args
