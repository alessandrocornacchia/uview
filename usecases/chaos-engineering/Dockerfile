# Use the official Debian image as the base
FROM gcr.io/distroless/cc-debian12

# Copy artifacts for processes with custom build commands
COPY --from=firm-build /anomaly /anomaly

# Get a shell
COPY --from=busybox:1.35.0-uclibc /bin/sh /bin/sh

# # Update package lists and install development tools
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

# uView : we use cc-debian12 and not base-debian12 to have stdlib for FIRM C++ code
# uView : PATH and dynamic libraries paths
ENV LD_LIBRARY_PATH="/anomaly/lib"
ENV PATH="/anomaly/bin:${PATH}"

# run bin/sh when running the container
CMD ["/bin/sh"]
