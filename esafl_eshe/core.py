"""
Core multi-key homomorphic encryption manager for ECPFL.

This module wraps the xMK-CKKS library from MASER and exposes:
  - multi-key key generation and public-key aggregation
  - per-client encryption under a joint public key
  - homomorphic aggregation of ciphertexts from different clients
  - distributed decryption via partial decryption shares

The underlying xMK-CKKS library is a Go-implemented multi-key CKKS scheme
exposed to Python through ctypes. It uses RLWE-based encryption and supports
SIMD packing.
"""

import sys
import os
import warnings
from typing import List, Any, Optional
import numpy as np

# Locate MASER's xMK-CKKS wrapper
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MASER_DIR = os.path.join(_PROJECT_ROOT, "MASER-main")

_XMKCKKS_AVAILABLE = False
_xmkckks_wrapper = None

if os.path.isdir(_MASER_DIR):
    sys.path.insert(0, _MASER_DIR)
    try:
        import xmkckks_wrapper as _xmkckks_wrapper
        _XMKCKKS_AVAILABLE = True
    except Exception as _e:  # pragma: no cover
        warnings.warn(f"Failed to load xMK-CKKS wrapper from {_MASER_DIR}: {_e}")
else:
    warnings.warn(f"MASER-main directory not found at {_MASER_DIR}")


