import logging
import pytest
from nano_dev_utils import release_ports as rp, PROXY_SERVER, INSPECTOR_CLIENT


@pytest.fixture
def ports_release():
    return rp.PortsRelease()


@pytest.fixture
def mock_logger(mocker):
    logger = mocker.MagicMock(spec=logging.Logger)
    mocker.patch.object(rp, 'lgr', logger)
    return logger


def encode_dict(input_dict: dict) -> bytes:
    return b' '.join(str(v).encode() for v in input_dict.values())


def remove_file_handlers():
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


def mock_pid_retrieval(ports_release, mocker, entry, port):
    mock_process = mocker.MagicMock()
    encoded_entry = encode_dict(entry)
    mock_process.communicate.return_value = (encoded_entry, '')
    mocker.patch('subprocess.Popen', return_value=mock_process)
    pid = ports_release.get_pid_by_port(port)
    return pid, encoded_entry


def test_get_pid_by_port_linux_success(ports_release, mock_logger, mocker):
    mock_popen = mocker.patch('subprocess.Popen')
    mocker.patch('platform.system', return_value='Linux')
    # ss - lntp command response structure
    port = 8080  # local port
    peer_port = '*'
    local_addr = '::'  # :: - listening to all available interfaces
    peer_addr = '::'
    _pid = 1234
    fd = 4  # file descriptor
    ss_entry = {
        'netid': 'tcp6',
        'rx_q': 0,
        'tx_q': 0,
        'local_addr_port': f'{local_addr}:{port}',
        'peer_addr_port': f'{peer_addr}:{peer_port}',
        'process_name': 'users:python3',
        'pid': f'pid={_pid}',
        'fd': f'fd={fd}',
    }

    mock_process = mocker.MagicMock()
    mock_process.communicate.return_value = (encode_dict(ss_entry), '')
    mock_popen.return_value = mock_process

    pid = ports_release.get_pid_by_port(port)
    assert pid == 1234
    mock_popen.assert_called_once_with(
        f'ss -lntp | grep :{port}',
        shell=True,
        stdout=-1,
        stderr=-1,
    )


def test_get_pid_by_port_windows_success(ports_release, mock_logger, mocker):
    mock_popen = mocker.patch('subprocess.Popen')
    mocker.patch('platform.system', return_value='Windows')

    # netstat -ano command response structure (Windows)
    port = 9000
    _pid = 5678
    netstat_entry = {
        'protocol': 'TCP',
        'local_addr_and_port ': f'0.0.0.0:{port}',
        'remote_addr_and_port': '0.0.0.0:0',
        'state_and_pid': f'LISTENING {_pid}\n',
    }

    mock_process = mocker.MagicMock()
    mock_process.communicate.return_value = (encode_dict(netstat_entry), '')
    mock_popen.return_value = mock_process

    pid = ports_release.get_pid_by_port(port)
    assert pid == 5678
    mock_popen.assert_called_once_with(
        f'netstat -ano | findstr :{port}',
        shell=True,
        stdout=-1,
        stderr=-1,
    )


def test_get_pid_by_port_darwin_success(ports_release, mock_logger, mocker):
    mock_popen = mocker.patch('subprocess.Popen')
    mocker.patch('platform.system', return_value='Darwin')
    # lsof -i command response structure (MacOS)
    port = 7000
    _pid = 1111
    lsof_entry = {
        'command': 'python3',  # Process name
        'pid': f'{_pid}',  # Process ID (integer)
        'user': 'user',  # User running the process
        'fd': '10u',  # File descriptor (read/write)
        'type': 'IPv4',  # Network connection type (IPv4/IPv6)
        'device': '0xabcdef0123456789',  # Kernel device identifier
        'size_off': '0t0',  # Size/offset (0 for sockets)
        'protocol': 'TCP',  # Protocol (TCP/UDP)
        'name': f'*:{port} (LISTEN)',  # Combined address & state (optional)
    }

    mock_process = mocker.MagicMock()
    mock_process.communicate.return_value = (encode_dict(lsof_entry), '')
    mock_popen.return_value = mock_process

    pid = ports_release.get_pid_by_port(port)
    assert pid == 1111
    mock_popen.assert_called_once_with(
        f'lsof -i :{port}',
        shell=True,
        stdout=-1,
        stderr=-1,
    )


def test_get_pid_by_port_unsupported_os(ports_release, mock_logger, mocker):
    mocker.patch('platform.system', return_value='UnsupportedOS')
    pid = ports_release.get_pid_by_port(1234)
    assert pid is None
    mock_logger.error.assert_called_once_with(ports_release._log_unsupported_os())


def test_get_pid_by_port_no_process(ports_release, mock_logger, mocker):
    port = 9999
    mocker.patch('platform.system', return_value='Linux')
    mock_process = mocker.MagicMock()
    mock_process.communicate.return_value = (b'', b'')
    mocker.patch('subprocess.Popen', return_value=mock_process)

    pid = ports_release.get_pid_by_port(port)
    assert pid is None
    mock_logger.error.assert_not_called()


def test_get_pid_by_port_command_error(ports_release, mock_logger, mocker):
    mock_popen = mocker.patch('subprocess.Popen')
    mocker.patch('platform.system', return_value='Linux')
    port = 80
    err = 'Error occurred'
    mock_process = mocker.MagicMock()
    mock_process.communicate.return_value = (b'', err.encode())
    mock_popen.return_value = mock_process
    pid = ports_release.get_pid_by_port(port)
    assert pid is None
    mock_logger.error.assert_called_once_with(f'Error running command: {err}')


