from pathlib import Path
from unittest import mock
import pytest
from pytest import MonkeyPatch

from nano_dev_utils.file_tree_display import FileTreeDisplay, DEFAULT_SFX


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
    output = list(ftd_mock.build_tree(str(ftd_mock.root_path)))
    names = [line.strip('-') for line in output]
    assert any('dir1' in n for n in names)
    assert any('dir2' in n for n in names)
    assert any('file_a.txt' in n or 'file_b.txt' in n for n in names)


def test_ignore_specific_dir(ftd_mock: FileTreeDisplay, sample_dir: Path) -> None:
    """Test that a specific directory is properly ignored."""
    ftd_mock.update({'ignore_dirs': {'ignored_dir'}})
    tree = '\n'.join(ftd_mock.build_tree(str(sample_dir)))
    assert 'ignored_dir' not in tree
    assert 'ignored_file.txt' in tree  # Not ignored, so should be present


def test_ignore_specific_file(ftd_mock: FileTreeDisplay, sample_dir: Path) -> None:
    """Test that a specific file is properly ignored."""
    ftd_mock.update({'ignore_files': {'ignored_file.txt'}})
    tree = '\n'.join(ftd_mock.build_tree(str(sample_dir)))
    assert 'ignored_file.txt' not in tree
    assert 'ignored_dir' in tree  # Not ignored, so should be present


def test_display_mode(
    ftd_mock: FileTreeDisplay, sample_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that display-only mode prints to stdout and not to file."""
    ftd_mock.printout = True
    ftd_mock.save2file = False
    ftd_mock.file_tree_display()
    captured = capsys.readouterr()
    assert 'dir1' in captured.out
    assert not Path(sample_dir / f'{sample_dir.name}{DEFAULT_SFX}').exists()


def test_style_and_indent_applied(ftd_mock: FileTreeDisplay, sample_dir: Path) -> None:
    """Ensure style and indentation customize the formatted output."""
    ftd_mock.update({'style': '*', 'indent': 3})
    lines = list(ftd_mock.build_tree(str(sample_dir)))
    assert all(line.startswith('***') for line in lines if not line.startswith('['))


def test_get_tree_info_proper_format(ftd_mock: FileTreeDisplay) -> None:
    """Check that get_tree_info formats output with root and lines."""
    prefix = 'item_'
    iterator = (f'{prefix}{i}' for i in range(4))
    result = ftd_mock.get_tree_info(iterator)
    lines = result.split('\n')
    assert lines[0] == f'{ftd_mock.root_path.name}/'
    assert lines[1] == f'{prefix}0'
    assert lines[-1] == f'{prefix}3'
    assert result.count('\n') == 4


def test_build_tree_permission_error(ftd_mock: FileTreeDisplay) -> None:
    """Handle PermissionError in build_tree."""
    with mock.patch('os.scandir', side_effect=PermissionError):
        results = list(ftd_mock.build_tree(str(ftd_mock.root_path)))
        # Should yield one "Permission Denied" line
        assert any('[Permission Denied]' in line for line in results)


def test_build_tree_os_error(ftd_mock: FileTreeDisplay) -> None:
    """Handle generic OSError in build_tree."""
    with mock.patch('os.scandir', side_effect=OSError):
        results = list(ftd_mock.build_tree(str(ftd_mock.root_path)))
        assert any('[Error reading directory]' in line for line in results)


def test_file_tree_display_invalid_dir(
    monkeypatch: MonkeyPatch, ftd_mock: FileTreeDisplay
) -> None:
    """Handle NotADirectoryError in file_tree_display"""
    ftd_mock.root_path = Path('NEW_ROOT_DIR')
    monkeypatch.setattr(type(ftd_mock.root_path), 'is_dir', lambda self: False)
    with pytest.raises(
        NotADirectoryError,
        match=f"The path '{str(ftd_mock.root_path)}' is not a directory.",
    ):
        ftd_mock.file_tree_display()
