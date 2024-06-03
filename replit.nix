{ pkgs }: {
  deps = [
    pkgs.libcxx
    pkgs.zeromq
    pkgs.xcodebuild
    pkgs.chromedriver
    pkgs.ncurses
    pkgs.c-ares
    pkgs.geckodriver
    pkgs.libffi
    pkgs.openssl
    pkgs.zlib
    pkgs.openjpeg
    pkgs.libwebp
    pkgs.libtiff
    pkgs.libjpeg
    pkgs.libimagequant
    pkgs.lcms2
    pkgs.glibcLocales
    pkgs.cacert
    pkgs.coreutils
    pkgs.gdb
    pkgs.pgadmin4
    pkgs.arrow-cpp
    pkgs.rustc
    pkgs.cargo
    pkgs.tk
    pkgs.tcl
    pkgs.qhull
    pkgs.gtk3
    pkgs.gobject-introspection
    pkgs.ghostscript
    pkgs.freetype
    pkgs.ffmpeg-full
    pkgs.cairo
    pkgs.playwright-driver
    pkgs.gitFull
    pkgs.postgresql
    pkgs.libiconv
    pkgs.xsimd
    pkgs.pkg-config
    pkgs.libxcrypt
    pkgs.python310Full
    pkgs.python310Packages.virtualenv
  ];

  # For setting up the Python environment
  run = [
    "cd scraper"
    "python -m venv env"
    "source env/bin/activate"
    "pip install -r requirements.txt"
    "python3 save_db.py"
  ];

  # For deployment
  deployment = [
    "python -m venv env"
    "source env/bin/activate"
    "pip install -r requirements.txt"
    "cd scraper"
    "python3 save_db.py"
  ];
}
