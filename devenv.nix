{
  pkgs,
  lib,
  config,
  ...
}:
{
  # https://devenv.sh/packages/
  packages = [
    pkgs.python3
    pkgs.zed-editor
  ];

  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    version = "3.10";
    uv = {
      enable = true;
      sync.enable = true;
    };
  };

  enterShell = ''
    # Create a symlink to the Python virtual environment for IDE compatibility
    if [ ! -L "$DEVENV_ROOT/.venv" ]; then
        ln -s "$DEVENV_STATE/venv/" "$DEVENV_ROOT/.venv"
    fi
  '';

  # https://devenv.sh/processes/
  processes.watch-run.exec = "${lib.getExe pkgs.watchexec} --filter \"*.py\" --restart -- uv run main.py";

  # See full reference at https://devenv.sh/reference/options/
}
