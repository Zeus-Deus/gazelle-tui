{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.programs.gazelle;
in
{
  options.programs.gazelle = {
    enable = mkOption {
      type = types.bool;
      default = false;
      description = "Enable gazelle configuration";
    };

    settings = mkOption {
      type = types.attrsOf types.str;
      default = { theme = "auto"; };
      description = "Gazelle settings (will be written to ~/.config/gazelle/config.json)";
    };
  };

  config = mkIf cfg.enable {
    home.file.".config/gazelle/config.json".text = builtins.toJSON cfg.settings;
  };
}
