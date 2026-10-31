"""
Utility helpers for the esafl_eshe multi-key HE backend.
"""

from typing import List
import numpy as np


def pad_to_length(values: List[float], length: int) -> List[float]:
    """
    Pad a list of floats with zeros to reach the specified length.

    Args:
        values: Input list of floats.
        length: Target length.

    Returns:
        Zero-padded list of length `length`.

    Raises:
        ValueError: If the input is already longer than `length`.
    """
    if len(values) > length:
        raise ValueError(f"Input length {len(values)} exceeds target length {length}.")
    return list(values) + [0.0] * (length - len(values))


def chunks_to_array(
    chunks: List[List[float]],
    total_length: int,
    slot_size: int,
) -> np.ndarray:
    """
    Flatten a list of ciphertext plaintext chunks into a single array and trim
    to the original parameter length.

    Args:
        chunks: List of decoded plaintext vectors, each of length slot_size.
        total_length: Original number of scalar values before padding.
        slot_size: Number of slots per chunk.

    Returns:
        Numpy array of length total_length containing the concatenated chunks.
    """
    flat = []
    for chunk in chunks:
        flat.extend(chunk[:slot_size])
    return np.array(flat[:total_length], dtype=np.float64)


def array_to_chunks(arr: np.ndarray, slot_size: int) -> List[List[float]]:
    """
    Split a 1-D numpy array into chunks of size slot_size, zero-padding the last
    chunk if necessary.

    Args:
        arr: Input 1-D array.
        slot_size: Chunk size.

    Returns:
        List of chunks as Python lists of floats.
    """
    n = len(arr)
    num_chunks = (n + slot_size - 1) // slot_size
    chunks = []
    for i in range(num_chunks):
        chunk = arr[i * slot_size : (i + 1) * slot_size].tolist()
        if len(chunk) < slot_size:
            chunk += [0.0] * (slot_size - len(chunk))
        chunks.append(chunk)
    return chunks
