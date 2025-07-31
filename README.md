# MicroView: NSDI'26 Artifact Evaluation

## Overview

MicroView is a cloud-native observability system that uses SmartNIC-to-host communication via RDMA for microservices metrics collection. 

This repository contains the artifacts to reproduce the experimental results from our NSDI paper **Sketching a Solution to Observability Bloat: In-Situ Metrics  Analytics on IPUs**, Alessandro Cornacchia, Theophilus A. Benson, Muhammad Bilal, Marco Canini

## 🔧 Access to Hardware

**Required Hardware**: Nvidia BlueField2 IPU (or SmartNIC) with RDMA capabilities

**Access**: Reviewers will be provided VPN access to our testbed infrastructure. Please contact the authors via HotCRP to request access credentials. We will ensure reviewer anonymity is preserved throughout the evaluation process.

### System architecture

The testbed consists of a host machine connected to a BlueField2 SmartNIC via RDMA:

```
┌─────────────────┐    RDMA     ┌─────────────────┐
│   Host Machine  │◄──────────► │ BlueField2 NIC  │
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


#### Connectivity check

Please verify connectivity with: `ping 192.168.100.2` (from host) and `ping 192.168.100.1` (from SmartNIC).

**RDMA**. Verify via `ib` utilities. For example: start RDMA server on IPU with `ib_write_bw -d mlx5_3 -i 1` and try to connect from host-side with `ib_write_bw -d mlx5_1 -i 1 10.200.0.52`


## ⚙️ Environment Setup

**Default Setup**: Reviewers will be provided with a local username on both host and SmartNIC machines. The environment includes:
- Pre-installed Python 3.11 with conda
- All dependencies from `requirements.txt` installed
- RDMA tools and drivers configured
- Network interfaces pre-configured as shown in architecture diagram

Simply activate the environment:
```bash
conda activate uview
cd uview
```

### 🛠️ Manual Installation (Fallback)

If the provided environment has issues, follow these steps:

<details>
<summary>Click to expand manual installation instructions</summary>

**Install Dependencies**:
```bash
# System packages
sudo apt-get update
sudo apt-get install -y python3 python3-pip wrk git ibverbs-utils rdma-core libibverbs-dev

# Python environment
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
conda create --name uview python=3.11
conda activate uview
pip install -r requirements.txt
```

**Verify RDMA Setup**:
```bash
# Check RDMA devices
ibstat
show_gids | grep enp3s0f1s0  # On SmartNIC
```

</details>

## 🚀 Getting Started

This section demonstrates a basic MicroView kick-off before running full benchmarks. The goal is to:
1. start the MicroView control plane components both on the host and on the IPU
2. and verify they can exchange control plane information and connect the RDMA QPs
3. start a process on the host that generates metrics from user-space and verify MicroView IPU component can read such metrics

### Step 1: Start MicroView Host Agent

On the **host machine**:
```bash
conda activate uview
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
conda activate uview
python libmicroview.py --debug --num-metrics 16 --update-metrics
```

This simulates a microservice that registers metrics and continuously updates them via shared memory.

### 🔌 Step 2: Start MicroView on IPU

On the **SmartNIC** (BlueField2):
```bash
conda activate uview
python microview-nic.py \
    --control-plane 172.18.0.39:5000 \
    --device mlx5_3 \
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

- **[📊 IPU Micro-Benchmarks Guide →](ipu-benchmarks.md)** guide to full benchmark of MicroView's performance on IPU
- **[📊 Use-Cases on Kubernetes Microservices Apps →](use-cases.md)** deploy microservice applications, inject failures and generate observability data

Please refer to the two sections individually for further instructions about the maturity of this repo relative to the content of the paper.

## 🔧 Troubleshooting

### 🚨 Connection Issues
- **Port Already in Use**: Kill existing processes: e.g., `pkill -f microview-nic.py`

### 🐛 Debug Mode
For detailed troubleshooting, run all components with `--debug`:
```bash
python microview-host.py --debug
python microview-nic.py --debug  
python libmicroview.py --debug
```

### 🔍 Environment Issues
- Verify conda environment: `conda info --envs`
- Check dependencies: `pip list | grep -E "(numpy|pandas|matplotlib)"`
- Test RDMA: `ibstat` should show active devices

## 💬 Support

For technical issues during evaluation contact [alessandro.cornacchia@kaust.edu.sa](mailto:alessandro.cornacchia@kaust.edu.sa)
