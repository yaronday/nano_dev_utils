"""CLI interface for FileTreeDisplay with config file, color output, and statistics.

Usage examples:
    py -m ftd_cli -r ./src --printout
    py -m ftd_cli --cfg ./ftd.json
"""

import argparse
import sys


from pathlib import Path
from typing import Any

from .file_tree_display import FileTreeDisplay
from .common import load_cfg_file


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Display or export a formatted file tree of a directory.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument('--cfg', type=str, help='Path to JSON config file.')
    parser.add_argument('--root-dir', '-r', type=str, help='Root directory to display.')
    parser.add_argument('--filepath', '-o', type=str, help='Output file path.')
    parser.add_argument(
        '--ignore-dirs', nargs='*', default=None, help='Directories to ignore.'
    )
    parser.add_argument(
        '--ignore-files', nargs='*', default=None, help='Files to ignore.'
    )
    parser.add_argument(
        '--include-dirs', nargs='*', default=None, help='Directories to include.'
    )
    parser.add_argument(
        '--include-files', nargs='*', default=None, help='Files to include.'
    )
    parser.add_argument(
        '--style',
        '-s',
        choices=['classic', 'dash', 'arrow', 'plus'],
        default='classic',
        help='Tree connector style.',
    )
    parser.add_argument(
        '--indent', '-i', type=int, default=2, help='Indent width per level.'
    )
    parser.add_argument(
        '--files-first',
        '-f',
        action='store_true',
        default=False,
        help='List files before directories.',
    )
    parser.add_argument(
        '--skip-sorting', action='store_true', default=False, help='Disable sorting.'
    )
    parser.add_argument(
        '--sort-key',
        choices=['natural', 'lex', 'custom'],
        default='natural',
        help='Sorting mode.',
    )
    parser.add_argument('--reverse', action='store_true', help='Reverse sort order.')
    parser.add_argument('--no-save', action='store_true', help='Do not save to file.')
    parser.add_argument(
        '--printout', '-p', action='store_true', help='Print tree to stdout.'
    )
    parser.add_argument('--version', action='version', version='file_tree_cli 1.0')
    return parser.parse_args(argv)


def merge_config(
    cli_args: argparse.Namespace, cfg_dict: dict[str, Any]
) -> dict[str, Any]:
    """Merge CLI args and config file into a unified options dict."""
    merged = {**cfg_dict}
    for k, v in vars(cli_args).items():
        if v is not None and k != 'config':
            merged[k] = v
    return merged


def main() -> None:
    args = parse()
    cfg_dict = load_cfg_file(args.config)
    opts = merge_config(args, cfg_dict)

    root_dir = Path(opts.get('root_dir') or Path.cwd())
    if not root_dir.exists():
        sys.exit(f"Error: root directory '{root_dir}' does not exist.")

    filepath = opts.get('filepath')
    if not filepath and not opts.get('no-save'):
        filepath = str(root_dir.with_name(f'{root_dir.name}_filetree.txt'))

    ftd = FileTreeDisplay(
        root_dir=str(root_dir),
        filepath=filepath,
        ignore_dirs=opts.get('ignore_dirs') or [],
        ignore_files=opts.get('ignore_files') or [],
        include_dirs=opts.get('include_dirs') or [],
        include_files=opts.get('include_files') or [],
        style=opts.get('style', 'classic'),
        indent=int(opts.get('indent', 2)),
        files_first=bool(opts.get('files_first', False)),
        skip_sorting=bool(opts.get('skip_sorting', False)),
        sort_key_name=opts.get('sort_key', 'natural'),
        reverse=bool(opts.get('reverse', False)),
        save2file=not opts.get('no_save', False),
        printout=opts.get('printout', False),
    )

    try:
        ftd.file_tree_display()
    except Exception as e:
        sys.exit(f'Error: {e}')


if __name__ == '__main__':
    main()
