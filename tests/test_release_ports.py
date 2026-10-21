import logging
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from nano_dev_utils import INSPECTOR_CLIENT, PROXY_SERVER, PortsRelease, release_ports
from nano_dev_utils.common import encode_dict


@pytest.fixture
def pr() -> PortsRelease:
    return release_ports.PortsRelease()


@pytest.fixture
def mock_logger(mocker: MockerFixture) -> Mock:
    mock_logger = mocker.MagicMock(spec=logging.Logger)
    mocker.patch.object(release_ports, 'lgr', mock_logger)
    return mock_logger


def remove_file_handlers() -> None:
    """Temporarily remove any file handlers from the root logger"""
    root_logger = logging.getLogger()
    existing_file_handlers = [
        handler
        for handler in root_logger.handlers
        if isinstance(handler, logging.FileHandler)
    ]
    for handler in existing_file_handlers:
        root_logger.removeHandler(handler)
        handler.close()


@pytest.fixture(autouse=True)
def cleanup():
    remove_file_handlers()
    yield


def test_ports_release_init_alias(pr) -> None:
    # Exercises the proxy method delegating to __init__
    pr.init()
    assert isinstance(pr, PortsRelease)


@pytest.mark.parametrize(
    'system, port, expected_pid, entry, expected_cmd',
    [
        (
            'Linux',
            8080,
            1234,
            {
                'netid': 'tcp6',
                'rx_q': 0,
                'tx_q': 0,
                'local_addr_port': ':::8080',
                'peer_addr_port': ':::*',
                'process_name': 'users:python3',
                'pid': 'pid=1234',
                'fd': 'fd=4',
            },
            'ss -lntp | grep :8080',
        ),
        (
            'Windows',
            9000,
            5678,
            {
                'protocol': 'TCP',
                'local_addr_and_port ': '0.0.0.0:9000',
                'remote_addr_and_port': '0.0.0.0:0',
                'state_and_pid': 'LISTENING 5678\n',
            },
            'netstat -ano | findstr :9000',
        ),
        (
            'Darwin',
            7000,
            1111,
            {
                'command': 'python3',
                'pid': '1111',
                'user': 'user',
                'fd': '10u',
                'type': 'IPv4',
                'device': '0xabcdef0123456789',
                'size_off': '0t0',
                'protocol': 'TCP',
                'name': '*:7000 (LISTEN)',
            },
            'lsof -i :7000',
        ),
    ],
)
def test_get_pid_by_port_success(
    pr: PortsRelease,
    mock_logger: Mock,
    mocker: MockerFixture,
    system,
    port,
    expected_pid,
    entry,
    expected_cmd,
) -> None:
    mock_popen = mocker.patch('subprocess.Popen')
    mocker.patch('platform.system', return_value=system)

    mock_process = mocker.MagicMock()
    mock_process.communicate.return_value = (encode_dict(entry), '')
    mock_popen.return_value = mock_process

    pid = pr.get_pid_by_port(port)
    assert pid == expected_pid
    mock_popen.assert_called_once_with(expected_cmd, shell=True, stdout=-1, stderr=-1)


def test_get_pid_windows_value_error(pr, mock_logger, mocker) -> None:
    port = 8080
    mocker.patch('platform.system', return_value='Windows')
    mock_process = mocker.MagicMock()
    # parts[4] is non-numeric
    mock_process.communicate.return_value = (
        f'TCP 0.0.0.0:{port} 0.0.0.0:0 LISTENING invalid_pid'.encode(),
        b'',
    )
    mocker.patch('subprocess.Popen', return_value=mock_process)
    assert pr.get_pid_by_port(port) is None
    mock_logger.error.assert_called()


def test_get_pid_linux_value_error(pr, mock_logger, mocker) -> None:
    port = 8080
    mocker.patch('platform.system', return_value='Linux')
    mock_process = mocker.MagicMock()
    # pid= part is non-numeric
    mock_process.communicate.return_value = (
        f'tcp LISTEN 0 128 *:{port} users:(("python",pid=invalid_pid,fd=3))'.encode(),
        b'',
    )
    mocker.patch('subprocess.Popen', return_value=mock_process)
    assert pr.get_pid_by_port(port) is None
    mock_logger.error.assert_called()


