# nano_dev_utils

A collection of small Python utilities for developers.

## Modules

### `timers.py`

This module provides a `Timer` class for measuring the execution time of code blocks and functions.

#### `Timer` Class

* **`__init__(self, precision: int = 4, verbose: bool = False)`**: Initializes a `Timer` instance.
    * `precision`: The number of decimal places to record and    
       display time durations. Defaults to 4.
    * `verbose`: Optionally displays the function's positional arguments (args) and keyword arguments (kwargs).       
       Defaults to `False`.

* **`timeit(self, func: Callable[P, R]) -> Callable[P, R]`**:   
      Decorator that times function execution with automatic unit scaling.   
    * When the decorated function is called, this decorator records the start and end times,   
      calculates the total execution time, prints the function name and execution    
      time (optionally including arguments), and returns the result of the original function.

#### Example Usage:

```python
import time
from nano_dev_utils.timers import Timer

timer = Timer(precision=6, verbose=True)


@timer.timeit
def my_function(a, b=10):
  """A sample function."""
  time.sleep(0.1)
  return a + b


result = my_function(5, b=20)
print(f"Result: {result}")
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
from nano_dev_utils.dynamic_importer import Importer

importer = Importer()

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
from nano_dev_utils import PortsRelease

# in case you're interested in logging 
logging.basicConfig(filename='port release.log',
                    level=logging.INFO,  # specify here desire level, e.g. DEBUG etc.
                    format='%(asctime)s - %(levelname)s: %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S')

# Create an instance with default ports
port_releaser = PortsRelease()
port_releaser.release_all()

# Create an instance with custom ports
custom_ports_releaser = PortsRelease(default_ports=[8080, 9000, 6274])
custom_ports_releaser.release_all(ports=[8080, 9000])

# Release only the default ports
port_releaser.release_all()
```

## License
This project is licensed under the MIT License. 
See [LICENSE](https://github.com/yaronday/nano_dev_utils/blob/master/LICENSE.md) for details.