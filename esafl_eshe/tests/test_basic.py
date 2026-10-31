"""
Basic functionality tests for the esafl_eshe multi-key HE backend.

Run with:
    python -m pytest esafl_eshe/tests/test_basic.py -v
or:
    python esafl_eshe/tests/test_basic.py
"""

import sys
import os
import unittest
import numpy as np

# Ensure project root is on path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT_ROOT)

from esafl_eshe import ESHEManager


class TestESHEBasic(unittest.TestCase):
    """Basic tests covering key generation, encryption, aggregation, and decryption."""

    def test_end_to_end_two_clients(self):
        """Two clients encrypt, server aggregates, distributed decryption recovers sum."""
        num_clients = 2
        slot_size = 4096
        mgr = ESHEManager(num_clients=num_clients, slot_size=slot_size)
        mgr.setup()

        # Client plaintexts
        pt1 = np.random.randn(slot_size).tolist()
        pt2 = np.random.randn(slot_size).tolist()
        expected = np.array(pt1) + np.array(pt2)

        # Encrypt and aggregate
        ct1 = mgr.encrypt(0, pt1)
        ct2 = mgr.encrypt(1, pt2)
        agg_ct = mgr.aggregate([ct1, ct2])

        # Distributed decryption
        shares = [mgr.partial_decrypt(0, agg_ct), mgr.partial_decrypt(1, agg_ct)]
        decoded = mgr.decode(shares, [0, 1])

        # Check approximate equality (CKKS is approximate arithmetic)
        np.testing.assert_allclose(decoded, expected, rtol=1e-3, atol=1e-2)

    def test_end_to_end_five_clients(self):
        """Five clients encrypt and aggregate; decryption recovers the sum."""
        num_clients = 5
        slot_size = 4096
        mgr = ESHEManager(num_clients=num_clients, slot_size=slot_size)
        mgr.setup()

        plaintexts = [np.random.randn(slot_size).tolist() for _ in range(num_clients)]
        expected = sum(np.array(pt) for pt in plaintexts)

        cts = [mgr.encrypt(i, pt) for i, pt in enumerate(plaintexts)]
        agg_ct = mgr.aggregate(cts)

        decoded = mgr.full_decrypt(agg_ct)
        np.testing.assert_allclose(decoded, expected, rtol=1e-3, atol=1e-2)

    def test_partial_participation(self):
        """Only a subset of clients participates; decryption still works for that subset."""
        num_clients = 5
        slot_size = 4096
        mgr = ESHEManager(num_clients=num_clients, slot_size=slot_size)
        mgr.setup()

        participating = [0, 2, 4]
        plaintexts = [np.random.randn(slot_size).tolist() for _ in participating]
        expected = sum(np.array(pt) for pt in plaintexts)

        cts = [mgr.encrypt(cid, pt) for cid, pt in zip(participating, plaintexts)]
        agg_ct = mgr.aggregate(cts)

        decoded = mgr.full_decrypt(agg_ct, participating)
        np.testing.assert_allclose(decoded, expected, rtol=1e-3, atol=1e-2)

    def test_padding(self):
        """Shorter plaintexts are zero-padded before encryption."""
        num_clients = 2
        slot_size = 4096
        mgr = ESHEManager(num_clients=num_clients, slot_size=slot_size)
        mgr.setup()

        pt1 = [1.0, 2.0, 3.0]
        pt2 = [4.0, 5.0, 6.0]

        ct1 = mgr.encrypt(0, pt1)
        ct2 = mgr.encrypt(1, pt2)
        agg_ct = mgr.aggregate([ct1, ct2])
        decoded = mgr.full_decrypt(agg_ct)

        self.assertAlmostEqual(decoded[0], 5.0, places=2)
        self.assertAlmostEqual(decoded[1], 7.0, places=2)
        self.assertAlmostEqual(decoded[2], 9.0, places=2)
        # Remaining slots should be near zero
        self.assertLess(np.max(np.abs(decoded[3:100])), 1e-1)


if __name__ == "__main__":
    unittest.main()
