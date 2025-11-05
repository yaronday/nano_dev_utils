from pathlib import Path
from unittest import mock
import pytest
from pytest import MonkeyPatch

from nano_dev_utils.file_tree_display import FileTreeDisplay


@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    """Creates a temporary directory structure for testing."""
    (tmp_path / 'dir1').mkdir()
    (tmp_path / 'dir1' / 'nested').mkdir()
    (tmp_path / 'dir1' / 'nested' / 'file_a.txt').write_text('alpha', encoding='utf-8')
    (tmp_path / 'dir2').mkdir()

    (tmp_path / 'dir2' / 'file_b.txt').write_text('bravo', encoding='utf-8')
    (tmp_path / 'ignored_dir').mkdir()
    (tmp_path / 'ignored_file.txt').write_text('ignore', encoding='utf-8')
    return tmp_path


@pytest.fixture
def ftd_mock(sample_dir: Path) -> FileTreeDisplay:
    """Fixture to provide FileTreeDisplay instance with a temp dir."""
    return FileTreeDisplay(root_dir=str(sample_dir))


def test_basic_structure_generation(ftd_mock: FileTreeDisplay) -> None:
    """Ensure the generator yields expected directory structure lines."""
    lines = list(
        ftd_mock._build_tree(
            str(ftd_mock.root_path),
            prefix='',
            style=ftd_mock.format_style(),
            sort_key=ftd_mock._resolve_sort_key(),
            files_first=ftd_mock.files_first,
            dir_filter=ftd_mock.dir_filter,
            file_filter=ftd_mock.file_filter,
            reverse=ftd_mock.reverse,
            indent=ftd_mock.indent,
        )
    )
    assert any('dir1' in line for line in lines)
    assert any('dir2' in line for line in lines)
    assert any('file_a.txt' in line or 'file_b.txt' in line for line in lines)


def test_ignore_specific_dir(ftd_mock: FileTreeDisplay, sample_dir: Path) -> None:
    """Test that a specific directory is properly ignored."""
    ftd_mock.init(root_dir=str(sample_dir), ignore_dirs=['ignored_dir'])
    tree = '\n'.join(
        ftd_mock._build_tree(
            str(sample_dir),
            prefix='',
            style=ftd_mock.format_style(),
            sort_key=ftd_mock._resolve_sort_key(),
            files_first=ftd_mock.files_first,
            dir_filter=ftd_mock.dir_filter,
            file_filter=ftd_mock.file_filter,
            reverse=ftd_mock.reverse,
            indent=ftd_mock.indent,
        )
    )
    assert 'ignored_dir' not in tree
    assert 'ignored_file.txt' in tree  # not ignored


def test_ignore_specific_file(ftd_mock: FileTreeDisplay, sample_dir: Path) -> None:
    """Test that a specific file is properly ignored."""
    ftd_mock.init(root_dir=str(sample_dir), ignore_files=['ignored_file.txt'])
    tree = '\n'.join(
        ftd_mock._build_tree(
            str(sample_dir),
            prefix='',
            style=ftd_mock.format_style(),
            sort_key=ftd_mock._resolve_sort_key(),
            files_first=ftd_mock.files_first,
            dir_filter=ftd_mock.dir_filter,
            file_filter=ftd_mock.file_filter,
            reverse=ftd_mock.reverse,
            indent=ftd_mock.indent,
        )
    )
    assert 'ignored_file.txt' not in tree
    assert 'ignored_dir' in tree


def test_display_mode(
    ftd_mock: FileTreeDisplay, capsys: pytest.CaptureFixture[str]
) -> None:
    """Ensure printout mode prints to stdout and doesn't save to file."""
    ftd_mock.printout = True
    ftd_mock.save2file = False
    ftd_mock.file_tree_display()
    captured = capsys.readouterr()
    assert 'dir1' in captured.out
    assert 'dir2' in captured.out


def test_style_and_indent_applied(ftd_mock: FileTreeDisplay) -> None:
    """Ensure style and indentation customize formatted output."""
    ftd_mock.init(root_dir=str(ftd_mock.root_path), style='classic', indent=3)
    lines = list(
        ftd_mock._build_tree(
            str(ftd_mock.root_path),
            prefix='',
            style=ftd_mock.format_style(),
            sort_key=ftd_mock._resolve_sort_key(),
            files_first=ftd_mock.files_first,
            dir_filter=ftd_mock.dir_filter,
            file_filter=ftd_mock.file_filter,
            reverse=ftd_mock.reverse,
            indent=ftd_mock.indent,
        )
    )
    assert all(
        line.startswith('├──')
        for line in lines
        if not (line.startswith('│') or line.startswith('└──'))
    )


