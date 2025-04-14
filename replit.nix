{pkgs}: {
  deps = [
    pkgs.libxcrypt
    pkgs.postgresql
    pkgs.openssl
  ];
}
