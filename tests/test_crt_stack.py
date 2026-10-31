"""
CRTStackPacking 单元测试
验证 CRT-Stack 传输层压缩打包策略的 pack/unpack 正确性与精度。
"""

import torch
import numpy as np
import pytest
from ckks_fed.packing import CRTStackPacking


class TestCRTStackPacking:
    def test_basic_pack_unpack(self):
        """基本 pack/unpack 功能测试"""
        slot_count = 4096
        packing = CRTStackPacking(slot_count, layers=4, quant_bits=8)

        model_update = {
            "layer1.weight": torch.randn(16, 32),
            "layer1.bias": torch.randn(16),
            "layer2.weight": torch.randn(8, 16),
        }

        chunks, metadata = packing.pack(model_update)
        assert len(chunks) > 0
        assert all(len(c) == slot_count for c in chunks)

        # 模拟解密（直接复用浮点值）
        decrypted = [c.copy() for c in chunks]
        unpacked = packing.unpack(decrypted, metadata)

        for name in model_update:
            assert name in unpacked
            assert unpacked[name].shape == model_update[name].shape

    def test_quantization_error(self):
        """量化误差应在合理范围内（8位：约 0.4% max abs）"""
        slot_count = 4096
        packing = CRTStackPacking(slot_count, layers=4, quant_bits=8)

        torch.manual_seed(42)
        model_update = {
            "w": torch.randn(1000),
        }

        chunks, metadata = packing.pack(model_update)
        decrypted = [c.copy() for c in chunks]
        unpacked = packing.unpack(decrypted, metadata)

        original = model_update["w"].numpy()
        recovered = unpacked["w"].numpy()

        max_abs = np.max(np.abs(original))
        max_err = np.max(np.abs(original - recovered))
        rel_err = max_err / max_abs if max_abs > 0 else 0

        # 8位对称量化理论最大相对误差 ≈ 1/(2*127) ≈ 0.4%
        assert rel_err < 0.01, f"相对误差 {rel_err:.4%} 超出预期"

    def test_compression_ratio(self):
        """验证压缩率 = layers"""
        slot_count = 4096
        layers = 4
        packing = CRTStackPacking(slot_count, layers=layers, quant_bits=8)

        # 制造大量参数
        n = slot_count * layers * 3  # 3 chunks
        model_update = {"w": torch.randn(n)}

        chunks, _ = packing.pack(model_update)
        # 标准打包需要 ceil(n / slot_count) = 12 chunks
        # CRTStack 只需要 ceil(n / (slot_count * layers)) = 3 chunks
        assert len(chunks) == 3

    def test_zero_values(self):
        """全零值应正确恢复"""
        slot_count = 4096
        packing = CRTStackPacking(slot_count, layers=4, quant_bits=8)

        model_update = {
            "w": torch.zeros(500),
            "b": torch.zeros(200),
        }

        chunks, metadata = packing.pack(model_update)
        decrypted = [c.copy() for c in chunks]
        unpacked = packing.unpack(decrypted, metadata)

        for name in model_update:
            assert np.allclose(unpacked[name].numpy(), 0, atol=1e-6)

    def test_negative_values(self):
        """负值应正确编码/解码"""
        slot_count = 4096
        packing = CRTStackPacking(slot_count, layers=4, quant_bits=8)

        model_update = {"w": torch.tensor([-1.5, -0.5, -0.1, 0.1, 0.5, 1.5])}

        chunks, metadata = packing.pack(model_update)
        decrypted = [c.copy() for c in chunks]
        unpacked = packing.unpack(decrypted, metadata)

        original = model_update["w"].numpy()
        recovered = unpacked["w"].numpy()
        assert np.allclose(original, recovered, atol=0.02)

    def test_small_param_count(self):
        """参数数量少于 slot_count * layers 时仍能正确工作"""
        slot_count = 4096
        packing = CRTStackPacking(slot_count, layers=4, quant_bits=8)

        model_update = {"w": torch.randn(10)}

        chunks, metadata = packing.pack(model_update)
        assert len(chunks) == 1
        decrypted = [c.copy() for c in chunks]
        unpacked = packing.unpack(decrypted, metadata)
        assert unpacked["w"].shape == (10,)

    def test_different_layers(self):
        """测试不同 layers 配置"""
        for layers in [2, 4, 8]:
            # 为不同 layers 选择合适模数
            if layers == 2:
                moduli = [257, 263]
            elif layers == 4:
                moduli = [257, 263, 269, 271]
            else:
                moduli = [257, 263, 269, 271, 277, 281, 283, 293]

            slot_count = 1024
            packing = CRTStackPacking(slot_count, layers=layers, quant_bits=8, moduli=moduli)
            model_update = {"w": torch.randn(500)}

            chunks, metadata = packing.pack(model_update)
            decrypted = [c.copy() for c in chunks]
            unpacked = packing.unpack(decrypted, metadata)
            assert unpacked["w"].shape == (500,)

    def test_crt_math_correctness(self):
        """验证 CRT 编码/解码数学正确性"""
        packing = CRTStackPacking(4096, layers=4, quant_bits=8)

        # 随机生成 d 个在 [0, 254] 范围内的值
        for _ in range(100):
            vals = np.random.randint(0, 255, size=packing.layers).tolist()
            x = packing._crt_encode(vals)
            decoded = packing._crt_decode(x)
            assert decoded == vals, f"CRT 编解码不一致: {vals} -> {x} -> {decoded}"

    def test_metadata_integrity(self):
        """metadata 应包含必要字段"""
        slot_count = 4096
        packing = CRTStackPacking(slot_count, layers=4, quant_bits=8)

        model_update = {"w": torch.randn(100)}
        chunks, metadata = packing.pack(model_update)

        data = metadata.data
        assert "shapes" in data
        assert "offsets" in data
        assert "total_elements" in data
        assert "layer_scales" in data
        assert "layers" in data and data["layers"] == 4
        assert "quant_bits" in data and data["quant_bits"] == 8
        assert "moduli" in data
        assert "P" in data


if __name__ == "__main__":
    test = TestCRTStackPacking()
    test.test_basic_pack_unpack()
    print("PASS: test_basic_pack_unpack")
    test.test_quantization_error()
    print("PASS: test_quantization_error")
    test.test_compression_ratio()
    print("PASS: test_compression_ratio")
    test.test_zero_values()
    print("PASS: test_zero_values")
    test.test_negative_values()
    print("PASS: test_negative_values")
    test.test_small_param_count()
    print("PASS: test_small_param_count")
    test.test_different_layers()
    print("PASS: test_different_layers")
    test.test_crt_math_correctness()
    print("PASS: test_crt_math_correctness")
    test.test_metadata_integrity()
    print("PASS: test_metadata_integrity")
    print("\nAll tests passed!")
