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


def test_ignore_bad_dir_via_patch(ftd: FileTreeDisplay, sample_dir: Path) -> None:
    dir_to_ignore = 'ignored_dir'
    with mock.patch.object(ftd, 'should_ignore',
                           side_effect=lambda name, is_dir: name == dir_to_ignore and is_dir):
        tree = '\n'.join(ftd.build_tree(str(sample_dir)))
        assert dir_to_ignore not in tree
        assert 'ignored_file.txt' in tree


def test_ignore_bad_file_via_patch(ftd: FileTreeDisplay, sample_dir: Path) -> None:
    file_to_ignore = 'ignored_file.txt'
    with mock.patch.object(ftd, 'should_ignore',
                           side_effect=lambda name, is_dir: name == file_to_ignore and not is_dir):
        tree = '\n'.join(ftd.build_tree(str(sample_dir)))
        assert file_to_ignore not in tree
        assert 'ignored_dir' in tree


def test_display_mode(ftd: FileTreeDisplay,
                      sample_dir: Path,
                      capsys: pytest.CaptureFixture[str]) -> None:
    """Test that display-only mode prints to stdout and not to file."""
    ftd.printout = True
    ftd.save2file = False
    ftd.file_tree_display()
    captured = capsys.readouterr()
    assert 'dir1' in captured.out
    assert not Path(sample_dir / f'{sample_dir.name}{DEFAULT_SFX}').exists()


def test_style_and_indent_applied(ftd: FileTreeDisplay, sample_dir: Path) -> None:
    """Ensure style and indentation customize the formatted output."""
    ftd.update({
        'style': '*',
        'indent': 3
    })
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
    with mock.patch("os.scandir", side_effect=PermissionError):
        results = list(ftd.build_tree(str(ftd.root_path)))
        # Should yield one "Permission Denied" line
        assert any("[Permission Denied]" in line for line in results)


def test_build_tree_oserror(ftd: FileTreeDisplay) -> None:
    """Handle generic OSError in build_tree."""
    with mock.patch("os.scandir", side_effect=OSError):
        results = list(ftd.build_tree(str(ftd.root_path)))
        assert any("[Error reading directory]" in line for line in results)


def test_buffer2file_permission_error(ftd: FileTreeDisplay, tmp_path: Path) -> None:
    """buffer2file should raise on PermissionError."""
    ftd.format_out_path = mock.Mock()
    fake_path = tmp_path / "fake.txt"
    ftd.format_out_path.return_value = fake_path

    with mock.patch.object(Path, "open",
                           side_effect=PermissionError("no permission")):
        with pytest.raises(PermissionError) as exc:
            ftd.buffer2file("test content")
        assert "no permission" in str(exc.value)


def test_buffer2file_oserror(ftd: FileTreeDisplay, tmp_path: Path) -> None:
    """buffer2file should propagate generic OSError."""
    ftd.format_out_path = mock.Mock()
    fake_path = tmp_path / "fake.txt"
    ftd.format_out_path.return_value = fake_path
    with mock.patch.object(Path, "open",
                           side_effect=OSError("disk error")):
        with pytest.raises(OSError) as exc:
            ftd.buffer2file("test")
        assert "Error writing file" in str(exc.value)


def test_buffer2file_creates_file(ftd: FileTreeDisplay) -> None:
    """Validate that buffer2file writes a file and returns correct path."""
    prefix = 'line_'
    iterator = (f'{prefix}{i}' for i in range(3))
    tree_info = ftd.get_tree_info(iterator)
    result_path = ftd.buffer2file(tree_info)
    assert Path(result_path).exists()
    content = Path(result_path).read_text(encoding='utf-8')
    assert f'{prefix}0' in content


def test_custom_filepath(ftd: FileTreeDisplay) -> None:
    """Check that user-specified filepath is respected."""
    custom = str(ftd.root_path / 'custom_output.txt')
    ftd.filepath = custom
    iterator = (f'L{i}' for i in range(2))
    tree_info = ftd.get_tree_info(iterator)
    ftd.buffer2file(tree_info)
    assert Path(custom).exists()
    assert '\nL1' in Path(custom).read_text(encoding='utf-8')


def test_buffer2file_overwrites_existing_file(ftd: FileTreeDisplay) -> None:
    """Ensure that buffer2file overwrites an existing file as expected."""
    existing_file_path = ftd.root_path / 'existing_output.txt'
    ftd.filepath = str(existing_file_path)
    txt1 = 'OLD_CONTENT'
    txt2 = 'NEW_HEADER'
    prefix = 'new_line_'

    existing_file_path.write_text(txt1, encoding='utf-8')
    ftd.root_path = Path(txt2)
    iterator = (f'{prefix}{i}' for i in range(2))
    tree_info = ftd.get_tree_info(iterator)

    ftd.buffer2file(tree_info)
    content = existing_file_path.read_text(encoding='utf-8')

    assert txt1 not in content
    assert txt2 in content
    assert f'{prefix}1' in content


def test_buffer2file_empty_iterator(ftd: FileTreeDisplay,
                                    sample_dir: Path) -> None:
    """Test behavior with an empty header and an empty iterator."""
    out_file = sample_dir / 'empty_file.txt'
    ftd.filepath = str(out_file)
    iterator = (i for i in [])  # An empty generator
    tree_info = ftd.get_tree_info(iterator)
    ftd.buffer2file(tree_info)
    content = out_file.read_text(encoding='utf-8')
    assert content == f'{sample_dir.name}/'


def test_format_out_path_with_filepath(ftd: FileTreeDisplay, tmp_path: Path) -> None:
    """format_out_path uses filepath property if set."""
    ftd.filepath = str(tmp_path / "myfile.txt")
    out = ftd.format_out_path()
    assert out == Path(ftd.filepath)


def test_format_out_path_without_filepath(ftd: FileTreeDisplay, tmp_path: Path) -> None:
    """format_out_path computes output filename if filepath not set."""
    ftd.filepath = None
    DEFAULT_SFX = "_filetree.txt"
    expected = tmp_path / f"{tmp_path.name}{DEFAULT_SFX}"
    out = ftd.format_out_path()
    assert out == expected
