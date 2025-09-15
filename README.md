# MicroView: NSDI'26 Artifacts Evaluation

## Overview

MicroView is a cloud-native observability system that uses SmartNIC-to-host communication via RDMA for microservices metrics collection. 

This repository contains instructions to access our artifats and reproduce the experimental results of the NSDI paper **Sketching a Solution to Observability Bloat: In-Situ Metrics  Analytics on IPUs**, Alessandro Cornacchia, Theophilus A. Benson, Muhammad Bilal, Marco Canini

### Contents

- [Getting Started](#-getting-started) kick the tires instructions to verify the setup is working correctly and basic functionalities of MicroView
- [Detailed Instructions](#-detailed-instructions) in-depth step-by-step instruction to reproduce paper's claims


## 🔧 Access

**Required Hardware**: Nvidia BlueField2 IPU.

> [!IMPORTANT]
> **Access**: Reviewers will be provided VPN access to our testbed infrastructure. Please reach out the  [authors](#-support) to request access. We will ensure reviewer anonymity is preserved throughout this process.

## ⚙️ Environment

Make sure to [obtain access](#-access) before proceeding with below. 

**Default Setup**: Reviewers will be provided with a local username on both host and SmartNIC machines. The environment includes:
- NVIDIA BLueField2 IPU with RDMA tools and drivers configured
- Network connectivity pre-configured as shown in architecture diagram below
- Pre-installed Python environment with conda and dependencies from `requirements.txt` installed
- Kubernetes cluster with microservices applications and Blueprint compiler

Shoud any issue occur with the configuration or should the reviewers reproduce manual install, please refer to [Troubleshooting](#-troubleshooting) guide

### System architecture

The testbed consists of a host machine connected to a BlueField2 SmartNIC via RDMA:

```
┌─────────────────┐    RDMA     ┌─────────────────┐
│   Host Machine  │◄──────────► │ BlueField2 IPU  │
│  192.168.100.1  │             │ 192.168.100.2   │
│                 │             │ 10.200.0.52     │
│ microview-host  │             │ microview-nic   │
│ libmicroview    │             │ (collectors)    │
└─────────────────┘             └─────────────────┘
      ens1f1                         enp3s0f1s0
```

**Pre-configured Network Interfaces**:
- Host: `192.168.100.1` on `ens1f1`  
- SmartNIC:
    * `192.168.100.2` on `tmfifo_net0` (management port)
    * `10.200.0.52` on `enp3s0f1s0` 


## 🚀 Getting Started

This section demonstrates a basic MicroView kick-off before running full benchmarks. The goal is to:
1. start the MicroView control plane components both on the host and on the IPU
2. and verify they can exchange control plane information and connect the RDMA QPs
3. start a process on the host that generates metrics from user-space and verify MicroView IPU component can read such metrics

Activate a conda environment:
```bash
conda activate uview
cd uview
```

### Step 1: Start MicroView Host Agent

On the **host machine**:
```bash
python microview-host.py --rdma-queues 1
```

Expected output: Host agent starts and listens for RDMA connections.
```
[INFO] 31 Jul 2025 18:50:03 microview-host.py:56: Each page can hold 64 metrics of size 64 bytes
[INFO] 31 Jul 2025 18:50:03 microview-host.py:60: Shared memory pool can hold 10 pages
[INFO] 31 Jul 2025 18:50:03 microview-host.py:65: Created shared memory with name microview and size 40960 bytes
[INFO] 31 Jul 2025 18:50:03 helpers.py:223: Opened RDMA device: mlx5_1
[INFO] 31 Jul 2025 18:50:03 helpers.py:286: Created Queue Pair #0: GID=0000:0000:0000:0000:0000:ffff:0ac8:001c, qp_num=550
[INFO] 31 Jul 2025 18:50:03 helpers.py:292: Created Queue Pair pool with 1 QPs
[INFO] 31 Jul 2025 18:50:03 microview-host.py:436: Created QP pool with size 1
[INFO] 31 Jul 2025 18:50:03 helpers.py:88: Registered memory region 'RDMA-MR-0': addr=0x7f3e2f3a4000, rkey=2342331, size=4096
[INFO] 31 Jul 2025 18:50:03 helpers.py:88: Registered memory region 'RDMA-MR-1': addr=0x7f3e2f3a5000, rkey=2342074, size=4096
[INFO] 31 Jul 2025 18:50:03 helpers.py:88: Registered memory region 'RDMA-MR-2': addr=0x7f3e2f3a6000, rkey=2341817, size=4096
[INFO] 31 Jul 2025 18:50:03 helpers.py:88: Registered memory region 'RDMA-MR-3': addr=0x7f3e2f3a7000, rkey=2341303, size=4096
[INFO] 31 Jul 2025 18:50:03 helpers.py:88: Registered memory region 'RDMA-MR-4': addr=0x7f3e2f3a8000, rkey=2340789, size=4096
[INFO] 31 Jul 2025 18:50:03 helpers.py:88: Registered memory region 'RDMA-MR-5': addr=0x7f3e2f3a9000, rkey=2340275, size=4096
[INFO] 31 Jul 2025 18:50:03 helpers.py:88: Registered memory region 'RDMA-MR-6': addr=0x7f3e2f3aa000, rkey=2339761, size=4096
[INFO] 31 Jul 2025 18:50:03 helpers.py:88: Registered memory region 'RDMA-MR-7': addr=0x7f3e2f3ab000, rkey=2339247, size=4096
[INFO] 31 Jul 2025 18:50:03 helpers.py:88: Registered memory region 'RDMA-MR-8': addr=0x7f3e2f3ac000, rkey=2338733, size=4096
[INFO] 31 Jul 2025 18:50:03 helpers.py:88: Registered memory region 'RDMA-MR-9': addr=0x7f3e2f3ad000, rkey=2338219, size=4096
[INFO] 31 Jul 2025 18:50:03 microview-host.py:441: ✅ RDMA initialized correctly
[INFO] 31 Jul 2025 18:50:03 microview-host.py:471: Starting REST API on 0.0.0.0:5000
 * Tip: There are .env files present. Install python-dotenv to use them.
 * Serving Flask app 'microview-host'
 * Debug mode: off
[INFO] 31 Jul 2025 18:50:03 _internal.py:97: WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://172.18.0.39:5000
[INFO] 31 Jul 2025 18:50:03 _internal.py:97: Press CTRL+C to quit
```

### Step 2: Create Test Metrics Generators

In a **new terminal on the host**:
```bash
python libmicroview.py --debug --num-metrics 16 --update-metrics
```

This simulates a microservice that registers metrics and continuously updates them via shared memory.

### 🔌 Step 2: Start MicroView on IPU

On the **SmartNIC** (BlueField2):
```bash
conda activate uview
python microview-nic.py \
    --control-plane 172.18.0.39:5000 \
    --dev mlx5_3 \
    --gid 1 \
    --ib-port 1 \
    --test read_loop \
    --debug
```
This starts the metrics collector and the LMAPs in the IPU SoC cores.

**Expected Results**:
- Host agent shows RDMA connection established
- SmartNIC collector displays metric read rates (scrapes/second)
- Test metrics appear in test application console output (step 2) and SmartNIC console output (step 3)

### Step 4: Verify Prometheus Integration

Test the Prometheus-compatible endpoint:
```bash
# On SmartNIC, restart with Prometheus mode
python microview-nic.py \
    --control-plane 192.168.100.1:5000 \
    --test prometheus \
    --debug

# On host, test the endpoint  
curl http://192.168.100.2:8000/metrics
```

If all steps complete successfully, MicroView is working correctly and ready for benchmark evaluation.

## 📈 Detailed Instructions

We provide separate instructions to evaluate the artifacts and reproduce the paper's experimental results. 

- **[📊 Motivation (Sec.2) →](cadvisor-scalability/README.md)** measuring generation and ingestion costs of cAdvisor + Prometheus
- **[📊 IPU Micro-Benchmarks Guide (Sec.6.1) →](docs/run-benchmark.md)** guide to benchmarks of MicroView's performance on IPU
- **[📊 Distributed Tracing for Microservices Apps (Sec.6.3) →](usecases/README.md)** deploy microservice applications, inject failures and generate observability data
- **[📊 Adaptive Metrics Sampling for Microservices Apps (Sec.6.4) →](adaptive-sampling/README.md)** deploy microservice applications, inject failures and generate observability data
- **[📊 Horizontal Autoscaling Microbenchmark (Sec.6.5) →](horizontal-autoscaling/README.md)** deploying and rescaling a microservice on Kubernetes to test MicroView under dynamic conditions

Please refer to the two sections individually for further instructions about the maturity of this repo relative to the content of the paper.

## 🔧 Troubleshooting

### 🛠️ Manual Install (Fallback)

Install system dependencies:
```bash
# System packages
sudo apt-get update
sudo apt-get install -y python3 python3-pip wrk git ibverbs-utils rdma-core libibverbs-dev
```

Make sure `conda` or `mamba` is installed:
```bash
# Python environment
wget "https://repo.anaconda.com/miniconda/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh
```

Clone repo and setup environment:
```bash
git clone 
cd ./uview
mamba env create -f mamba-env.yml
mamba activate uview
```

#### Install `pyverbs` 

We encountered issues when installing `pyverbs` via `pip`.

The Python wheels compile, however, out of all symbols that should be defined within the module `pyverbs.enums` only a few can be actually found when running a python script (See `tests/hello_pyverbs/pyverbs-symbols.py`)

As a workaround, we solved by creating a symlink to the system installation. 
To install `pyverbs` manually, run:

```bash
./pyverbs-install.sh
```

### 🚨 Connection Issues

#### Connectivity check

Please verify connectivity with: `ping 192.168.100.2` (from host) and `ping 192.168.100.1` (from SmartNIC).

**Verify RDMA Setup**:
```bash
# Check RDMA devices
ibstat
show_gids | grep enp3s0f1s0  # On SmartNIC
```

- **Check RDMA one-sided operations**. Verify RDMA one-sided operations are healthy via `ib` utilities.  Start RDMA server on IPU with `ib_write_bw -d mlx5_3 -i 1` and try to connect from host-side with `ib_write_bw -d mlx5_1 -i 1 10.200.0.52`
- **Port Already in Use**: If you get these errors, kill pre-existing microview processes: e.g., `pkill -f microview-nic.py`

### 🐛 Debug Mode
For detailed troubleshooting, run all components with `--debug`:
```bash
python microview-host.py --debug
python microview-nic.py --debug  
python libmicroview.py --debug
```

## 💬 Support

For technical issues during evaluation contact [alessandro.cornacchia@kaust.edu.sa](mailto:alessandro.cornacchia@kaust.edu.sa)
