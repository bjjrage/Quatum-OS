from scripts.os_launcher import parse_listen_pids


def test_parse_netstat_only_returns_listening_pid_for_requested_port():
    sample = """\
  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:3000            0.0.0.0:0              LISTENING       1234
  TCP    [::]:8000               [::]:0                 LISTENING       4321
  TCP    127.0.0.1:3000          127.0.0.1:50000        ESTABLISHED     8888
  TCP    0.0.0.0:13000           0.0.0.0:0              LISTENING       9999
"""
    assert parse_listen_pids(sample, 3000) == {1234}
    assert parse_listen_pids(sample, 8000) == {4321}
    assert parse_listen_pids(sample, 5000) == set()
