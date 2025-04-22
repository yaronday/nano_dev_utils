import unittest
from unittest.mock import patch
import logging
from src.nano_utils_yaronday import release_ports


class TestPortsRelease(unittest.TestCase):

    def setUp(self):
        self.ports_release = release_ports.PortsRelease()
        self.mock_logger = unittest.mock.MagicMock(spec=logging.Logger)

        self.remove_file_handlers()

        patch.object(release_ports, 'lgr', self.mock_logger).start()
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
                self.mock_logger.error.assert_called_once_with("Error running command: Error occurred")

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
                self.mock_logger.error.assert_called_once_with("An unexpected error occurred: Unexpected")


if __name__ == '__main__':
    unittest.main()
