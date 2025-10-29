import platform
import subprocess
import logging

from nano_dev_utils.common import update


lgr = logging.getLogger(__name__)
"""Module-level logger. Configure using logging.basicConfig() in your application."""

PROXY_SERVER = 6277
INSPECTOR_CLIENT = 6274


class PortsRelease:
    def __init__(self, default_ports: list[int] | None = None):
        self.default_ports: list[int] = (
            default_ports
            if default_ports is not None
            else [PROXY_SERVER, INSPECTOR_CLIENT]
        )

    @staticmethod
    def _log_process_found(port: int, pid: int) -> str:
        return f'Process ID (PID) found for port {port}: {pid}.'

    @staticmethod
    def _log_process_terminated(pid: int, port: int) -> str:
        return f'Process {pid} (on port {port}) terminated successfully.'

    @staticmethod
    def _log_no_process(port: int) -> str:
        return f'No process found listening on port {port}.'

    @staticmethod
    def _log_invalid_port(port: int) -> str:
        return f'Invalid port number: {port}. Skipping.'

    @staticmethod
    def _log_terminate_failed(
        pid: int, port: int | None = None, error: str | None = None
    ) -> str:
        base_msg = f'Failed to terminate process {pid}'
        if port:
            base_msg += f' (on port {port})'
        if error:
            base_msg += f'. Error: {error}'
        return base_msg

    @staticmethod
    def _log_line_parse_failed(line: str) -> str:
        return f'Could not parse PID from line: {line}'

    @staticmethod
    def _log_unexpected_error(e: Exception) -> str:
        return f'An unexpected error occurred: {e}'

    @staticmethod
    def _log_cmd_error(error: bytes) -> str:
        return f'Error running command: {error.decode()}'

    @staticmethod
    def _log_unsupported_os() -> str:
        return f'Unsupported OS: {platform.system()}'

    def init(self, *args, **kwargs) -> None:
        self.__init__(*args, **kwargs)

    def update(self, attrs: dict) -> None:
        update(self, attrs)

    def get_pid_by_port(self, port: int) -> int | None:
        """Gets the process ID (PID) listening on the specified port."""
        system = platform.system()
        try:
            cmd: str = {
                'Windows': f'netstat -ano | findstr :{port}',
                'Linux': f'ss -lntp | grep :{port}',
                'Darwin': f'lsof -i :{port}',
            }.get(system, '')
            if not cmd:
                lgr.error(self._log_unsupported_os())
                return None

            process = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            output, error = process.communicate()
            if error:
                lgr.error(self._log_cmd_error(error))
                return None

            lines: list[str] = output.decode().splitlines()
            for line in lines:
                if str(port) in line:
                    parts: list[str] = line.split()
                    if system == 'Windows' and len(parts) > 4:
                        try:
                            return int(parts[4])
                        except ValueError:
                            lgr.error(self._log_line_parse_failed(line))
                            return None
                    elif system == 'Linux':
                        for part in parts:
                            if 'pid=' in part:
                                try:
                                    return int(part.split('=')[1])
                                except ValueError:
                                    lgr.error(self._log_line_parse_failed(line))
                                    return None
                    elif system == 'Darwin' and len(parts) > 1:
                        try:
                            return int(parts[1])
                        except ValueError:
                            lgr.error(self._log_line_parse_failed(line))
                            return None
            return None
        except Exception as e:
            lgr.error(self._log_unexpected_error(e))
            return None

    def kill_process(self, pid: int) -> bool:
        """Kills the process with the specified PID."""
        try:
            cmd: str = {
                'Windows': f'taskkill /F /PID {pid}',
                'Linux': f'kill -9 {pid}',
                'Darwin': f'kill -9 {pid}',
            }.get(platform.system(), '')  # fallback to empty string
            if not cmd:
                lgr.error(self._log_unsupported_os())
                return False
            process = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE)
            _, error = process.communicate()
            if process.returncode:
                error_msg = error.decode()
                lgr.error(self._log_terminate_failed(pid=pid, error=error_msg))
                return False
            return True
        except Exception as e:
            lgr.error(self._log_unexpected_error(e))
            return False

    def release_all(self, ports: list[int] | None = None) -> None:
        try:
            ports_to_release: list[int] = self.default_ports if ports is None else ports

            for port in ports_to_release:
                if not isinstance(port, int):
                    lgr.error(self._log_invalid_port(port))
                    continue

                pid: int | None = self.get_pid_by_port(port)
                if pid is None:
                    lgr.info(self._log_no_process(port))
                    continue

                lgr.info(self._log_process_found(port, pid))
                if self.kill_process(pid):
                    lgr.info(self._log_process_terminated(pid, port))
                else:
                    lgr.error(self._log_terminate_failed(pid=pid, port=port))
        except Exception as e:
            lgr.error(self._log_unexpected_error(e))
