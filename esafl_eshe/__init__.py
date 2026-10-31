"""
esafl_eshe: Multi-Key Homomorphic Encryption Backend for ECPFL

This package provides a Python-accessible multi-key CKKS backend by wrapping
the xMK-CKKS library from the MASER framework. It exposes a high-level API
suitable for ECPFL's pack-level encryption, aggregation, and decryption.

Note on terminology:
- The cryptographic primitive is multi-key CKKS (Chen-Kim-Kim-Song style),
  implemented in Go inside MASER's xmkckks.dll and exposed through Python.
- Decryption follows the distributed partial-decryption model: each client
  contributes a partial decryption share, and the server aggregates the shares
  to recover the plaintext. This differs from ESAFL's one-step decryption model,
  in which each client decrypts locally using the summed global key.
- The package name "esafl_eshe" reflects the design lineage (ESAFL-style
  multi-key AHE for FL), not an exact re-implementation of ESAFL's C++ ESHE.
"""

from .core import ESHEManager, _XMKCKKS_AVAILABLE as ESAFL_ESHE_AVAILABLE
from .utils import pad_to_length, chunks_to_array

__all__ = ["ESHEManager", "ESAFL_ESHE_AVAILABLE", "pad_to_length", "chunks_to_array"]
