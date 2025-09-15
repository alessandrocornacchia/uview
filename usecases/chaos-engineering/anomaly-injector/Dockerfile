# Use the official GCC image from Docker Hub
FROM gcc:latest

COPY [ "./", "/anomaly" ]
WORKDIR /anomaly


# make optional FIRM injectors such as sysbench
RUN apt-get update && apt-get -y install \
    make \
    automake \
    libtool \
    pkg-config \
    libaio-dev \
    default-libmysqlclient-dev \
    libssl-dev \
    libpq-dev \
    iproute2\
    stress-ng\
    sleep

# make FIRM injectors
RUN make

RUN cd pmbw-0.6.2 && \
    ./configure && \
    make

RUN cd ./sysbench \
    && ./autogen.sh \
    && ./configure \
    && make -j \
    && make install


# Copy the stress-ng binary and its dependencies to the anomaly folder which will be copied
# to the final image of Blueprint containers
RUN mkdir -p bin lib

# Copy the stress-ng binary and libraries
RUN cp /usr/bin/stress-ng ./bin
RUN ldd /usr/bin/stress-ng | grep -o '/[^ ]*' | xargs -I '{}' cp -uv '{}' ./lib/

# Copy the sysbench binary and libraries
RUN cp /usr/local/bin/sysbench ./bin
RUN ldd /usr/local/bin/sysbench | grep -o '/[^ ]*' | xargs -I '{}' cp -uv '{}' ./lib/
