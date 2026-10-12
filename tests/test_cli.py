import pytest

from wef import cli


def test_help_lists_all_stages(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    for stage in [*cli.STAGES, "all"]:
        assert stage in out


def test_unimplemented_stage_exits_with_phase(monkeypatch):
    monkeypatch.setitem(cli.STAGES, "download", ("wef.does_not_exist", 1))
    with pytest.raises(SystemExit, match="Phase 1"):
        cli.main(["download"])
