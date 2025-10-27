from pathlib import Path
import pytest
from nano_dev_utils import FileTreeDisplay, ftd_consts

FTD_PATCH_PATH = 'nano_dev_utils.file_tree_display'


@pytest.fixture
def sample_dir(tmp_path):
    """Creates a temporary directory structure for testing."""
    (tmp_path / 'dir1').mkdir()
    (tmp_path / 'dir1' / 'nested').mkdir()
    (tmp_path / 'dir1' / 'nested' / 'file_a.txt').write_text('alpha', encoding='utf-8')
    (tmp_path / 'dir2').mkdir()
    (tmp_path / 'dir2' / 'file_b.txt').write_text('bravo', encoding='utf-8')
    (tmp_path / 'ignored_dir').mkdir()
    (tmp_path / 'ignored_file.txt').write_text('ignore', encoding='utf-8')
    return tmp_path


def test_basic_structure_generation(sample_dir):
    """Ensure the generator yields expected directory structure lines."""
    ftd = FileTreeDisplay(root_dir=str(sample_dir))
    output = list(ftd.build_tree(str(sample_dir)))
    names = [line.strip('-') for line in output]
    assert any('dir1' in n for n in names)
    assert any('dir2' in n for n in names)
    assert any('file_a.txt' in n or 'file_b.txt' in n for n in names)


def test_ignore_dirs_files(sample_dir):
    """Verify ignored dirs and files are excluded from output."""
    dir2ignore = 'ignored_dir'
    file2ignore = 'ignored_file.txt'
    ftd = FileTreeDisplay(
        root_dir=str(sample_dir),
        ignore_dirs={dir2ignore},
        ignore_files={file2ignore},
    )
    lines = list(ftd.build_tree(str(sample_dir)))
    tree = '\n'.join(lines)
    assert dir2ignore not in tree
    assert file2ignore not in tree


def test_display_mode(monkeypatch, sample_dir, capsys):
    """Test that display-only mode prints to stdout and not to file."""
    ftd = FileTreeDisplay(root_dir=str(sample_dir))
    ftd.file_tree_display(save2file=False)
    captured = capsys.readouterr()
    assert ftd_consts.TITLE in captured.out
    assert 'dir1' in captured.out
    assert not Path(sample_dir / f'{sample_dir.name}{ftd_consts.DEFAULT_SFX}').exists()


def test_style_and_indent_applied(sample_dir):
    """Ensure style and indentation customize the formatted output."""
    ftd = FileTreeDisplay(root_dir=str(sample_dir), style='*', indent=3)
    lines = list(ftd.build_tree(str(sample_dir)))
    assert all(line.startswith('***') for line in lines if not line.startswith('['))


def test_save2file_creates_file(sample_dir):
    """Validate that save2file writes a file and returns correct path."""
    ftd = FileTreeDisplay(root_dir=str(sample_dir))
    header_txt = 'header_line'
    prefix = 'line_'
    header = [header_txt]
    iterator = (f'{prefix}{i}' for i in range(3))
    result_path = ftd.save2file(header, iterator)
    assert Path(result_path).exists()
    content = Path(result_path).read_text(encoding='utf-8')
    assert header_txt in content
    assert f'{prefix}0' in content


def test_custom_filepath(sample_dir):
    """Check that user-specified filepath is respected."""
    ftd = FileTreeDisplay(root_dir=str(sample_dir))
    custom = str(sample_dir / 'custom_output.txt')
    header = ['H']
    iterator = (f'L{i}' for i in range(2))
    ftd.save2file(header, iterator, filepath=custom)
    assert Path(custom).exists()
    assert 'H' in Path(custom).read_text(encoding='utf-8')


def test_save2file_overwrites_existing_file(sample_dir):
    """Ensure that save2file overwrites an existing file as expected."""
    ftd = FileTreeDisplay(root_dir=str(sample_dir))
    txt1 = 'OLD_CONTENT'
    txt2 = 'NEW_HEADER'
    prefix = 'new_line_'
    existing_file_path = sample_dir / 'existing_output.txt'
    existing_file_path.write_text(txt1, encoding='utf-8')
    header = [txt2]
    iterator = (f'{prefix}{i}' for i in range(2))
    ftd.save2file(header, iterator, filepath=str(existing_file_path))
    content = existing_file_path.read_text(encoding='utf-8')

    assert txt1 not in content
    assert txt2 in content
    assert f'{prefix}1' in content


def test_save2file_empty_header_and_iterator(sample_dir):
    """Test behavior with an empty header and an empty iterator."""
    ftd = FileTreeDisplay(root_dir=str(sample_dir))
    out_file = sample_dir / 'empty_file.txt'
    header = []
    iterator = (i for i in [])  # An empty generator
    ftd.save2file(header, iterator, filepath=str(out_file))
    content = out_file.read_text(encoding='utf-8')
    assert content == '\n'


def test_save2file_permission_error(sample_dir, mocker):
    """Test that a PermissionError is caught and re-raised correctly."""
    ret_value = 'Custom Permission Denied'
    mock_t_msg = mocker.patch(f'{FTD_PATCH_PATH}.t_msg', return_value=ret_value)

    mock_path_open = mocker.patch.object(
        Path, 'open', side_effect=PermissionError('Mocked Permission Denied')
    )

    ftd = FileTreeDisplay(root_dir=str(sample_dir))

    bad_path = sample_dir / 'protected.txt'
    header = ['Header']
    iterator = (f'line {i}' for i in range(1))

    with pytest.raises(PermissionError, match=ret_value):
        ftd.save2file(header, iterator, filepath=str(bad_path))

    mock_t_msg.assert_called_once()
    assert mock_t_msg.call_args[0][0] == ftd_consts.WR_PERMISSION_DENIED
    assert mock_t_msg.call_args[1]['filepath'] == bad_path

    mock_path_open.assert_called_once()
    assert mock_path_open.call_args[0][0] == 'w'
    assert mock_path_open.call_args[1]['encoding'] == 'utf-8'


def test_save2file_os_error_invalid_path(sample_dir, mocker):
    """Test that a generic OSError (like a non-existent path) is caught."""
    ret_value = 'Custom File Write Error'
    mock_t_msg = mocker.patch(f'{FTD_PATCH_PATH}.t_msg', return_value=ret_value)

    mock_path_open = mocker.patch.object(
        Path, 'open', side_effect=OSError('Mocked Permission Denied')
    )

    ftd = FileTreeDisplay(root_dir=str(sample_dir))

    bad_path = sample_dir / 'protected.txt'
    header = ['Header']
    iterator = (f'line {i}' for i in range(1))

    with pytest.raises(OSError, match=ret_value) as exec_info:
        ftd.save2file(header, iterator, filepath=str(bad_path))

    assert isinstance(exec_info.value, OSError)

    mock_t_msg.assert_called_once()
    assert mock_t_msg.call_args[0][0] == ftd_consts.FILE_WR_ERR
    assert mock_t_msg.call_args[1]['filepath'] == bad_path

    mock_path_open.assert_called_once()
    assert mock_path_open.call_args[0][0] == 'w'
    assert mock_path_open.call_args[1]['encoding'] == 'utf-8'
