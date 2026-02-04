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
          # COMMAND UPDATED: Points to Super_App/Home.py
          command = [
            "/bin/bash"
            "-c"
            # 1. Create/Activate venv  2. Install Req  3. Run Home.py
            "python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && streamlit run Super_App/Home.py --server.port $PORT --server.address 0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false"
          ];
          manager = "web";
        };
      };
    };
  };
}