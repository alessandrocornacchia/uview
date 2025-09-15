#!/bin/bash

CONDA_SITE_PACKAGES=$(mamba run -n uview python -c "import site; print(site.getsitepackages()[0])")

echo "Conda site-packages directory: $CONDA_SITE_PACKAGES"

if [ ! -d "$CONDA_SITE_PACKAGES" ]; then
    echo "Conda site-packages directory does not exist. Please check your conda environment."
    exit 1
fi

# Define the system pyverbs path
SYSTEM_PYVERBS="/usr/lib/python3/dist-packages/pyverbs"

# check if pyverbs is installed in the system, if not exit
if [ ! -d "$SYSTEM_PYVERBS" ]; then
    echo "pyverbs is not installed at selected location. Please install it first."
    exit 1
fi

# create a symlink to the system pyverbs in the conda environment
ln -sf $SYSTEM_PYVERBS $CONDA_SITE_PACKAGES/pyverbs
echo "Symlink created from $SYSTEM_PYVERBS to $CONDA_SITE_PACKAGES/pyverbs"

echo "✅ pyverbs installation completed."
