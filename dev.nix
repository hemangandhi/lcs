# Nix packages version of "the set of things you need in your system to code
# this"

with import <nixpkgs> {};

stdenv.mkDerivation {
  name = "lcsh-dev-env";
  buildInputs = [
    # Python
    python36
    gcc
    libffi
    # Mongo
    mongodb
  ];
}
