import unittest
from unittest.mock import patch, call
import logging
from src.nano_dev_utils import release_ports as rp

PROXY_SERVER = rp.PROXY_SERVER
CLIENT_PORT = rp.INSPECTOR_CLIENT


class TestPortsRelease(unittest.TestCase):
    PORTS_RELEASE_OBJ = 'tests.test_release_ports.rp.PortsRelease'

    def setUp(self):
        self.ports_release = rp.PortsRelease()
        self.mock_logger = unittest.mock.MagicMock(spec=logging.Logger)

        self.remove_file_handlers()

        patch.object(rp, 'lgr', self.mock_logger).start()
        self.addCleanup(patch.stopall)

    @staticmethod
    def _encode_dict(input_dict: dict) -> bytes:
        return b' '.join(str(v).encode() for v in input_dict.values())

    @staticmethod
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

    def _mock_pid_retrieval(
        self, mock_popen: unittest.mock.MagicMock, entry: dict, port: int
    ) -> (int, bytes):
        mock_process = unittest.mock.MagicMock()
        encoded_entry = self._encode_dict(entry)
        mock_process.communicate.return_value = (encoded_entry, '')
        mock_popen.return_value = mock_process
        pid = self.ports_release.get_pid_by_port(port)
        return pid, encoded_entry

    def tearDown(self):
        patch.stopall()

    def test_get_pid_by_port_linux_success(self):
        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.Popen') as mock_popen:
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

                pid, _ = self._mock_pid_retrieval(mock_popen, ss_entry, port)
                self.assertEqual(pid, _pid)
                mock_popen.assert_called_once_with(
                    f'ss -lntp | grep :{port}',
                    shell=True,
                    stdout=unittest.mock.ANY,
                    stderr=unittest.mock.ANY,
                )

    def test_get_pid_by_port_windows_success(self):
        with patch('platform.system', return_value='Windows'):
            with patch('subprocess.Popen') as mock_popen:
                # netstat -ano command response structure (Windows)
                port = 9000
                _pid = 5678
                netstat_entry = {
                    'protocol': 'TCP',
                    'local_addr_and_port ': f'0.0.0.0:{port}',
                    'remote_addr_and_port': '0.0.0.0:0',
                    'state_and_pid': f'LISTENING {_pid}\n',
                }

                pid, _ = self._mock_pid_retrieval(mock_popen, netstat_entry, port)
                self.assertEqual(pid, _pid)
                mock_popen.assert_called_once_with(
                    f'netstat -ano | findstr :{port}',
                    shell=True,
                    stdout=unittest.mock.ANY,
                    stderr=unittest.mock.ANY,
                )

    def test_get_pid_by_port_darwin_success(self):
        with patch('platform.system', return_value='Darwin'):
            with patch('subprocess.Popen') as mock_popen:
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

                pid, _ = self._mock_pid_retrieval(mock_popen, lsof_entry, port)
                self.assertEqual(pid, _pid)
                mock_popen.assert_called_once_with(
                    f'lsof -i :{port}',
                    shell=True,
                    stdout=unittest.mock.ANY,
                    stderr=unittest.mock.ANY,
                )

    def test_get_pid_by_port_unsupported_os(self):
        with patch('platform.system', return_value='UnsupportedOS'):
            pid = self.ports_release.get_pid_by_port(1234)
            self.assertIsNone(pid)
            self.mock_logger.error.assert_called_once_with(
                self.ports_release._log_unsupported_os()
            )

    def test_get_pid_by_port_no_process(self):
        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = unittest.mock.MagicMock()
                mock_process.communicate.return_value = (b'', b'')
                mock_popen.return_value = mock_process
                pid = self.ports_release.get_pid_by_port(9999)
                self.assertIsNone(pid)

    def test_get_pid_by_port_command_error(self):
        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.Popen') as mock_popen:
                err = 'Error occurred'
                mock_process = unittest.mock.MagicMock()
                mock_process.communicate.return_value = (b'', err.encode())
                mock_popen.return_value = mock_process
                pid = self.ports_release.get_pid_by_port(80)
                self.assertIsNone(pid)
                self.mock_logger.error.assert_called_once_with(
                    f'Error running command: {err}'
                )

    def test_get_pid_by_port_parse_error(self):
        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.Popen') as mock_popen:
                # ss - lntp command response structure
                port = 8080  # local port
                peer_port = '*'
                local_addr = '::'  # :: - listening to all available interfaces
                peer_addr = '::'
                _pid = 'invalid'
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

                pid, enc_entry = self._mock_pid_retrieval(mock_popen, ss_entry, port)
                self.assertIsNone(pid)
                self.mock_logger.error.assert_called_once_with(
                    f'Could not parse PID from line: {enc_entry.decode()}'
                )

    def test_get_pid_by_port_unexpected_exception(self):
        with patch('platform.system', return_value='Linux'):
            err = Exception('Unexpected')
            with patch('subprocess.Popen', side_effect=err):
                port = 1234
                pid = self.ports_release.get_pid_by_port(port)
                self.assertIsNone(pid)
                self.mock_logger.error.assert_called_once_with(
                    f'An unexpected error occurred: {err}'
                )

    def test_kill_process_success(self):
        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.Popen') as mock_popen:
                port = 5678
                mock_process = unittest.mock.MagicMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b'', b'')
                mock_popen.return_value = mock_process
                result = self.ports_release.kill_process(port)
                self.assertTrue(result)
                mock_popen.assert_called_once_with(
                    f'kill -9 {port}', shell=True, stderr=unittest.mock.ANY
                )

    def test_kill_process_fail(self):
        pid = 1234
        err = 'Access denied'
        with patch('platform.system', return_value='Windows'):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = unittest.mock.MagicMock()
                mock_process.returncode = 1
                mock_process.communicate.return_value = (b'', err.encode())
                mock_popen.return_value = mock_process
                result = self.ports_release.kill_process(pid)
                self.assertFalse(result)
                self.mock_logger.error.assert_called_once_with(
                    self.ports_release._log_terminate_failed(pid=pid, error=err)
                )

    def test_kill_process_unsupported_os(self):
        with patch('platform.system', return_value='UnsupportedOS'):
            pid = 9999
            result = self.ports_release.kill_process(pid)
            self.assertFalse(result)
            self.mock_logger.error.assert_called_once_with(
                self.ports_release._log_unsupported_os()
            )

    def test_kill_process_unexpected_exception(self):
        err = Exception('Another error')
        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.Popen', side_effect=err):
                pid = 4321
                result = self.ports_release.kill_process(pid)
                self.assertFalse(result)
                self.mock_logger.error.assert_called_once_with(
                    self.ports_release._log_unexpected_error(err)
                )

    @patch(f'{PORTS_RELEASE_OBJ}.get_pid_by_port')
    @patch(f'{PORTS_RELEASE_OBJ}.kill_process')
    def test_release_all_default_ports_success(self, mock_kill, mock_get_pid):
        pid1, pid2 = 1111, 2222
        mock_get_pid.side_effect = [pid1, pid2]
        mock_kill.side_effect = [True, True]
        self.ports_release.release_all()
        mock_get_pid.assert_has_calls([call(PROXY_SERVER), call(CLIENT_PORT)])
        mock_kill.assert_has_calls([call(pid1), call(pid2)])
        self.assertEqual(mock_get_pid.call_count, 2)
        self.assertEqual(mock_kill.call_count, 2)
        self.mock_logger.info.assert_any_call(
            self.ports_release._log_process_found(PROXY_SERVER, pid1)
        )
        self.mock_logger.info.assert_any_call(
            self.ports_release._log_process_terminated(pid1, PROXY_SERVER)
        )
        self.mock_logger.info.assert_any_call(
            self.ports_release._log_process_found(CLIENT_PORT, pid2)
        )
        self.mock_logger.info.assert_any_call(
            self.ports_release._log_process_terminated(pid2, CLIENT_PORT)
        )

    def test_release_all_invalid_port(self):
        with patch(f'{self.PORTS_RELEASE_OBJ}.get_pid_by_port') as mock_get_pid:
            with patch(f'{self.PORTS_RELEASE_OBJ}.kill_process') as mock_kill:
                # Make get_pid_by_port return None for the valid ports in this test
                ports = ['invalid', 1234, 5678]
                mock_get_pid.side_effect = [None, None]
                self.ports_release.release_all(ports=ports)
                mock_get_pid.assert_any_call(ports[1])
                mock_get_pid.assert_any_call(ports[2])
                self.assertEqual(mock_get_pid.call_count, 2)
                mock_kill.assert_not_called()
                self.mock_logger.error.assert_called_once_with(
                    self.ports_release._log_invalid_port(ports[0])
                )

    def test_release_all_unexpected_exception(self):
        err = Exception('Release all error')
        with patch(f'{self.PORTS_RELEASE_OBJ}.get_pid_by_port', side_effect=err):
            port = 9010
            self.ports_release.release_all(ports=[port])
            self.mock_logger.error.assert_called_once_with(
                self.ports_release._log_unexpected_error(err)
            )
            self.ports_release.get_pid_by_port.assert_called_once_with(port)


if __name__ == '__main__':
    unittest.main()