class ESHEManager:
    """
    Manager for multi-key CKKS operations used by ECPFL.

    The manager creates a server instance and one client instance per participant.
    Each client holds its own secret key; the server aggregates client public keys
    into a joint public key that enables multi-key homomorphic addition.
    """

    def __init__(self, num_clients: int, slot_size: int = 4096, client_ids: Optional[List[int]] = None):
        """
        Initialize the multi-key HE manager.

        Args:
            num_clients: Number of clients (must be >= 2 for multi-key).
            slot_size: Length of the plaintext vector per ciphertext. Must not exceed
                the number of CKKS slots configured in xMK-CKKS (default 4096).
            client_ids: Optional external client IDs. If provided, maps each ID to
                the internal 0-based client index used by the wrapper.
        """
        if not _XMKCKKS_AVAILABLE:
            raise RuntimeError(
                "xMK-CKKS backend is not available. "
                "Please ensure MASER-main/xmkckks_go2py/xmkckks.dll exists."
            )
        if num_clients < 2:
            raise ValueError("Multi-key HE requires at least 2 clients.")
        if slot_size <= 0:
            raise ValueError("slot_size must be positive.")

        self.num_clients = num_clients
        self.slot_size = slot_size
        self.wrapper = _xmkckks_wrapper

        # Server instance with id=0; clients with ids 1..N
        self.server = self.wrapper.MPHEServer(server_id=0)
        self.clients = [self.wrapper.MPHEServer(server_id=i + 1) for i in range(num_clients)]

        # External client_id -> internal client_idx mapping.
        # By default we treat the identifier as the internal 0-based index, so
        # callers can simply pass 0..N-1. Custom client IDs can be supplied when
        # integrating with an experiment runner that uses its own identifiers.
        if client_ids is not None:
            if len(client_ids) != num_clients:
                raise ValueError("len(client_ids) must equal num_clients")
            self.client_id_to_idx = {cid: idx for idx, cid in enumerate(client_ids)}
        else:
            self.client_id_to_idx = {i: i for i in range(num_clients)}

        self._ready = False

    def setup(self) -> Any:
        """
        Aggregate all client public keys and distribute the joint public key.

        Returns:
            The aggregated joint public-key polynomial.
        """
        if self.num_clients < 2:
            raise RuntimeError("Need at least two clients to aggregate public keys.")

        ring_p_list = [client.pk[0].P for client in self.clients]
        aggregated_p = self.server.aggregate_ringPs(ring_p_list)

        for client in self.clients:
            client.pk[0].P = aggregated_p

        self._ready = True
        return aggregated_p

    def _resolve_client_idx(self, client_id_or_idx: int) -> int:
        """Resolve an external client_id or internal client_idx to internal index."""
        if client_id_or_idx in self.client_id_to_idx:
            return self.client_id_to_idx[client_id_or_idx]
        if 0 <= client_id_or_idx < self.num_clients:
            return client_id_or_idx
        raise ValueError(
            f"Invalid client identifier {client_id_or_idx}. "
            f"Expected one of {list(self.client_id_to_idx.keys())} or an internal index in [0, {self.num_clients - 1}]."
        )

    def encrypt(self, client_id_or_idx: int, values: List[float]) -> Any:
        """
        Encrypt a plaintext vector for a specific client under the joint public key.

        Args:
            client_id_or_idx: External client ID or internal client index.
            values: Plaintext vector of floats. Shorter vectors are zero-padded
                to slot_size; longer vectors raise ValueError.

        Returns:
            An xMK-CKKS Ciphertext object.
        """
        if not self._ready:
            raise RuntimeError("Call setup() before encryption.")

        client_idx = self._resolve_client_idx(client_id_or_idx)
        if len(values) < self.slot_size:
            values = list(values) + [0.0] * (self.slot_size - len(values))
        elif len(values) > self.slot_size:
            raise ValueError(
                f"Input length {len(values)} exceeds slot_size {self.slot_size}."
            )

        return self.clients[client_idx].encryptFromPk(values)

    def aggregate(self, ciphertexts: List[Any]) -> Any:
        """
        Homomorphically aggregate a list of ciphertexts.

        All ciphertexts must be encrypted under the same joint public key.
        The result is a multi-key ciphertext decryptable only when all
        participating clients contribute their partial decryption shares.

        Args:
            ciphertexts: List of xMK-CKKS Ciphertext objects.

        Returns:
            Aggregated xMK-CKKS Ciphertext object.
        """
        if not ciphertexts:
            raise ValueError("ciphertexts list is empty")

        result = ciphertexts[0]
        for ct in ciphertexts[1:]:
            result = self.server.addCTs(result, ct)
        return result

    def partial_decrypt(self, client_id_or_idx: int, aggregated_ct: Any) -> Any:
        """
        Generate a partial decryption share from a specific client.

        Args:
            client_id_or_idx: External client ID or internal client index.
            aggregated_ct: An aggregated multi-key ciphertext.

        Returns:
            Partial decryption share (Ciphertext object).
        """
        client_idx = self._resolve_client_idx(client_id_or_idx)
        return self.clients[client_idx].partialDecrypt(aggregated_ct)

    def decode(
        self,
        partial_shares: List[Any],
        client_id_or_idx_list: Optional[List[int]] = None,
    ) -> np.ndarray:
        """
        Aggregate partial decryption shares and decode to plaintext.

        Args:
            partial_shares: List of partial decryption shares, one per participating
                client, in the same order as client_id_or_idx_list.
            client_id_or_idx_list: List of client identifiers corresponding to the
                partial shares. If None, assumes all clients 0..N-1 participated.

        Returns:
            Decoded plaintext as a numpy array of floats (length == slot_size).
        """
        if not partial_shares:
            raise ValueError("partial_shares list is empty")

        if client_id_or_idx_list is None:
            if len(partial_shares) != self.num_clients:
                raise ValueError(
                    "When client_id_or_idx_list is None, partial_shares must contain "
                    "exactly num_clients shares."
                )
            client_id_or_idx_list = list(range(self.num_clients))

        if len(partial_shares) != len(client_id_or_idx_list):
            raise ValueError("partial_shares and client_id_or_idx_list must have the same length")

        server_ids = [
            self.clients[self._resolve_client_idx(cid)].idx
            for cid in client_id_or_idx_list
        ]

        aggregated_pd = self.server.aggregate_pds(partial_shares, server_ids)
        decoded = self.server.decodeAfterPartialDecrypt(aggregated_pd)
        # xMK-CKKS decodes to 2*slot_size floats (the full polynomial); the
        # user plaintext occupies the first slot_size entries.
        return np.array(decoded[: self.slot_size], dtype=np.float64)

    def encrypt_and_aggregate(
        self,
        plaintext_list: List[List[float]],
        client_id_or_idx_list: Optional[List[int]] = None,
    ) -> Any:
        """
        Convenience method: encrypt multiple plaintexts and aggregate the ciphertexts.

        Args:
            plaintext_list: List of plaintext vectors, one per participating client.
            client_id_or_idx_list: Client identifiers in the same order. If None,
                uses internal indices 0..len(plaintext_list)-1.

        Returns:
            Aggregated multi-key ciphertext.
        """
        if client_id_or_idx_list is None:
            client_id_or_idx_list = list(range(len(plaintext_list)))
        if len(plaintext_list) != len(client_id_or_idx_list):
            raise ValueError("plaintext_list and client_id_or_idx_list must have the same length")

        cts = [
            self.encrypt(cid, pt)
            for cid, pt in zip(client_id_or_idx_list, plaintext_list)
        ]
        return self.aggregate(cts)

    def full_decrypt(
        self,
        aggregated_ct: Any,
        client_id_or_idx_list: Optional[List[int]] = None,
    ) -> np.ndarray:
        """
        Convenience method: collect partial decryption shares from all participating
        clients and decode the plaintext.

        In a real deployment, each client would generate its share locally and send
        it to the server. This method simulates that process by using the in-memory
        client secret keys.

        Args:
            aggregated_ct: Aggregated multi-key ciphertext.
            client_id_or_idx_list: Participating client identifiers. If None, all
                clients are assumed to participate.

        Returns:
            Decoded plaintext as a numpy array.
        """
        if client_id_or_idx_list is None:
            client_id_or_idx_list = list(range(self.num_clients))

        shares = [
            self.partial_decrypt(cid, aggregated_ct)
            for cid in client_id_or_idx_list
        ]
        return self.decode(shares, client_id_or_idx_list)
