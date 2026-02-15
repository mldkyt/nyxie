{
  description = "Obsidian Discord bot";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    let 
      mkObsidian = pkgs: 
        let 
          pythonEnv = pkgs.python310.withPackages (ps: with ps; [ #smh cat noises
            pytz
            requests
            yt-dlp
            "py-cord"
            python-dateutil
            deepl
            python-dotenv
            alembic
            sqlalchemy
          ]);
        in
          pkgs.stdenvNoCC.mkDerivation {
            pname = "obsidian";
            version = self.shortRev or "dirty";
            src = self;
            
            dontBuild = true;


            installPhase = ''
              mkdir -p $out/app
              cp -r . $out/app
              mkdir -p $out/bin
              cat > $out/bin/obsidian <<EOF
#!${pkgs.runtimeShell}
exec ${pythonEnv}/bin/python $out/app/main.py
EOF
              chmod +x $out/bin/obsidian
            '';
          };
    in
      flake-utils.lib.eachDefaultSystem (system:
        let
          pkgs = import nixpkgs { inherit system; };
          package = mkObsidian pkgs;
        in
          {
            packages.default = package;

            devShells.default = pkgs.mkShell {
              packages = [
                package.pythonEnv
              ];
            };
          })
      //
      {
        nixosModules.default = { config, lib, pkgs, ... }:
        let
          cfg = config.services.obsidian;
          package = mkObsidian pkgs;
        in
        {
          options.services.obsidian = {
            enable = lib.mkEnableOption "Obsidian Discord bot";

            env = lib.mkOption {
              type = lib.types.nullOr lib.types.path;
              default = null;
              description = "env";
            };

            user = lib.mkOption {
              type = lib.types.str;
              default = "obsidian";
            };

            dataDir = lib.mkOption {
              type = lib.types.path;
              default = "/var/lib/obsidian";
            };
          };

          config = lib.mkIf cfg.enable {

            users.users.${cfg.user} = {
              isSystemUser = true;
              group = cfg.user;
              home = cfg.dataDir;
              createHome = true;
            };

            users.groups.${cfg.user} = {};

            systemd.services.obsidian = {
              description = "Obsidian Discord Bot";
              wantedBy = [ "multi-user.target" ];
              after = [ "network.target" ];

              serviceConfig = {
                Type = "simple";
                User = cfg.user;
                WorkingDirectory = cfg.dataDir;

                ExecStart = "${package}/bin/obsidian";

                Restart = "always";
                RestartSec = 5;

                EnvironmentFile =
                  lib.mkIf (cfg.env != null)
                    cfg.env;

                StateDirectory = "obsidian";
              };
            };
          };
        };
      };
}
