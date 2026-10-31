"""
Shamir Secret Sharing for PAMP
Implements (t, n)-threshold secret sharing over a finite field.

Used for:
1. Splitting the CKKS secret key sk into n shares
2. Splitting per-client self-masks s_i into n shares for recovery
"""

import random
import os
from typing import List, Tuple, Dict, Set


# Large prime for finite field arithmetic
# Must be > max secret value. For 128-bit security, use a 128+ bit prime.
DEFAULT_PRIME = 2 ** 127 - 1  # Mersenne prime


class ShamirSecretSharing:
    """
    (t, n)-Shamir Secret Sharing over Z_p.
    
    Properties:
    - Any t shares can reconstruct the secret
    - Any t-1 shares reveal zero information (information-theoretic security)
    """

    def __init__(self, prime: int = DEFAULT_PRIME):
        self.prime = prime

    def _eval_at(self, poly: List[int], x: int) -> int:
        """Evaluate polynomial at point x (mod prime)."""
        result = 0
        for coef in reversed(poly):
            result = (result * x + coef) % self.prime
        return result

    def split(self, secret: int, n: int, t: int) -> List[Tuple[int, int]]:
        """
        Split secret into n shares with threshold t.
        
        Args:
            secret: The secret to share (must be < prime)
            n: Total number of shares
            t: Threshold (minimum shares needed to reconstruct)
            
        Returns:
            List of (index, share) tuples, indices are 1-based
        """
        if secret >= self.prime:
            raise ValueError(f"Secret must be < prime ({self.prime})")
        if t > n:
            raise ValueError("Threshold t cannot exceed n")
        if t < 2:
            raise ValueError("Threshold t must be >= 2")

        # Generate random polynomial of degree t-1
        # f(x) = secret + a1*x + a2*x^2 + ... + a_{t-1}*x^{t-1}
        poly = [secret]  # a_0 = secret
        for _ in range(t - 1):
            poly.append(random.randint(1, self.prime - 1))

        # Evaluate at points 1, 2, ..., n
        shares = []
        for i in range(1, n + 1):
            share = self._eval_at(poly, i)
            shares.append((i, share))

        return shares

    def reconstruct(self, shares: List[Tuple[int, int]]) -> int:
        """
        Reconstruct secret from shares using Lagrange interpolation.
        
        Args:
            shares: List of (index, share) tuples
            
        Returns:
            The reconstructed secret
        """
        if len(shares) < 2:
            raise ValueError("Need at least 2 shares to reconstruct")

        secret = 0
        indices = [x for x, _ in shares]

        for i, (x_i, y_i) in enumerate(shares):
            # Compute Lagrange basis polynomial l_i(0)
            numerator = 1
            denominator = 1

            for j, (x_j, _) in enumerate(shares):
                if i != j:
                    numerator = (numerator * (-x_j)) % self.prime
                    denominator = (denominator * (x_i - x_j)) % self.prime

            # l_i(0) = numerator / denominator mod prime
            lagrange_coeff = (numerator * self._mod_inverse(denominator, self.prime)) % self.prime
            secret = (secret + y_i * lagrange_coeff) % self.prime

        return secret

    def _mod_inverse(self, a: int, m: int) -> int:
        """Compute modular inverse using extended Euclidean algorithm."""
        def extended_gcd(a, b):
            if b == 0:
                return (a, 1, 0)
            g, x1, y1 = extended_gcd(b, a % b)
            x = y1
            y = x1 - (a // b) * y1
            return (g, x, y)

        g, x, _ = extended_gcd(a % m, m)
        if g != 1:
            raise ValueError(f"No modular inverse for {a} mod {m}")
        return x % m


class MaskManager:
    """
    Per-Client Concealment Masking (PCCM) manager.
    
    Handles:
    - Self-mask generation: s_i ← U(-B, B)
    - Pairwise mask negotiation: r_ij = -r_ji
    - Total mask computation: m_i = s_i + Σ_j r_ij
    - Shamir sharing of self-masks for later recovery
    """

    def __init__(self, client_id: int, num_clients: int, threshold: int,
                 mask_range: int = 2 ** 20, prime: int = DEFAULT_PRIME,
                 seed: int = None):
        self.client_id = client_id
        self.n = num_clients
        self.t = threshold
        self.B = mask_range
        self.prime = prime
        self.shamir = ShamirSecretSharing(prime)

        if seed is not None:
            random.seed(seed + client_id)

        # Self-mask (kept secret)
        self.self_mask = random.randint(-self.B, self.B)

        # Pairwise masks: r_ij for each neighbor j
        # r_ij = -r_ji
        self.pairwise_masks: Dict[int, int] = {}

        # Shamir shares of self-mask (distributed to other clients)
        self.self_mask_shares: List[Tuple[int, int]] = []

        # Received shares from other clients
        # {client_j: [(round, share_value), ...]}
        self.received_shares: Dict[int, List[Tuple[int, int]]] = {}

    def generate_pairwise_masks(self, neighbor_ids: List[int],
                                 shared_seeds: Dict[int, int] = None):
        """
        Generate pairwise masks r_ij such that r_ij = -r_ji.
        
        Two methods:
        1. If shared_seeds provided: use PRNG with shared seed
        2. Otherwise: use Diffie-Hellman style negotiation (simplified)
        
        For simplicity in implementation, we use shared seeds derived from
        client ID pair hash.
        """
        for j in neighbor_ids:
            if j == self.client_id:
                continue

            # Deterministic shared seed from client pair
            pair_seed = hash((min(self.client_id, j), max(self.client_id, j))) % (2 ** 32)
            rng = random.Random(pair_seed)

            # C_i computes r_ij, C_j computes r_ji = -r_ij
            if self.client_id < j:
                r_ij = rng.randint(-self.B, self.B)
            else:
                r_ij = -rng.randint(-self.B, self.B)

            self.pairwise_masks[j] = r_ij

    def compute_total_mask(self) -> int:
        """Compute total mask: m_i = s_i + Σ_j r_ij"""
        total = self.self_mask
        for r_ij in self.pairwise_masks.values():
            total += r_ij
        return total

    def split_self_mask(self, round_num: int = 0) -> Dict[int, Tuple[int, int]]:
        """
        Split self-mask into n Shamir shares.
        
        Returns:
            {client_j: (share_index, share_value)} for distribution
        """
        # Encode self_mask into finite field
        secret = (self.self_mask + self.B) % self.prime  # Shift to positive

        shares = self.shamir.split(secret, self.n, self.t)

        # Format for distribution
        share_dict = {}
        for idx, (share_idx, share_val) in enumerate(shares):
            share_dict[idx] = (share_idx, share_val)

        self.self_mask_shares = shares
        return share_dict

    def receive_share(self, from_client: int, round_num: int,
                      share_idx: int, share_val: int):
        """Receive a Shamir share from another client.
        
        Args:
            from_client: Client ID who sent the share
            round_num: Training round number
            share_idx: The x-coordinate (1-based) of the share
            share_val: The share value
        """
        if from_client not in self.received_shares:
            self.received_shares[from_client] = []
        self.received_shares[from_client].append((round_num, share_idx, share_val))

    def recover_mask(self, round_num: int, available_clients: Set[int]) -> int:
        """
        Recover self-mask for a given round from received shares.
        
        Args:
            round_num: Which round's mask to recover
            available_clients: Set of client IDs whose shares we have
            
        Returns:
            Recovered mask value
        """
        shares = []
        for client_id, share_list in self.received_shares.items():
            if client_id in available_clients:
                for r, idx, val in share_list:
                    if r == round_num:
                        shares.append((idx, val))  # idx is already 1-based
                        break

        if len(shares) < self.t:
            raise ValueError(f"Need {self.t} shares, only have {len(shares)}")

        recovered = self.shamir.reconstruct(shares[:self.t])
        # Shift back: we added B before splitting
        recovered_shifted = (recovered - self.B) % self.prime
        if recovered_shifted > self.prime // 2:
            recovered_shifted -= self.prime
        return recovered_shifted

    def apply_mask_to_gradient(self, gradient: dict, mask: int) -> dict:
        """Add mask to each element of gradient (for scalar mask over all params)."""
        # For simplicity, add mask to each parameter's first element
        # In practice, mask should be expanded to match gradient shape
        masked = {}
        for key, val in gradient.items():
            if hasattr(val, 'shape'):
                # Tensor: add mask to all elements
                import torch
                masked[key] = val + mask
            else:
                masked[key] = val + mask
        return masked


# ============================================================================
# Tests
# ============================================================================

if __name__ == "__main__":
    print("Testing Shamir Secret Sharing...")

    # Test 1: Basic split and reconstruct
    sss = ShamirSecretSharing()
    secret = 42
    n, t = 5, 3

    shares = sss.split(secret, n, t)
    print(f"Secret: {secret}")
    print(f"Shares: {shares}")

    # Reconstruct with t shares
    recovered = sss.reconstruct(shares[:t])
    print(f"Recovered (with {t} shares): {recovered}")
    assert recovered == secret, "Reconstruction failed!"

    # Reconstruct with n shares
    recovered_all = sss.reconstruct(shares)
    print(f"Recovered (with {n} shares): {recovered_all}")
    assert recovered_all == secret, "Reconstruction failed!"

    # Test 2: t-1 shares should NOT reconstruct (information-theoretic security)
    # We can't test this deterministically, but we can verify they don't crash
    try:
        partial = sss.reconstruct(shares[:t - 1])
        print(f"Partial reconstruction (t-1={t-1} shares): {partial} (should be random)")
        assert partial != secret, "t-1 shares should not reveal secret!"
    except ValueError as e:
        print(f"t-1 shares correctly failed: {e}")

    print("\nTesting MaskManager...")

    # Test 3: Pairwise mask cancellation
    n_clients = 4
    managers = [MaskManager(i, n_clients, threshold=3, seed=12345) for i in range(n_clients)]

    # Generate pairwise masks
    for i, mgr in enumerate(managers):
        mgr.generate_pairwise_masks(list(range(n_clients)))

    # Verify r_ij = -r_ji
    for i in range(n_clients):
        for j in range(i + 1, n_clients):
            r_ij = managers[i].pairwise_masks[j]
            r_ji = managers[j].pairwise_masks[i]
            assert r_ij == -r_ji, f"Pairwise mask cancellation failed for ({i},{j})"

    print("Pairwise mask cancellation: PASSED")

    # Verify total pairwise sum = 0
    total_pairwise = 0
    for i in range(n_clients):
        for j in range(n_clients):
            if i != j:
                total_pairwise += managers[i].pairwise_masks[j]
    assert total_pairwise == 0, "Total pairwise mask sum should be 0"
    print("Total pairwise mask sum = 0: PASSED")

    # Test 4: Shamir sharing and recovery
    mgr = managers[0]
    shares_dict = mgr.split_self_mask(round_num=0)

    # Simulate distribution and recovery
    for recipient_id in range(n_clients):
        if recipient_id == 0:
            continue
        share_idx, share_val = shares_dict[recipient_id]
        # Recipient (client 0) receives the share
        mgr.receive_share(from_client=recipient_id, round_num=0,
                          share_idx=share_idx, share_val=share_val)

    # Recover from t shares
    available = set(range(1, n_clients))
    recovered = mgr.recover_mask(0, available)
    assert recovered == mgr.self_mask, "Mask recovery failed!"
    print(f"Mask recovery: PASSED (recovered={recovered}, original={mgr.self_mask})")

    print("\nAll tests passed!")
