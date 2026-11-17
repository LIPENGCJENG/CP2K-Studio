from core.local_run_runtime import LogFollower, file_snapshot


def test_wait_create_last_thirty_append(tmp_path):
    path = tmp_path / 'output.out'
    follower = LogFollower(path)
    assert follower.poll() == follower.poll() == ''
    path.write_text(''.join(f'{i}\n' for i in range(50)))
    assert follower.poll() == ''.join(f'{i}\n' for i in range(20, 50))
    assert follower.poll() == ''
    with path.open('a') as handle:
        handle.write('new line\n')
    assert follower.poll() == 'new line\n'


def test_unchanged_old_log_excluded_even_when_it_says_success(tmp_path):
    path = tmp_path / 'output.out'
    path.write_text('OLD CP2K SUCCESS\n')
    follower = LogFollower(path, file_snapshot(path))
    assert follower.poll() == ''
    with path.open('a') as handle:
        handle.write('new run\n')
    assert follower.poll() == 'new run\n'


def test_truncation_regrowth_replacement_deletion_recreation(tmp_path):
    path = tmp_path / 'output.out'
    path.write_text('old data\n' * 30)
    follower = LogFollower(path, file_snapshot(path))
    path.write_text('fresh\n')
    assert follower.poll() == 'fresh\n'
    path.write_text('rapid regrowth\n' * 40)
    assert follower.poll() == 'rapid regrowth\n' * 30
    replacement = tmp_path / 'replacement'
    replacement.write_text('replacement\n')
    replacement.replace(path)
    assert follower.poll() == 'replacement\n'
    path.unlink()
    assert follower.poll() == ''
    path.write_text('recreated\n')
    assert follower.poll() == 'recreated\n'


def test_partial_utf8_and_long_line(tmp_path):
    path = tmp_path / 'output.out'
    path.write_bytes(b'')
    follower = LogFollower(path)
    assert follower.poll() == ''
    data = '中文'.encode()
    with path.open('ab') as handle:
        handle.write(data[:2])
    assert follower.poll() == ''
    with path.open('ab') as handle:
        handle.write(data[2:] + b'\n')
    assert follower.poll() == '中文\n'


def test_old_file_rewritten_before_first_poll(tmp_path):
    path = tmp_path / 'output.out'
    path.write_text('old data\n')
    follower = LogFollower(path, file_snapshot(path))
    path.write_text('new data with greater length\n')
    assert follower.poll() == 'new data with greater length\n'
