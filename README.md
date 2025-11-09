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

## `file_tree_display.py`

This module provides a utility for generating a visually structured directory tree.  
It supports recursive traversal, customizable hierarchy styles, and inclusion / exclusion  
patterns for directories and files.  
Output can be displayed in the console or saved to a file.


#### Key Features

- Recursively displays and logs directory trees
- Efficient directory traversal
- Blazing fast (see Benchmarks below)
- Generates human-readable file tree structure 
- Supports including / ignoring specific directories or files via pattern matching
- Customizable tree display output
- Optionally saves the resulting tree to a text file
- Lightweight, flexible and easily configurable


### Benchmarks

The measurements were carried out on unfiltered folders containing multiple files und subdirectories, using SSD.   
Avg. time was measured over 20 runs per configuration, using `timeit` decorator I've implemented in this package. 

Comparing FileTreeDisplay (FTD) with
[win_tree_wrapper](https://github.com/yaronday/nano_dev_utils/blob/master/benchmark/win_tree_wrapper.py) 
(Windows [tree](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/tree) 
wrapper which I've implemented for this purpose).    
[Benchtest code](https://github.com/yaronday/nano_dev_utils/blob/master/benchmark/benchtest.py)  

### Performance Comparison — FTD vs.`tree`

<table>
<tr><th>Test Context </th><th>Results</th></tr>
<tr><td>

| Metric               | Test1  | Test2      |
|:---------------------|:-------|:-----------|
| **Files**            | 10553  | 138492     |
| **Folders**          | 1235   | 20428      |
| **Wrapper Overhead** | ~30 ms | negligible |

</td><td>

| Tool     | T1 (s) | T2 (s) | Relative Speed |
|:---------|:------:|:------:|:--------------:|
| **FTD**  | 0.196  | 2.900* |       —        |
| **tree** | 0.390  | 5.018  |   ~2x slower   |

</td></tr> </table>

***Without sorting** FTD takes 162 ms and 2.338 s for Test1 and Test2, respectively.  
FTD is roughly **1.7x–2.4x faster** than the native `tree` binary across both datasets.  

### Brief Analysis

### I. Linear scaling as a function of entries 
FTD performance scales almost perfectly linearly with total entries:

* **T1:** 10 k files → 0.2 s
* **T2:** 138 k files → 2.9 s
  → ~14x more files → ~15x more runtime => expected by linearity.

### II. Figuring out why `tree` is nearly 2 times slower than my FTD    
Although `tree` is implemented in C, it incurs more I/O work:  
* Performs full `lstat()` on each entry (permissions, timestamps, etc.).  
* Prints incrementally to `stdout` → many system calls (syscalls).  
* Handles color / formatting output.  

My FTD avoids this by:  

* Using `os.scandir()` (caching stat info).
* Filtering and sorting in-memory.
* Buffering output before optional print/write.

Result: lower syscall count and fewer I/O stalls.

### III. Python overhead is clearly negligible
Even at 2.9 s for ~160K entries, throughput ~55K entries/s — close to filesystem limits on SSDs.
Measured wrapper overhead (~30 ms) is < 1 % of total runtime.

### Key Insights

| Observation                    | Explanation                                         |
|:-------------------------------|:----------------------------------------------------|
| **FTD ~2x faster than `tree`** | Avoids per-file printing and redundant stats.       |
| **I/O-bound execution**        | Filesystem metadata fetch dominates total time.     |
| **Linear runtime scaling**     | Recursive generator design adds no hidden overhead. |
| **Stable memory footprint**    | Uses streaming generators and `StringIO` buffering. |

### Conclusions 

* **FTD outperforms `tree` by roughly 2x** on both moderate and large datasets.  
* **Runtime scales linearly** with total directory entries.  
* **Python layer overhead is negligible** — performance is bounded by kernel I/O.


#### Class Overview

**`FileTreeDisplay`**
Constructs and manages the visual representation of a folder structure of a path or of a disk drive.

**Initialization Parameters**

| Parameter                             | Type                                | Description                                                                      |
|:--------------------------------------|:------------------------------------|:---------------------------------------------------------------------------------|
| `root_dir`                            | `str`                               | Path to the directory to scan.                                                   |
| `filepath`                            | `str / None`                        | Optional output destination for the saved file tree.                             |                                               
| `ignore_dirs`                         | `list[str] or set[str] or None`     | Directory names or patterns to skip.                                             |                                                
| `ignore_files`                        | `list[str] or set[str] or None`     | File names or patterns to skip.                                                  |
| `include_dirs`                        | `list[str] or set[str] or None`     | Only include specified folder names or patterns.                                 |
| `include_files`                       | `list[str] or set[str] or None`     | Only include specified file names or patterns, '*.pdf' - only include pdfs.      |
| `style`                               | `str`                               | Characters used to mark hierarchy levels. Defaults to `'classic'`.               |
| `indent`                              | `int`                               | Number of style characters per level. Defaults `2`.                              |
| `files_first`                         | `bool`                              | Determines whether to list files first. Defaults to False.                       |
| `skip_sorting`                        | `bool`                              | Skip sorting directly, even if configured.                                       |
| `sort_key_name`                       | `str`                               | Sort key. Lexicographic ('lex') or 'custom'. Defaults to 'natural'.              |
| `reverse`                             | `bool`                              | Reversed sorting order.                                                          |
| `custom_sort`                         | `Callable[[str], Any] / None`       | Custom sort key function.                                                        |
| `title`                               | `str`                               | Custom title shown in the output.                                                |
| `save2file`                           | `bool`                              | Save file tree (folder structure) info into a file.                              |
| `printout`                            | `bool`                              | Print file tree info.                                                            |

#### Core Methods

- `file_tree_display(save2file: bool = True) -> str | None`  
Generates the directory tree. If `save2file=True`, saves the output; otherwise prints it directly.

- `_build_tree(dir_path, *, prefix, style, sort_key,   
   files_first, dir_filter, file_filter, reverse, indent) -> Generator[str, None, None]`  
Recursively traverses the directory tree in depth-first order (DFS) and yields formatted lines representing the file and folder structure.

| Parameter                           | Type                    | Description                                                                  |
|-------------------------------------|-------------------------|------------------------------------------------------------------------------|
| **`dir_path`**                      | `str`                   | Path to the directory being traversed.                                       |
| **`prefix`**                        | `str`                   | Current indentation prefix for nested entries.                               |
| **`style`**                         | `dict[str, str]`        | Connector style mapping with keys: `branch`, `end`, `space`, and `vertical`. |
| **`sort_key`**                      | `Callable[[str], Any]`  | Function used to sort directory and file names.                              |
| **`files_first`**                   | `bool`                  | If `True`, list files before subdirectories.                                 |
| **`dir_filter`**, **`file_filter`** | `Callable[[str], bool]` | Predicates to include or exclude directories and files.                      |
| **`reverse`**                       | `bool`                  | If `True`, reverses the sort order.                                          |
| **`indent`**                        | `int`                   | Number of spaces (or repeated characters) per indentation level.             |


#### Example Usage

```python
from pathlib import Path
from nano_dev_utils.file_tree_display import FileTreeDisplay

root = r'c:/your_root_dir'
target_path = r'c:/your_target_path'
filename = 'filetree.md'
filepath = str(Path(target_path, filename))

ftd = FileTreeDisplay(root_dir=root,
                      ignore_dirs=['.git', 'node_modules', '.idea'],
                      ignore_files=['.gitignore', '*.toml'], 
                      style='classic',
                      include_dirs=['src', 'tests', 'snapshots'],
                      filepath=filepath, 
                      sort_key_name='custom',
                      custom_sort=(lambda x: any(ext in x.lower() for ext in ('jpg', 'png'))),
                      files_first=True,
                      reverse=True
                     )
ftd.file_tree_display()
```

#### Custom connector style   
You can define and register your own connector styles at runtime by adding entries to style_dict:

```Python
from nano_dev_utils.file_tree_display import FileTreeDisplay
ftd = FileTreeDisplay(root_dir=".")
ftd.style_dict["plus2"] = ftd.connector_styler("+-- ", "+== ")
ftd.style = "plus2"
ftd.printout = True
ftd.file_tree_display()
```


#### Error Handling

The module raises well-defined exceptions for common issues:

- `NotADirectoryError` when the path is not a directory
- `PermissionError` for unreadable directories or write-protected files
- `OSError` for general I/O or write failures

***

## License
This project is licensed under the MIT License. 
See [LICENSE](https://github.com/yaronday/nano_dev_utils/blob/master/LICENSE) for details.