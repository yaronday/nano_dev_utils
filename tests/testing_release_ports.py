import unittest
from unittest.mock import patch, call
import logging
from src.nano_dev_utils import release_ports as rp

PROXY_SERVER = rp.PROXY_SERVER
CLIENT_PORT = rp.INSPECTOR_CLIENT


class TestPortsRelease(unittest.TestCase):

    def setUp(self):
        self.ports_release = rp.PortsRelease()
        self.mock_logger = unittest.mock.MagicMock(spec=logging.Logger)

        self.remove_file_handlers()

        patch.object(rp, 'lgr', self.mock_logger).start()
        self.addCleanup(patch.stopall)

    @staticmethod
    def _encode_array(arr: list[str]) -> bytes:
        return ''.join(arr).encode()

    @staticmethod
    def _encode_dict(input_dict: dict) -> bytes:
        return b' '.join(str(v).encode() for v in input_dict.values())

    @staticmethod
    def remove_file_handlers():
        """Temporarily remove any file handlers from the root logger"""
        root_logger = logging.getLogger()
        existing_file_handlers = [
            handler for handler in root_logger.handlers
            if isinstance(handler, logging.FileHandler)
        ]
        for handler in existing_file_handlers:
            root_logger.removeHandler(handler)
            handler.close()

    def tearDown(self):
        patch.stopall()

    def test_get_pid_by_port_linux_success(self):
        with (patch('platform.system', return_value='Linux')):
            with patch('subprocess.Popen') as mock_popen:
                port = 8080
                _pid = 1234
                cmd_resp = [f'tcp6 0 0 :::{port} ',
                            f':::* users:(("python3",)',
                            f' pid={_pid} fd=4)\n',
                            ]
                cmd_resp_byte = self._encode_array(cmd_resp)

                mock_process = unittest.mock.MagicMock()
                mock_process.communicate.return_value = (cmd_resp_byte, '')
                mock_popen.return_value = mock_process
                pid = self.ports_release.get_pid_by_port(port)
                self.assertEqual(pid, _pid)
                mock_popen.assert_called_once_with(f'ss -lntp | grep :{port}',
                                                   shell=True, stdout=unittest.mock.ANY,
                                                   stderr=unittest.mock.ANY)

    def test_get_pid_by_port_windows_success(self):
        with patch('platform.system', return_value='Windows'):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = unittest.mock.MagicMock()

                # netstat -ano command response structure (Windows)
                port = 9000
                _pid = 5678
                protocol = 'TCP'
                local_addr = '0.0.0.0'
                remote_addr = '0.0.0.0'
                remote_port = 0
                state = 'LISTENING'

                cmd_resp = [f'{protocol} {local_addr}:{port} ',
                            f'{remote_addr}:{remote_port} ',
                            f'{state} {_pid}\n']

                cmd_resp_byte = self._encode_array(cmd_resp)
                mock_process.communicate.return_value = (cmd_resp_byte, '')
                mock_popen.return_value = mock_process
                pid = self.ports_release.get_pid_by_port(port)
                self.assertEqual(pid, _pid)
                mock_popen.assert_called_once_with(f'netstat -ano | findstr :{port}',
                                                   shell=True, stdout=unittest.mock.ANY,
                                                   stderr=unittest.mock.ANY)

    def test_get_pid_by_port_darwin_success(self):
        with patch('platform.system', return_value='Darwin'):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = unittest.mock.MagicMock()
                # lsof -i  command response structure (MacOS)
                port = 7000
                _pid = 1111
                lsof_entry = {
                    "command": "python3",  # Process name
                    "pid": f'{_pid}',  # Process ID (integer)
                    "user": "user",  # User running the process
                    "fd": "10u",  # File descriptor (read/write)
                    "type": "IPv4",  # Network connection type (IPv4/IPv6)
                    "device": "0xabcdef0123456789",  # Kernel device identifier
                    "size_off": "0t0",  # Size/offset (0 for sockets)
                    "protocol": "TCP",  # Protocol (TCP/UDP)
                    "name": f"*:{port} (LISTEN)"  # Combined address & state (optional)
                }

                mock_process.communicate.return_value = (self._encode_dict(lsof_entry), '')

                # mock_process.communicate.return_value = (b"python3     "
                #                                          b"1111 user   "
                #                                          b"10u  IPv4 "
                #                                          b"0xabcdef0123456789"
                #                                          b"      0t0  TCP *:"
                #                                          b"7000 (LISTEN)\n", b"")
                mock_popen.return_value = mock_process
                pid = self.ports_release.get_pid_by_port(port)
                self.assertEqual(pid, _pid)
                mock_popen.assert_called_once_with(f'lsof -i :{port}',
                                                   shell=True, stdout=unittest.mock.ANY,
                                                   stderr=unittest.mock.ANY)

    def test_get_pid_by_port_unsupported_os(self):
        with patch('platform.system', return_value='UnsupportedOS'):
            pid = self.ports_release.get_pid_by_port(1234)
            self.assertIsNone(pid)
            self.mock_logger.error.assert_called_once_with(self.ports_release.
                                                           _log_unsupported_os())

    def test_get_pid_by_port_no_process(self):
        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = unittest.mock.MagicMock()
                mock_process.communicate.return_value = (b"", b"")
                mock_popen.return_value = mock_process
                pid = self.ports_release.get_pid_by_port(9999)
                self.assertIsNone(pid)

    def test_get_pid_by_port_command_error(self):
        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = unittest.mock.MagicMock()
                mock_process.communicate.return_value = (b"", b"Error occurred")
                mock_popen.return_value = mock_process
                pid = self.ports_release.get_pid_by_port(80)
                self.assertIsNone(pid)
                self.mock_logger.error.assert_called_once_with("Error running "
                                                               "command: Error occurred")

    def test_get_pid_by_port_parse_error(self):
        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = unittest.mock.MagicMock()
                mock_process.communicate.return_value = (b"tcp6   0"
                                                         b"      0 "
                                                         b":::8080"
                                                         b"              "
                                                         b":::* users:((\"python3\","
                                                         b"pid=invalid,fd=4))\n", b"")
                mock_popen.return_value = mock_process
                pid = self.ports_release.get_pid_by_port(8080)
                self.assertIsNone(pid)
                self.mock_logger.error.assert_called_once_with("Could not parse PID "
                                                               "from line: tcp6   0"
                                                               "      0 :::8080"
                                                               "              :::*"
                                                               " users:((\"python3\","
                                                               "pid=invalid,fd=4))")

    def test_get_pid_by_port_unexpected_exception(self):
        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.Popen', side_effect=Exception("Unexpected")):
                pid = self.ports_release.get_pid_by_port(1234)
                self.assertIsNone(pid)
                self.mock_logger.error.assert_called_once_with("An unexpected "
                                                               "error occurred: Unexpected")

    def test_kill_process_success(self):
        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = unittest.mock.MagicMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"", b"")
                mock_popen.return_value = mock_process
                result = self.ports_release.kill_process(5678)
                self.assertTrue(result)
                mock_popen.assert_called_once_with('kill -9 5678',
                                                   shell=True, stderr=unittest.mock.ANY)

    def test_kill_process_fail(self):
        pid = 1234
        err = 'Access denied'
        with patch('platform.system', return_value='Windows'):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = unittest.mock.MagicMock()
                mock_process.returncode = 1
                mock_process.communicate.return_value = (b"", err.encode('utf-8'))
                mock_popen.return_value = mock_process
                result = self.ports_release.kill_process(pid)
                self.assertFalse(result)
                self.mock_logger.error.assert_called_once_with(self.ports_release.
                                                               _log_terminate_failed(pid=pid, error=err))

    def test_kill_process_unsupported_os(self):
        with patch('platform.system', return_value='UnsupportedOS'):
            result = self.ports_release.kill_process(9999)
            self.assertFalse(result)
            self.mock_logger.error.assert_called_once_with(self.ports_release.
                                                           _log_unsupported_os())

    def test_kill_process_unexpected_exception(self):
        err = Exception("Another error")
        with (patch('platform.system', return_value='Linux')):
            with patch('subprocess.Popen',
                       side_effect=err):
                result = self.ports_release.kill_process(4321)
                self.assertFalse(result)
                self.mock_logger.error.assert_called_once_with(self.ports_release.
                                                               _log_unexpected_error(err))
                
    @patch('testing_release_ports.rp.PortsRelease.get_pid_by_port')
    @patch('testing_release_ports.rp.PortsRelease.kill_process')
    def test_release_all_default_ports_success(self, mock_kill, mock_get_pid):
        pid1, pid2 = 1111, 2222
        mock_get_pid.side_effect = [pid1, pid2]
        mock_kill.side_effect = [True, True]
        self.ports_release.release_all()
        mock_get_pid.assert_has_calls([call(PROXY_SERVER), call(CLIENT_PORT)])
        mock_kill.assert_has_calls([call(pid1), call(pid2)])
        self.assertEqual(mock_get_pid.call_count, 2)
        self.assertEqual(mock_kill.call_count, 2)
        self.mock_logger.info.assert_any_call(self.ports_release.
                                              _log_process_found(PROXY_SERVER, pid1))
        self.mock_logger.info.assert_any_call(self.ports_release.
                                              _log_process_terminated(pid1, PROXY_SERVER))
        self.mock_logger.info.assert_any_call(self.ports_release.
                                              _log_process_found(CLIENT_PORT, pid2))
        self.mock_logger.info.assert_any_call(self.ports_release.
                                              _log_process_terminated(pid2, CLIENT_PORT))

    def test_release_all_invalid_port(self):
        with patch('testing_release_ports.rp.PortsRelease.get_pid_by_port') as mock_get_pid:
            with patch('testing_release_ports.rp.PortsRelease.kill_process') as mock_kill:
                # Make get_pid_by_port return None for the valid ports in this test
                port = "invalid"
                mock_get_pid.side_effect = [None, None]
                self.ports_release.release_all(ports=[1234, "invalid", 5678])
                mock_get_pid.assert_any_call(1234)
                mock_get_pid.assert_any_call(5678)
                self.assertEqual(mock_get_pid.call_count, 2)
                mock_kill.assert_not_called()
                self.mock_logger.error.assert_called_once_with(self.ports_release.
                                                               _log_invalid_port(port))

    def test_release_all_unexpected_exception(self):
        err = Exception("Release all error")
        with patch('testing_release_ports.'
                   'rp.PortsRelease.get_pid_by_port',
                   side_effect=err):
            self.ports_release.release_all(ports=[9010])
            self.mock_logger.error.assert_called_once_with(self.ports_release.
                                                           _log_unexpected_error(err))
            self.ports_release.get_pid_by_port.assert_called_once_with(9010)


if __name__ == '__main__':
    unittest.main()
