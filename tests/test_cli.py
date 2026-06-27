from __future__ import annotations
from click.testing import CliRunner
from displayctl import __version__
from displayctl.cli import cli


def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_status_no_backend():
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0


def test_list_no_backend():
    runner = CliRunner()
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0


def test_profiles_no_file():
    runner = CliRunner()
    result = runner.invoke(cli, ["profiles"])
    assert result.exit_code == 0


def test_mirror_dry_run():
    runner = CliRunner()
    result = runner.invoke(cli, ["--dry-run", "mirror"])
    assert result.exit_code == 0


def test_extend_dry_run():
    runner = CliRunner()
    result = runner.invoke(cli, ["--dry-run", "extend"])
    assert result.exit_code == 0


def test_pc_dry_run():
    runner = CliRunner()
    result = runner.invoke(cli, ["--dry-run", "pc"])
    assert result.exit_code == 0


def test_second_dry_run():
    runner = CliRunner()
    result = runner.invoke(cli, ["--dry-run", "second"])
    assert result.exit_code == 0


def test_save_no_profile():
    runner = CliRunner()
    result = runner.invoke(cli, ["save"])
    assert result.exit_code != 0


def test_save_with_profile():
    runner = CliRunner()
    result = runner.invoke(cli, ["--dry-run", "save", "--profile", "test"])
    assert result.exit_code == 0


def test_load_with_profile():
    runner = CliRunner()
    result = runner.invoke(cli, ["--dry-run", "load", "--profile", "test"])
    assert result.exit_code == 0
