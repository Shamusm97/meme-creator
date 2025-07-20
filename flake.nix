{
    description = "Python Template Development Environment";

    inputs = {
        nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
        flake-utils.url = "github:numtide/flake-utils";
    };

    outputs = { self, nixpkgs, flake-utils }:
        flake-utils.lib.eachDefaultSystem (system:
            let
                pkgs = nixpkgs.legacyPackages.${system};

                pythonPackages = ps: with ps; [
                    ffmpeg-python
                    moviepy
                    google-genai
                ];

                python = pkgs.python3.withPackages pythonPackages;

            in
                {
                devShells.default = pkgs.mkShell {
                    buildInputs = with pkgs; [
                        python
                    ];

                    shellHook = ''
            echo "🐍 Python Template Development Environment"
            '';
                };
            });
}
