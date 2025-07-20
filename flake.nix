{
    description = "Python Template Development Environment";

    inputs = {
        nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
        flake-utils.url = "github:numtide/flake-utils";
    };

    outputs = { self, nixpkgs, flake-utils }:
        flake-utils.lib.eachDefaultSystem (system:
            let
                pkgs = import nixpkgs {
                  inherit system;
                  config = {
                    allowUnfree = true;
                  };
                };

                pythonPackages = ps: with ps; [
                    ffmpeg-python
                    moviepy
                    google-genai
                    python-dotenv
                ];

                python = pkgs.python3.withPackages pythonPackages;

            in
                {
                devShells.default = pkgs.mkShell {
                    buildInputs = with pkgs; [
                        python
                        claude-code
                    ];

                    shellHook = ''
            export PYTHONDONTWRITEBYTECODE=1
            echo "🐍 Python Template Development Environment"
            '';
                };
            });
}
