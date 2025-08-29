# mock_rdma.py

"""Mock RDMA module for testing without actual RDMA hardware or libraries."""

class MockMemoryRegion:
    def read(self, offset, length):
        # Return mock data that matches your expected format
        import struct
        # Mock values: 100 requests, 150ms total latency, 100 count
        return struct.pack('Qdd', 100, 0.15, 100)

def connect_mr(host_addr, rkey):
    return MockMemoryRegion()
