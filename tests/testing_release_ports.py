import unittest
from unittest.mock import patch, call
import logging
from src.nano_utils_yaronday import release_ports as rp

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
        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = unittest.mock.MagicMock()
                mock_process.communicate.return_value = (b"tcp6 0 0 :::8080 "
                                                         b":::* users:((\"python3\",)"
                                                         b" pid=1234 fd=4)\n", b"")
                mock_popen.return_value = mock_process
                pid = self.ports_release.get_pid_by_port(8080)
                self.assertEqual(pid, 1234)
                mock_popen.assert_called_once_with('ss -lntp | grep :8080',
                                                   shell=True, stdout=unittest.mock.ANY,
                                                   stderr=unittest.mock.ANY)

    def test_get_pid_by_port_windows_success(self):
        with patch('platform.system', return_value='Windows'):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = unittest.mock.MagicMock()
                mock_process.communicate.return_value = (b"TCP    0.0.0.0:"
                                                         b"9000           "
                                                         b"0.0.0.0:0"
                                                         b"              "
                                                         b"LISTENING"
                                                         b"       5678\n", b"")
                mock_popen.return_value = mock_process
                pid = self.ports_release.get_pid_by_port(9000)
                self.assertEqual(pid, 5678)
                mock_popen.assert_called_once_with('netstat -ano | findstr :9000',
                                                   shell=True, stdout=unittest.mock.ANY,
                                                   stderr=unittest.mock.ANY)

    def test_get_pid_by_port_darwin_success(self):
        with patch('platform.system', return_value='Darwin'):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = unittest.mock.MagicMock()
                mock_process.communicate.return_value = (b"python3     "
                                                         b"1111 user   "
                                                         b"10u  IPv4 "
                                                         b"0xabcdef0123456789"
                                                         b"      0t0  TCP *:"
                                                         b"7000 (LISTEN)\n", b"")
                mock_popen.return_value = mock_process
                pid = self.ports_release.get_pid_by_port(7000)
                self.assertEqual(pid, 1111)
                mock_popen.assert_called_once_with('lsof -i :7000',
                                                   shell=True, stdout=unittest.mock.ANY,
                                                   stderr=unittest.mock.ANY)

    def test_get_pid_by_port_unsupported_os(self):
        with patch('platform.system', return_value='UnsupportedOS'):
            pid = self.ports_release.get_pid_by_port(1234)
            self.assertIsNone(pid)
            self.mock_logger.error.assert_called_once_with("Unsupported "
                                                           "OS: UnsupportedOS")

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
        with patch('platform.system', return_value='Windows'):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = unittest.mock.MagicMock()
                mock_process.returncode = 1
                mock_process.communicate.return_value = (b"", b"Access denied")
                mock_popen.return_value = mock_process
                result = self.ports_release.kill_process(1234)
                self.assertFalse(result)
                self.mock_logger.error.assert_called_once_with("Failed to kill "
                                                               "process 1234. "
                                                               "Error: Access denied")

    def test_kill_process_unsupported_os(self):
        with patch('platform.system', return_value='UnsupportedOS'):
            result = self.ports_release.kill_process(9999)
            self.assertFalse(result)
            self.mock_logger.error.assert_called_once_with("Unsupported OS: "
                                                           "UnsupportedOS")

    def test_kill_process_unexpected_exception(self):
        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.Popen',
                       side_effect=Exception("Another error")):
                result = self.ports_release.kill_process(4321)
                self.assertFalse(result)
                self.mock_logger.error.assert_called_once_with("An unexpected "
                                                               "error occurred: "
                                                               "Another error")
                
    @patch('testing_release_ports.rp.PortsRelease.get_pid_by_port')
    @patch('testing_release_ports.rp.PortsRelease.kill_process')
    def test_release_all_default_ports_success(self, mock_kill, mock_get_pid):
        mock_get_pid.side_effect = [1111, 2222]
        mock_kill.side_effect = [True, True]
        self.ports_release.release_all()
        mock_get_pid.assert_has_calls([call(PROXY_SERVER), call(CLIENT_PORT)])
        mock_kill.assert_has_calls([call(1111), call(2222)])
        self.assertEqual(mock_get_pid.call_count, 2)
        self.assertEqual(mock_kill.call_count, 2)
        self.mock_logger.info.assert_any_call(f"Process ID (PID) found for "
                                              f"port {PROXY_SERVER}: 1111")
        self.mock_logger.info.assert_any_call(f"Process {1111} (on port "
                                              f"{PROXY_SERVER}) "
                                              f"killed successfully.")
        self.mock_logger.info.assert_any_call(f"Process ID (PID) "
                                              f"found for port {CLIENT_PORT}: "
                                              f"2222")
        self.mock_logger.info.assert_any_call(f"Process {2222} (on port "
                                              f"{CLIENT_PORT}) killed successfully.")

    def test_release_all_invalid_port(self):
        with patch('testing_release_ports.rp.PortsRelease.get_pid_by_port') as mock_get_pid:
            with patch('testing_release_ports.rp.PortsRelease.kill_process') as mock_kill:
                # Make get_pid_by_port return None for the valid ports in this test
                mock_get_pid.side_effect = [None, None]
                self.ports_release.release_all(ports=[1234, "invalid", 5678])
                mock_get_pid.assert_any_call(1234)
                mock_get_pid.assert_any_call(5678)
                self.assertEqual(mock_get_pid.call_count, 2)
                mock_kill.assert_not_called()
                self.mock_logger.error.assert_called_once_with("Invalid port "
                                                               "number: invalid."
                                                               " Skipping.")

    def test_release_all_unexpected_exception(self):
        with patch('testing_release_ports.'
                   'rp.PortsRelease.get_pid_by_port',
                   side_effect=Exception("Release all error")):
            self.ports_release.release_all(ports=[9010])
            self.mock_logger.error.assert_called_once_with("An unexpected error "
                                                           "occurred: Release all error")
            self.ports_release.get_pid_by_port.assert_called_once_with(9010)


if __name__ == '__main__':
    unittest.main()