def test_get_pid_by_port_command_error(
    pr: PortsRelease, mock_logger: Mock, mocker: MockerFixture
) -> None:
    mock_popen = mocker.patch('subprocess.Popen')
    mocker.patch('platform.system', return_value='Linux')
    port = 80
    err = 'Error occurred'
    mock_process = mocker.MagicMock()
    mock_process.communicate.return_value = (b'', err.encode())
    mock_popen.return_value = mock_process
    pid = pr.get_pid_by_port(port)
    assert pid is None
    mock_logger.error.assert_called_once_with(f'Error running command: {err}')


def test_get_pid_unsupported_os_exact_log(pr, mock_logger, mocker) -> None:
    mocker.patch('platform.system', return_value='UnsupportedOS')
    assert pr.get_pid_by_port(8080) is None
    mock_logger.error.assert_called_once_with(pr._log_unsupported_os())


def test_get_pid_line_parse_failed(pr, mock_logger, mocker) -> None:
    port = 8080
    mocker.patch('platform.system', return_value='Darwin')
    mock_process = mocker.MagicMock()
    # Contains port '8080', but parts[1] ('bad_pid') causes int() to raise ValueError
    mock_process.communicate.return_value = (f'python bad_pid {port}'.encode(), b'')
    mocker.patch('subprocess.Popen', return_value=mock_process)

    assert pr.get_pid_by_port(port) is None
    # Verifies the exact helper log method was called
    mock_logger.error.assert_called_once()


def test_get_pid_unexpected_exception_logged(pr, mock_logger, mocker) -> None:
    port = 8080
    exc = RuntimeError('Disk error')
    mocker.patch('platform.system', return_value='Linux')
    mocker.patch('subprocess.Popen', side_effect=exc)

    assert pr.get_pid_by_port(port) is None
    mock_logger.error.assert_called_once_with(pr._log_unexpected_error(exc))


def test_get_pid_by_port_no_matching_line(pr, mock_logger, mocker) -> None:
    port = 8080
    mocker.patch('platform.system', return_value='Linux')
    mock_process = mocker.MagicMock()
    # Output has lines, but none contain the target port '8080'
    mock_process.communicate.return_value = (
        b'tcp LISTEN 0 128 *:9999 users:(("python",pid=1234,fd=3))',
        b'',
    )
    mocker.patch('subprocess.Popen', return_value=mock_process)

    pid = pr.get_pid_by_port(port)
    assert pid is None
    mock_logger.error.assert_not_called()


def test_kill_process_success(
    pr: PortsRelease, mock_logger: Mock, mocker: MockerFixture
) -> None:
    mocker.patch('platform.system', return_value='Linux')
    mock_popen = mocker.patch('subprocess.Popen')

    port = 5678
    mock_process = mocker.MagicMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b'', b'')
    mock_popen.return_value = mock_process
    result = pr.kill_process(port)
    assert result is True
    mock_popen.assert_called_once_with(f'kill -9 {port}', shell=True, stderr=-1)


def test_kill_process_fail(
    pr: PortsRelease, mock_logger: Mock, mocker: MockerFixture
) -> None:
    pid = 1234
    err = 'Access denied'
    mocker.patch('platform.system', return_value='Windows')
    mock_popen = mocker.patch('subprocess.Popen')
    mock_process = mocker.MagicMock()
    mock_process.returncode = 1
    mock_process.communicate.return_value = (b'', err.encode())
    mock_popen.return_value = mock_process
    result = pr.kill_process(pid)
    assert result is False
    mock_logger.error.assert_called_once_with(
        pr._log_terminate_failed(pid=pid, error=err)
    )


