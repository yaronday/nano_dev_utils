import logging

from pathlib import Path
from nano_dev_utils.file_tree_display import FileTreeDisplay
from nano_dev_utils import timer

from win_tree_wrapper import tree_wrapper


logging.basicConfig(
    filename='Benchmark_FTD.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S',
)

ITER = 20

root = r'c:/HugeFolder'  # a directory that contains many files and subdirectories
target_path = r'YourTargetPath'

timer.update({'precision': 3})


@timer.timeit(iterations=ITER, timeout=10, per_iteration=True)
def ftd_run():
    filename = 'nano_filetree_FilesFirst.txt'
    filepath = str(Path(target_path, filename))

    ftd = FileTreeDisplay(
        root_dir=root,
        filepath=filepath,
        save2file=True,
        files_first=True,  # For the content comparison, since this is the default for 'Tree /F'
        style=' ',
    )
    return ftd.file_tree_display()


@timer.timeit(iterations=ITER, timeout=10, per_iteration=True)
def win_tree_cmd():
    filename = 'wintree_w_files.txt'
    filepath = str(Path(target_path, filename))
    tree_wrapper(root_path=root, show_files=True, save2file=True, filepath=filepath)


def run():
    ftd_run()
    win_tree_cmd()


if __name__ == '__main__':
    run()
