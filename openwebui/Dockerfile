FROM ghcr.io/open-webui/open-webui:main

# The upstream image ships NumPy 2.x which is compiled with X86_V2 baseline
# optimizations and will crash at import time on CPUs that only support X86_V1.
# Downgrade to the last NumPy 1.x release which uses the plain x86-64 baseline.
RUN pip install --force-reinstall "numpy==1.26.4"