def test_custom_styles(ftd_mock: FileTreeDisplay) -> None:
    """Ensure dynamic user-added styles work correctly."""
    ftd_mock.style_dict['plus'] = ftd_mock.connector_styler('+-- ', '+== ')
    ftd_mock.style_dict['arrowstar'] = ftd_mock.connector_styler('→* ', '↳* ')

    plus_style = ftd_mock.style_dict['plus']
    arrowstar_style = ftd_mock.style_dict['arrowstar']

    for s in (plus_style, arrowstar_style):
        assert set(s.keys()) == {'space', 'vertical', 'branch', 'end'}
        assert isinstance(s['branch'], str)
        assert isinstance(s['end'], str)

    ftd_mock.style = 'plus'
    selected_plus = ftd_mock.format_style()
    assert selected_plus['branch'].startswith('+')

    ftd_mock.style = 'arrowstar'
    selected_arrowstar = ftd_mock.format_style()
    assert '→' in selected_arrowstar['branch'] or '↳' in selected_arrowstar['end']


def test_get_tree_info_proper_format(ftd_mock: FileTreeDisplay) -> None:
    """Check that get_tree_info formats output with root and lines."""
    iterator = (f'line_{i}' for i in range(3))
    result = ftd_mock.get_tree_info(iterator)
    lines = result.split('\n')
    assert lines[0] == f'{ftd_mock.root_path.name}/'
    assert lines[1].startswith('line_')
    assert result.count('\n') == 3


def test_build_tree_permission_error(ftd_mock: FileTreeDisplay) -> None:
    """Handle PermissionError in build_tree."""
    with mock.patch('os.scandir', side_effect=PermissionError):
        results = list(
            ftd_mock._build_tree(
                str(ftd_mock.root_path),
                prefix='',
                style=ftd_mock.format_style(),
                sort_key=ftd_mock._resolve_sort_key(),
                files_first=ftd_mock.files_first,
                dir_filter=ftd_mock.dir_filter,
                file_filter=ftd_mock.file_filter,
                reverse=ftd_mock.reverse,
                indent=ftd_mock.indent,
            )
        )
        assert any('[Permission Denied]' in line for line in results)


def test_build_tree_os_error(ftd_mock: FileTreeDisplay) -> None:
    """Handle generic OSError in build_tree."""
    with mock.patch('os.scandir', side_effect=OSError):
        results = list(
            ftd_mock._build_tree(
                str(ftd_mock.root_path),
                prefix='',
                style=ftd_mock.format_style(),
                sort_key=ftd_mock._resolve_sort_key(),
                files_first=ftd_mock.files_first,
                dir_filter=ftd_mock.dir_filter,
                file_filter=ftd_mock.file_filter,
                reverse=ftd_mock.reverse,
                indent=ftd_mock.indent,
            )
        )
        assert any('[Error reading directory]' in line for line in results)


def test_file_tree_display_invalid_dir(
    monkeypatch: MonkeyPatch, ftd_mock: FileTreeDisplay
) -> None:
    """Handle NotADirectoryError in file_tree_display."""
    ftd_mock.root_path = Path('FAKE_DIR')
    monkeypatch.setattr(Path, 'is_dir', lambda self: False)
    with pytest.raises(
        NotADirectoryError,
        match=f"The path '{ftd_mock.root_path}' is not a directory.",
    ):
        ftd_mock.file_tree_display()


def test_invalid_sort_key_raises(ftd_mock: FileTreeDisplay) -> None:
    """Ensure invalid sort key raises ValueError."""
    ftd_mock.sort_key_name = 'unknown_key'
    with pytest.raises(ValueError, match='Invalid sort key name'):
        ftd_mock._resolve_sort_key()


def test_custom_sort_key_without_function_raises(ftd_mock: FileTreeDisplay) -> None:
    """Ensure 'custom' sort requires a custom_sort function."""
    ftd_mock.sort_key_name = 'custom'
    ftd_mock.custom_sort = None
    with pytest.raises(ValueError, match='custom_sort function must be specified'):
        ftd_mock._resolve_sort_key()


def test_format_style_invalid(ftd_mock: FileTreeDisplay) -> None:
    """Invalid style name raises ValueError."""
    ftd_mock.style = 'invalid-style'
    with pytest.raises(ValueError):
        ftd_mock.format_style()


def test_update_predicates_rebuilds_filters(ftd_mock: FileTreeDisplay) -> None:
    """Ensure update_predicates rebuilds the filter predicates."""
    old_dir_filter = ftd_mock.dir_filter
    ftd_mock.ignore_dirs.add('X')
    ftd_mock.update_predicates()
    assert ftd_mock.dir_filter is not old_dir_filter
