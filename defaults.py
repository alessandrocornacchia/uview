"""
MicroView system-wide default configuration values.

All defaults can be overridden via environment variables at runtime.
Provides centralized configuration management for memory layout,
RDMA settings, and MicroView parameters, needed by multiple modules.
"""

import logging
import os

def get_env(name, default, convert=lambda x: x):
    """
    Get environment variables with type conversion 
    """
    value = os.environ.get(name)
    if value is not None:
        try:
            return convert(value)
        except (ValueError, TypeError):
            logging.warning(f"Failed to convert environment variable {name}={value} to required type, using default: {default}")
    return default


# ---- memory layout ----
DEFAULT_PAGE_SIZE = get_env("DEFAULT_PAGE_SIZE", 4096, int)
DEFAULT_RDMA_MR_SIZE = get_env("DEFAULT_RDMA_MR_SIZE", 1 * DEFAULT_PAGE_SIZE, int)  # 64KB maximum size for RDMA read groups
SHM_POOL_SIZE = get_env("SHM_POOL_SIZE", 10 * DEFAULT_RDMA_MR_SIZE, int)   # 10 MR
SHM_POOL_NAME = "microview"
IPU_HOSTNAME_PREFIX = get_env("IPU_HOSTNAME_PREFIX", "mcbf", str)

# ---- RDMA settings ----
DEFAULT_RDMA_DEVICE = "mlx5_1"
DEFAULT_QP_POOL_SIZE = 1
DEFAULT_GID = 3
DEFAULT_IB_PORT = 1

# ---- Microview default settings ----
DEFAULT_POLL_INTERVAL = 1  # seconds
DEFAULT_LMAP = 1


# Configure default logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

default_logger = logging.getLogger('default')