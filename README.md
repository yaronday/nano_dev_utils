# nano_dev_utils

A collection of small Python utilities for developers.
[PYPI package: nano-dev-utils](https://pypi.org/project/nano-dev-utils)

## Modules

### `timers.py`

This module provides a `Timer` class for measuring the execution time of code blocks and functions with additional features like timeout control and multi-iteration averaging.

#### `Timer` Class

* **`__init__(self, precision: int = 4, verbose: bool = False, printout: bool = False)`**: Initializes a `Timer` instance.
    * `precision`: The number of decimal places to record and display time durations. Defaults to 4.
    * `verbose`: Optionally displays the function's positional arguments (args) and keyword arguments (kwargs). Defaults to `False`.
    * `printout`: Allows printing to console.

* **`def timeit(
        self,
        iterations: int = 1,
        timeout: float | None = None,
        per_iteration: bool = False,
    ) -> Callable[[Callable[P, Any]], Callable[P, Any]]:`**:   
      Decorator that times either **sync** or **async** function execution with advanced features:
    * `iterations`: Number of times to run the function (for averaging). Defaults to 1.
    * `timeout`: Maximum allowed execution time in seconds. When exceeded:
        * Raises `TimeoutError` immediately
        * **Warning:** The function execution will be aborted mid-operation
        * No return value will be available if timeout occurs
    * `per_iteration`: If True, applies timeout check to each iteration; otherwise checks total time across all iterations.
    * Features:
        * Records execution times
        * Handles timeout conditions
        * Calculates average execution time across iterations
        * Logs the function name and execution time (with optional arguments)
        * Returns the result of the original function (unless timeout occurs)

#### Example Usage:

```python
import time
import logging
from nano_dev_utils import timer

# if printout is not enabled, a logger must be configured in order to see timing results
logging.basicConfig(filename='timer example.log',
                    level=logging.INFO,  # DEBUG, WARNING, ERROR, CRITICAL
                    format='%(asctime)s - %(levelname)s: %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S')

# Basic timing
@timer.timeit()
def my_function(a, b=10):
    """A sample function."""
    time.sleep(0.1)
    return a + b

timer.init(precision=6, verbose=True)
'''Alternative options: 
timer.update({'precision': 6, 'verbose': True})  # 1. Using update method  

from nano_dev_utils.timers import Timer  # 2. explicit instantiation
timer = Timer(precision=6, verbose=True)  
'''

timer.update({'printout': True})  # allow printing to console

# Advanced usage with timeout and iterations
@timer.timeit(iterations=5, timeout=0.5, per_iteration=True)
def critical_function(x):
    """Function with timeout check per iteration."""
    time.sleep(0.08)
    return x * 2

result1 = my_function(5, b=20)  # Shows args/kwargs and timing
result2 = critical_function(10)  # Runs 5 times with per-iteration timeout
```

### `dynamic_importer.py`

This module provides an `Importer` class for lazy loading and caching module imports.

#### `Importer` Class

* **`__init__(self)`**: Initializes an `Importer` instance with an empty dictionary `imported_modules` to cache imported modules.

* **`import_mod_from_lib(self, library: str, module_name: str) -> ModuleType | Any`**: Lazily imports a module from a specified library and caches it.
    * `library` (str): The name of the library (e.g., "os", "requests").
    * `module_name` (str): The name of the module to import within the library (e.g., "path", "get").
    * Returns the imported module. If the module has already been imported, it returns a cached instance.
    * Raises `ImportError` if the module cannot be found.

#### Example Usage:

```python
from nano_dev_utils import importer

os_path = importer.import_mod_from_lib("os", "path")
print(f"Imported os.path: {os_path}")

requests_get = importer.import_mod_from_lib("requests", "get")
print(f"Imported requests.get: {requests_get}")

# Subsequent calls will return the cached module
os_path_again = importer.import_mod_from_lib("os", "path")
print(f"Imported os.path again (cached): {os_path_again}")
```

### `release_ports.py`

This module provides a `PortsRelease` class to identify and release processes 
listening on specified TCP ports.    
It supports Windows, Linux, and macOS.

#### `PortsRelease` Class

* **`__init__(self, default_ports: list[int] | None = None)`**: 
* Initializes a `PortsRelease` instance.
    * `default_ports`: A list of default ports to manage. If not provided, it defaults to `[6277, 6274]`.

* **`get_pid_by_port(self, port: int) -> int | None`**: A static method that attempts to find   
     a process ID (PID) listening on a given `port`.       
*    It uses platform-specific commands (`netstat`, `ss`, `lsof`).       
*    Returns the PID if found, otherwise `None`.    

* **`kill_process(self, pid: int) -> bool`**: A static method that attempts to kill the process 
  with the given `pid`.   
* It uses platform-specific commands (`taskkill`, `kill -9`). 
* Returns `True` if the process was successfully killed, `False` otherwise. 

* **`release_all(self, ports: list[int] | None = None) -> None`**: Releases all processes listening on the specified `ports`.   
    * `ports`: A list of ports to release.   
    * If `None`, it uses the `default_ports` defined during initialization.   
    * For each port, it first tries to get the PID and then attempts to kill the process.       
    * It logs the actions and any errors encountered. Invalid port numbers in the provided list are skipped.

#### Example Usage:

```python
import logging
from nano_dev_utils import ports_release, PortsRelease

 
logging.basicConfig(filename='port release.log',
                    level=logging.INFO,  # DEBUG, WARNING, ERROR, CRITICAL 
                    format='%(asctime)s - %(levelname)s: %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S')


ports_release.release_all()

# Create an instance with custom ports
custom_ports_releaser = PortsRelease(default_ports=[8080, 9000, 6274])
custom_ports_releaser.release_all(ports=[8080, 9000])

# Release only the default ports
ports_release.release_all()
```


## License
This project is licensed under the MIT License. 
See [LICENSE](https://github.com/yaronday/nano_dev_utils/blob/master/LICENSE) for details.