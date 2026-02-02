# To learn more about how to use Nix to configure your environment
# see: https://developers.google.com/idx/guides/customize-idx-env
{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-23.11"; # Uses stable Python
  # Use https://search.nixos.org/packages to find packages
  packages = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.virtualenv
  ];
  # Sets environment variables in the workspace
  env = {};
  idx = {
    # Search for the extensions you want on https://open-vsx.org/ and use "publisher.id"
    extensions = [
      "google.gemini-cli-vscode-ide-companion"
      "ms-python.python"
    ];
    # Enable previews
    previews = {
      enable = true;
      previews = {
         web = {
          # COMMAND UPDATED: 
          # 1. Creates venv
          # 2. Installs requirements from SMFC_Manager folder
          # 3. Runs app from SMFC_Manager folder
          command = [
            "sh" "-c" 
            "python3 -m venv venv && source venv/bin/activate && pip install -r SMFC_Manager/requirements.txt && streamlit run SMFC_Manager/app.py --server.port $PORT --server.address 0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false"
          ];
          manager = "web";
        };
      };
    };
  };
}