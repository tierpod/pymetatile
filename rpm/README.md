build rpm package
=================

* Use your own build server: download spec file to SPECS directory and run "build_python2-pyosmkit.sh"

* Use local docker container:

  ```bash
  make image
  ./build_python2-pyosmkit.sh
  # all RPMS will be located in current directory
  ```