def test_get_pid_by_port_parse_error(ports_release, mock_logger, mocker):
    mocker.patch('platform.system', return_value='Linux')
    port = 8080
    peer_port = '*'
    local_addr = '::'
    peer_addr = '::'
    _pid = 'invalid'
    fd = 4
    ss_entry = {
        'netid': 'tcp6',
        'rx_q': 0,
        'tx_q': 0,
        'local_addr_port': f'{local_addr}:{port}',
        'peer_addr_port': f'{peer_addr}:{peer_port}',
        'process_name': 'users:python3',
        'pid': f'pid={_pid}',
        'fd': f'fd={fd}',
    }

    pid, enc_entry = mock_pid_retrieval(ports_release, mocker, ss_entry, port)
    assert pid is None
    mock_logger.error.assert_called_once_with(
        f'Could not parse PID from line: {enc_entry.decode()}'
    )


def test_get_pid_by_port_unexpected_exception(ports_release, mock_logger, mocker):
    mocker.patch('platform.system', return_value='Linux')
    err = Exception('Unexpected')
    port = 1234
    mocker.patch('subprocess.Popen', side_effect=err)
    pid = ports_release.get_pid_by_port(port)
    assert pid is None
    mock_logger.error.assert_called_once_with(f'An unexpected error occurred: {err}')


def test_kill_process_success(ports_release, mock_logger, mocker):
    mocker.patch('platform.system', return_value='Linux')
    mock_popen = mocker.patch('subprocess.Popen')

    port = 5678
    mock_process = mocker.MagicMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b'', b'')
    mock_popen.return_value = mock_process
    result = ports_release.kill_process(port)
    assert result is True
    mock_popen.assert_called_once_with(f'kill -9 {port}', shell=True, stderr=-1)


def test_kill_process_fail(ports_release, mock_logger, mocker):
    pid = 1234
    err = 'Access denied'
    mocker.patch('platform.system', return_value='Windows')
    mock_popen = mocker.patch('subprocess.Popen')
    mock_process = mocker.MagicMock()
    mock_process.returncode = 1
    mock_process.communicate.return_value = (b'', err.encode())
    mock_popen.return_value = mock_process
    result = ports_release.kill_process(pid)
    assert result is False
    mock_logger.error.assert_called_once_with(
        ports_release._log_terminate_failed(pid=pid, error=err)
    )


def test_kill_process_unsupported_os(ports_release, mock_logger, mocker):
    mocker.patch('platform.system', return_value='UnsupportedOS')
    pid = 9999
    result = ports_release.kill_process(pid)
    assert result is False
    mock_logger.error.assert_called_once_with(ports_release._log_unsupported_os())


def test_kill_process_unexpected_exception(ports_release, mock_logger, mocker):
    err = Exception('Another error')
    mocker.patch('platform.system', return_value='Linux')
    mocker.patch('subprocess.Popen', side_effect=err)

    pid = 4321
    result = ports_release.kill_process(pid)
    assert result is False
    mock_logger.error.assert_called_once_with(ports_release._log_unexpected_error(err))


def test_release_all_default_ports_success(ports_release, mock_logger, mocker):
    mock_get_pid = mocker.patch.object(ports_release, 'get_pid_by_port')
    mock_kill = mocker.patch.object(ports_release, 'kill_process')

    pid1, pid2 = 1111, 2222
    mock_get_pid.side_effect = [pid1, pid2]
    mock_kill.side_effect = [True, True]
    ports_release.release_all()

    assert mock_get_pid.call_args_list == [
        mocker.call(PROXY_SERVER),
        mocker.call(INSPECTOR_CLIENT),
    ]
    assert mock_kill.call_args_list == [mocker.call(pid1), mocker.call(pid2)]
    mock_logger.info.assert_has_calls(
        [
            mocker.call(ports_release._log_process_found(PROXY_SERVER, pid1)),
            mocker.call(ports_release._log_process_terminated(pid1, PROXY_SERVER)),
            mocker.call(ports_release._log_process_found(INSPECTOR_CLIENT, pid2)),
            mocker.call(ports_release._log_process_terminated(pid2, INSPECTOR_CLIENT)),
        ]
    )


def test_release_all_invalid_port(ports_release, mock_logger, mocker):
    mock_get_pid = mocker.patch.object(ports_release, 'get_pid_by_port')
    mock_kill = mocker.patch.object(ports_release, 'kill_process')
    ports = ['invalid', 1234, 5678]
    mock_get_pid.side_effect = [None, None]
    ports_release.release_all(ports=ports)
    assert mock_get_pid.call_args_list == [mocker.call(ports[1]), mocker.call(ports[2])]

    mock_kill.assert_not_called()
    mock_logger.error.assert_called_once_with(ports_release._log_invalid_port(ports[0]))


def test_release_all_unexpected_exception(ports_release, mock_logger, mocker):
    err = Exception('Release all error')
    port = 9010
    mock_get_pid = mocker.patch.object(
        ports_release, 'get_pid_by_port', side_effect=err
    )
    ports_release.release_all(ports=[port])
    mock_logger.error.assert_called_once_with(ports_release._log_unexpected_error(err))
    mock_get_pid.assert_called_once_with(port)
    assert mock_get_pid.call_args_list == [mocker.call(port)]