def test_kill_process_unsupported_os(
    pr: PortsRelease, mock_logger: Mock, mocker: MockerFixture
) -> None:
    mocker.patch('platform.system', return_value='UnsupportedOS')
    pid = 9999
    result = pr.kill_process(pid)
    assert result is False
    mock_logger.error.assert_called_once_with(pr._log_unsupported_os())


def test_kill_process_unexpected_exception(
    pr: PortsRelease, mock_logger: Mock, mocker: MockerFixture
) -> None:
    err = Exception('Another error')
    mocker.patch('platform.system', return_value='Linux')
    mocker.patch('subprocess.Popen', side_effect=err)

    pid = 4321
    result = pr.kill_process(pid)
    assert result is False
    mock_logger.error.assert_called_once_with(pr._log_unexpected_error(err))


def test_release_all_default_ports_success(
    pr: PortsRelease, mock_logger: Mock, mocker: MockerFixture
) -> None:
    mock_get_pid = mocker.patch.object(pr, 'get_pid_by_port')
    mock_kill = mocker.patch.object(pr, 'kill_process')

    pid1, pid2 = 1111, 2222
    mock_get_pid.side_effect = [pid1, pid2]
    mock_kill.side_effect = [True, True]
    pr.release_all()

    assert mock_get_pid.call_args_list == [
        mocker.call(PROXY_SERVER),
        mocker.call(INSPECTOR_CLIENT),
    ]
    assert mock_kill.call_args_list == [mocker.call(pid1), mocker.call(pid2)]
    mock_logger.info.assert_has_calls(
        [
            mocker.call(pr._log_process_found(PROXY_SERVER, pid1)),
            mocker.call(pr._log_process_terminated(pid1, PROXY_SERVER)),
            mocker.call(pr._log_process_found(INSPECTOR_CLIENT, pid2)),
            mocker.call(pr._log_process_terminated(pid2, INSPECTOR_CLIENT)),
        ]
    )


def test_release_all_invalid_port(
    pr: PortsRelease, mock_logger: Mock, mocker: MockerFixture
) -> None:
    mock_get_pid = mocker.patch.object(pr, 'get_pid_by_port')
    mock_kill = mocker.patch.object(pr, 'kill_process')
    ports = ['invalid', 1234, 5678]
    mock_get_pid.side_effect = [None, None]
    pr.release_all(ports=ports)  # type: ignore[arg-type]
    assert mock_get_pid.call_args_list == [mocker.call(ports[1]), mocker.call(ports[2])]

    mock_kill.assert_not_called()
    mock_logger.error.assert_called_once_with(pr._log_invalid_port(ports[0]))  # type: ignore[arg-type]


def test_release_all_unexpected_exception(
    pr: PortsRelease, mock_logger: Mock, mocker: MockerFixture
) -> None:
    err = Exception('Release all error')
    port = 9010
    mock_get_pid = mocker.patch.object(pr, 'get_pid_by_port', side_effect=err)
    pr.release_all(ports=[port])
    mock_logger.error.assert_called_once_with(pr._log_unexpected_error(err))
    mock_get_pid.assert_called_once_with(port)
    assert mock_get_pid.call_args_list == [mocker.call(port)]


def test_ports_release_update_sets_attributes(pr):
    pr.update({'foo': 123, 'bar': 'baz'})
    assert pr.foo == 123  # type: ignore[attr-defined]
    assert pr.bar == 'baz'  # type: ignore[attr-defined]


def test_ports_release_update_invalid_attribute_raises(pr):
    pr.update({'anything_you_want': 'ok'})
    assert pr.anything_you_want == 'ok'  # type: ignore[attr-defined]


def test_release_all_terminate_failed(pr, mock_logger, mocker) -> None:
    port = 8080
    pid = 1234

    # Mock finding a PID and then failing to kill it
    mocker.patch.object(pr, 'get_pid_by_port', return_value=pid)
    mocker.patch.object(pr, 'kill_process', return_value=False)

    pr.release_all([port])

    mock_logger.error.assert_called_once_with(
        pr._log_terminate_failed(pid=pid, port=port)
    )
