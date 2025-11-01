from pathlib import Path
from unittest import mock
import pytest
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
def ftd(sample_dir: Path) -> FileTreeDisplay:
    """Fixture to provide FileTreeDisplay instance with a temp dir."""
    return FileTreeDisplay(root_dir=str(sample_dir))


def test_basic_structure_generation(ftd: FileTreeDisplay) -> None:
    """Ensure the generator yields expected directory structure lines."""
    output = list(ftd.build_tree(str(ftd.root_path)))
    names = [line.strip('-') for line in output]
    assert any('dir1' in n for n in names)
    assert any('dir2' in n for n in names)
    assert any('file_a.txt' in n or 'file_b.txt' in n for n in names)


def test_ignore_specific_dir(ftd: FileTreeDisplay, sample_dir: Path) -> None:
    """Test that a specific directory is properly ignored."""
    ftd.update({'ignore_dirs': {'ignored_dir'}})
    tree = '\n'.join(ftd.build_tree(str(sample_dir)))
    assert 'ignored_dir' not in tree
    assert 'ignored_file.txt' in tree  # Not ignored, so should be present


def test_ignore_specific_file(ftd: FileTreeDisplay, sample_dir: Path) -> None:
    """Test that a specific file is properly ignored."""
    ftd.update({'ignore_files': {'ignored_file.txt'}})
    tree = '\n'.join(ftd.build_tree(str(sample_dir)))
    assert 'ignored_file.txt' not in tree
    assert 'ignored_dir' in tree  # Not ignored, so should be present


def test_display_mode(
    ftd: FileTreeDisplay, sample_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that display-only mode prints to stdout and not to file."""
    ftd.printout = True
    ftd.save2file = False
    ftd.file_tree_display()
    captured = capsys.readouterr()
    assert 'dir1' in captured.out
    assert not Path(sample_dir / f'{sample_dir.name}{DEFAULT_SFX}').exists()


def test_style_and_indent_applied(ftd: FileTreeDisplay, sample_dir: Path) -> None:
    """Ensure style and indentation customize the formatted output."""
    ftd.update({'style': '*', 'indent': 3})
    lines = list(ftd.build_tree(str(sample_dir)))
    assert all(line.startswith('***') for line in lines if not line.startswith('['))


def test_get_tree_info_proper_format(ftd: FileTreeDisplay) -> None:
    """Check that get_tree_info formats output with root and lines."""
    prefix = 'item_'
    iterator = (f'{prefix}{i}' for i in range(4))
    result = ftd.get_tree_info(iterator)
    lines = result.split('\n')
    assert lines[0] == f'{ftd.root_path.name}/'
    assert lines[1] == f'{prefix}0'
    assert lines[-1] == f'{prefix}3'
    assert result.count('\n') == 4


def test_build_tree_permission_error(ftd: FileTreeDisplay) -> None:
    """Handle PermissionError in build_tree."""
    with mock.patch('os.scandir', side_effect=PermissionError):
        results = list(ftd.build_tree(str(ftd.root_path)))
        # Should yield one "Permission Denied" line
        assert any('[Permission Denied]' in line for line in results)


def test_build_tree_oserror(ftd: FileTreeDisplay) -> None:
    """Handle generic OSError in build_tree."""
    with mock.patch('os.scandir', side_effect=OSError):
        results = list(ftd.build_tree(str(ftd.root_path)))
        assert any('[Error reading directory]' in line for line in results)


def test_format_out_path_with_filepath(ftd: FileTreeDisplay, tmp_path: Path) -> None:
    """format_out_path uses filepath property if set."""
    ftd.filepath = str(tmp_path / 'myfile.txt')
    out = ftd.format_out_path()
    assert out == Path(ftd.filepath)


def test_format_out_path_without_filepath(ftd: FileTreeDisplay, tmp_path: Path) -> None:
    """format_out_path computes output filename if filepath not set."""
    ftd.filepath = None
    expected = tmp_path / f'{tmp_path.name}{DEFAULT_SFX}'
    out = ftd.format_out_path()
    assert out == expected
