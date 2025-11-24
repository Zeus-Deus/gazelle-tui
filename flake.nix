{
  description = "Nix flake for gazelle-tui - Minimal NetworkManager TUI with complete 802.1X enterprise WiFi support";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    let
      homeModules = {
        gazelle = import ./home-manager/gazelle.nix;
      };
    in flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python3;
        pythonPackages = pkgs.python3Packages;
      in {
        packages.default = pythonPackages.buildPythonApplication rec {
          pname = "gazelle-tui";
          version = "1.8.1";
          src = ./.;
          format = "other";

          propagatedBuildInputs = with pythonPackages; [
            textual
            rich
            platformdirs
            dbus-python
          ];

          nativeBuildInputs = [ pkgs.makeWrapper ];

          # since upstream isn't using setuptools or poetry, install manually
          installPhase = ''
            runHook preInstall

            mkdir -p $out/share/${pname}
            cp -r . $out/share/${pname}/
            chmod +x $out/share/${pname}/gazelle
            
            mkdir -p $out/bin
            
            cp -s $out/share/${pname}/gazelle $out/bin/gazelle

            wrapProgram $out/bin/gazelle \
              --prefix PYTHONPATH ":" "${pythonPackages.makePythonPath propagatedBuildInputs}:$out/share/${pname}" \
              --prefix PATH ":" "${pkgs.python3}/bin"
            
            runHook postInstall
          '';

          meta = with pkgs.lib; {
            mainProgram = "gazelle";
            description = "Minimal NetworkManager TUI with complete 802.1X enterprise WiFi support";
            changelog = "https://github.com/Zeus-Deus/gazelle-tui/blob/v${version}/CHANGELOG.md";
            license = licenses.mit;
            homepage = "https://github.com/Zeus-Deus/gazelle-tui";
            platforms = platforms.linux;
          };
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            pkgs.python3
            pkgs.dbus
            pythonPackages.rich
            pythonPackages.textual
            pythonPackages.platformdirs
            pythonPackages.dbus-python
          ];
        
          shellHook = ''
            echo "Python dev environment ready"
            echo "try:  python3 gazelle  (run the app)"
          '';
        };

      }) // {
        homeModules = homeModules;
      };
}
