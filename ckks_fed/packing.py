"""
CKKS 模型更新可插拔打包策略模块
支持多种打包方式以减少 ciphertext 数量：
  - layerwise:   逐层加密（默认，兼容原代码）
  - merged:      将所有层合并成一个数组后统一分块加密
  - conjugate:   利用复数实部/虚部分别存储两个值，slot 容量翻倍
  - twotier:     Two-Pack CKKS 适配版（分层量化 + slot batching）
"""

import numpy as np
import torch
from typing import Dict, List, Tuple, Any
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class PackingMetadata:
    """打包后的元数据，用于解密恢复"""

    def __init__(self, strategy: str, data: Dict[str, Any]):
        self.strategy = strategy
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return {"__packing_strategy__": self.strategy, "__packing_data__": self.data}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PackingMetadata":
        return cls(d["__packing_strategy__"], d["__packing_data__"])


class PackingStrategy(ABC):
    """模型更新打包策略抽象基类"""

    def __init__(self, slot_count: int):
        self.slot_count = slot_count

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def pack(self, model_update: Dict[str, torch.Tensor]) -> Tuple[List[np.ndarray], PackingMetadata]:
        """
        将 model_update 打包为可加密块列表。
        返回: (chunks, metadata)
          chunks: List[np.ndarray]，每个数组长度为 slot_count（不足则 pad）
          metadata: 解密恢复所需元数据
        """
        pass

    @abstractmethod
    def unpack(self, decrypted_chunks: List[np.ndarray], metadata: PackingMetadata) -> Dict[str, torch.Tensor]:
        """
        从解密后的 chunks 恢复 model_update。
        """
        pass

    def _pad_chunk(self, chunk: np.ndarray) -> np.ndarray:
        """将数组填充到 slot_count 长度"""
        if len(chunk) < self.slot_count:
            return np.pad(chunk, (0, self.slot_count - len(chunk)), mode="constant")
        return chunk

    def get_values_per_chunk(self) -> int:
        """返回每个 chunk 对应的**原始参数数量**。

        用于 GlobalMaskVote 对齐切分边界：投票阶段的 batch 大小
        必须和加密阶段的 chunk 切分大小一致。

        默认实现：每个 chunk 存 slot_count 个原始值（Merged/Layerwise）。
        CRTStack 等压缩策略必须覆盖此方法。
        """
        return self.slot_count

    def create_zero_chunk(self) -> np.ndarray:
        """生成表示"零值"的 chunk，用于 mask=0 时的占位填充。
        
        默认实现返回浮点 0 数组（适用于无额外编解码的策略如 Merged）。
        引入量化/CRT 编码的策略（CRTStack）必须覆盖此方法，
        确保 unpack 后缺失位置还原为浮点 0，而非编码空间中的 0。
        """
        return np.zeros(self.slot_count, dtype=np.float64)


class LayerwisePacking(PackingStrategy):
    """
    逐层打包（默认行为，完全兼容原代码）。
    每层独立 flatten 后分块，保持 Dict[str, List[CKKSVector]] 的层级结构。
    """

    @property
    def name(self) -> str:
        return "layerwise"

    def pack(self, model_update: Dict[str, torch.Tensor]) -> Tuple[List[np.ndarray], PackingMetadata]:
        """
        为了与上层 crypto.py 兼容，layerwise 模式下不真正合并，
        而是返回一个标记性的结构，由 crypto.py 按原逻辑逐层处理。
        这里仅返回空 chunks 和标记 metadata。
        """
        return [], PackingMetadata(self.name, {"layerwise": True})

    def unpack(self, decrypted_chunks: List[np.ndarray], metadata: PackingMetadata) -> Dict[str, torch.Tensor]:
        # layerwise 不走此接口，由 CKKSDecryptor.decrypt_to_tensor 逐层处理
        raise NotImplementedError("LayerwisePacking.unpack 不应被直接调用")


class MergedPacking(PackingStrategy):
    """
    合并打包：将所有层的参数按固定顺序 concat 成一个长数组，
    再按 slot_count 统一分块加密。
    可显著减少小层（bias）造成的密文碎片。
    """

    @property
    def name(self) -> str:
        return "merged"

    def pack(self, model_update: Dict[str, torch.Tensor]) -> Tuple[List[np.ndarray], PackingMetadata]:
        # 按固定顺序合并所有参数（排序保证确定性）
        all_values = []
        shapes = {}
        offsets = {}
        offset = 0

        for name in sorted(model_update.keys()):
            param = model_update[name]
            flat = param.detach().cpu().numpy().flatten()
            shapes[name] = list(param.shape)
            offsets[name] = (offset, param.numel())
            all_values.extend(flat.tolist())
            offset += param.numel()

        # 统一分块并填充
        chunks = []
        for i in range(0, len(all_values), self.slot_count):
            chunk = np.array(all_values[i : i + self.slot_count], dtype=np.float64)
            chunk = self._pad_chunk(chunk)
            chunks.append(chunk)

        metadata = PackingMetadata(
            self.name,
            {"shapes": shapes, "offsets": offsets, "total_elements": len(all_values)},
        )
        return chunks, metadata

    def unpack(self, decrypted_chunks: List[np.ndarray], metadata: PackingMetadata) -> Dict[str, torch.Tensor]:
        data = metadata.data
        shapes = data["shapes"]
        offsets = data["offsets"]
        total_elements = data["total_elements"]

        # 拼接所有 chunks 并截取有效长度
        all_values = np.concatenate([chunk[: self.slot_count] for chunk in decrypted_chunks])[:total_elements]

        result = {}
        for name in sorted(shapes.keys()):
            offset, numel = offsets[name]
            shape = shapes[name]
            result[name] = torch.tensor(all_values[offset : offset + numel].reshape(shape))
        return result


class ConjugatePacking(PackingStrategy):
    """
    复数共轭打包：利用 CKKS 复数域特性，将两个实数分别存入
    一个复数的实部和虚部，使每个 slot 容量翻倍。
    要求底层 TenSEAL 支持复数数组编码。
    """

    @property
    def name(self) -> str:
        return "conjugate"

    def pack(self, model_update: Dict[str, torch.Tensor]) -> Tuple[List[np.ndarray], PackingMetadata]:
        # 合并所有参数
        all_values = []
        shapes = {}
        offsets = {}
        offset = 0

        for name in sorted(model_update.keys()):
            param = model_update[name]
            flat = param.detach().cpu().numpy().flatten()
            shapes[name] = list(param.shape)
            offsets[name] = (offset, param.numel())
            all_values.extend(flat.tolist())
            offset += param.numel()

        # 配对：实部=值1, 虚部=值2
        pairs = []
        for i in range(0, len(all_values), 2):
            if i + 1 < len(all_values):
                pairs.append(all_values[i] + 1j * all_values[i + 1])
            else:
                pairs.append(all_values[i] + 0j)

        # 按 slot_count 分块并填充
        chunks = []
        for i in range(0, len(pairs), self.slot_count):
            chunk = np.array(pairs[i : i + self.slot_count], dtype=np.complex128)
            if len(chunk) < self.slot_count:
                chunk = np.pad(chunk, (0, self.slot_count - len(chunk)), mode="constant")
            chunks.append(chunk)

        metadata = PackingMetadata(
            self.name,
            {"shapes": shapes, "offsets": offsets, "total_elements": len(all_values)},
        )
        return chunks, metadata

    def unpack(self, decrypted_chunks: List[np.ndarray], metadata: PackingMetadata) -> Dict[str, torch.Tensor]:
        data = metadata.data
        shapes = data["shapes"]
        offsets = data["offsets"]
        total_elements = data["total_elements"]

        # 从复数数组提取实部和虚部
        all_values = []
        for chunk in decrypted_chunks:
            for val in chunk[: self.slot_count]:
                all_values.append(val.real)
                if len(all_values) < total_elements:
                    all_values.append(val.imag)

        all_values = np.array(all_values[:total_elements])

        result = {}
        for name in sorted(shapes.keys()):
            offset, numel = offsets[name]
            shape = shapes[name]
            result[name] = torch.tensor(all_values[offset : offset + numel].reshape(shape))
        return result


def _check_conjugate_support() -> bool:
    """检测当前 TenSEAL 是否支持复数编码"""
    try:
        import tenseal as ts
        ctx = ts.context(ts.SCHEME_TYPE.CKKS, 4096, [40, 20, 40])
        data = np.array([1.0 + 2.0j], dtype=np.complex128)
        ct = ts.ckks_vector(ctx, data)
        dec = ct.decrypt()[0]
        # 如果虚部被保留，dec 应该是复数且 imag 接近 2.0
        return np.iscomplexobj(dec) and abs(dec.imag - 2.0) < 0.1
    except Exception:
        return False


# 全局缓存检测结果
_CONJUGATE_SUPPORTED = None


class TwoTierPacking(PackingStrategy):
    """
    Two-Pack CKKS 适配版 (Zhou et al., CCS 2024)。

    论文原方案基于纯加法 RLWE HE（BFV/BGV），核心贡献：
      - Tier 1 (IntCRT):  整数层 CRT 编码，避免拼接进位溢出
      - Tier 2 (PolySubR): 多项式层子环分解，提升打包密度

    CKKS 适配思路：
      - Tier 1: 分块对称量化。把浮点更新压缩为 16-bit（或配置比特）整数，
                等效于论文"整数层打包"——将数据压缩到更紧凑的数值表示。
      - Tier 2: 量化后的 slot batching。利用 CKKS 的 SIMD 能力，一个密文
                并行处理 N/2 个量化值。由于值范围被压缩，聚合精度更稳定。

    相比 MergedPacking：
      - 密文数量相同（每个 slot 仍存一个值）
      - 但精度-通信权衡更优：量化后的值范围更小，CKKS 近似误差影响更低
      - per-block scale 适应不同层的数值分布，比全局缩放更精细
    """

    def __init__(self, slot_count: int, quant_bits: int = 16):
        super().__init__(slot_count)
        self.quant_bits = quant_bits
        self.max_q = float(2 ** (quant_bits - 1) - 1)  # 对称量化最大值

    @property
    def name(self) -> str:
        return "twotier"

    def _quantize_block(self, block: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        对单个 block 做对称 min-max 量化。
        返回: (quantized_floats, scale)
          quantized_floats: 范围在 [-1, 1] 的 float64 数组，可直接输入 CKKS
          scale: 反量化所需的缩放因子
        """
        max_abs = float(np.max(np.abs(block)))
        if max_abs < 1e-12:
            return np.zeros_like(block, dtype=np.float64), 1.0

        scale = max_abs / self.max_q
        # 量化为整数，再归一化到 [-1, 1] 以输入 CKKS
        q_int = np.round(block / scale).astype(np.float64)
        # 限制在有效范围，防止溢出
        q_int = np.clip(q_int, -self.max_q, self.max_q)
        q_float = q_int / self.max_q  # 范围 [-1, 1]
        return q_float, scale

    def pack(self, model_update: Dict[str, torch.Tensor]) -> Tuple[List[np.ndarray], PackingMetadata]:
        # 1) 按固定顺序合并所有参数
        all_values = []
        shapes = {}
        offsets = {}
        offset = 0

        for name in sorted(model_update.keys()):
            param = model_update[name]
            flat = param.detach().cpu().numpy().flatten()
            shapes[name] = list(param.shape)
            offsets[name] = (offset, param.numel())
            all_values.extend(flat.tolist())
            offset += param.numel()

        total_elements = len(all_values)

        # 2) Tier 1: 分块量化（每 block 一个 scale）
        # 3) Tier 2: 按 slot_count 分块并填充
        chunks = []
        scales = []

        for i in range(0, total_elements, self.slot_count):
            block = np.array(all_values[i : i + self.slot_count], dtype=np.float64)
            q_float, scale = self._quantize_block(block)
            q_float = self._pad_chunk(q_float)
            chunks.append(q_float)
            scales.append(scale)

        metadata = PackingMetadata(
            self.name,
            {
                "shapes": shapes,
                "offsets": offsets,
                "total_elements": total_elements,
                "quant_bits": self.quant_bits,
                "scales": scales,
            },
        )
        return chunks, metadata

    def unpack(self, decrypted_chunks: List[np.ndarray], metadata: PackingMetadata) -> Dict[str, torch.Tensor]:
        data = metadata.data
        shapes = data["shapes"]
        offsets = data["offsets"]
        total_elements = data["total_elements"]
        scales = data["scales"]
        quant_bits = data.get("quant_bits", self.quant_bits)
        max_q = float(2 ** (quant_bits - 1) - 1)

        # 反量化：先还原到量化整数范围，再乘以 per-block scale
        all_values = []
        for idx, chunk in enumerate(decrypted_chunks):
            chunk = np.array(chunk, dtype=np.float64)[: self.slot_count]
            scale = scales[idx]
            # chunk 是 [-1, 1] 范围的 float，先还原到 [-max_q, max_q]
            q_int = np.round(chunk * max_q).astype(np.float64)
            # 反量化到原始值
            block_vals = q_int * scale
            all_values.extend(block_vals.tolist())

        all_values = np.array(all_values[:total_elements])

        result = {}
        for name in sorted(shapes.keys()):
            off, numel = offsets[name]
            shape = shapes[name]
            result[name] = torch.tensor(all_values[off : off + numel].reshape(shape))
        return result


class CRTStackPacking(PackingStrategy):
    """
    CRT-Stack 数据压缩打包。

    核心思想：利用中国剩余定理（CRT），将 d 个量化后的整数值编码为
    单个浮点数，存入 1 个 CKKS slot。压缩率 = d×。

    适用场景：传输层压缩。客户端量化+CRT打包→加密上传→服务器解密后
    明文解包→恢复为标准浮点数组→聚合。无需同态 mod 解包。

    参数：
      - layers: CRT 层数 d（每 slot 存 d 个值），默认 4
      - quant_bits: 量化位宽，默认 8（范围 [-127, 127]，映射到 [0, 254]）
      - moduli: CRT 基础模数列表，必须两两互素且 > 2^quant_bits
    """

    # 默认 CRT 模数：4 个大于 256 的素数，两两互素
    # P = 257 * 263 * 269 * 271 = 4,924,014,089 < 2^53 (double 精确整数范围)
    DEFAULT_MODULI = [257, 263, 269, 271]

    def __init__(self, slot_count: int, layers: int = 4, quant_bits: int = 8,
                 moduli: List[int] = None):
        super().__init__(slot_count)
        self.layers = layers
        self.quant_bits = quant_bits
        self.max_q = float(2 ** (quant_bits - 1) - 1)  # 对称量化最大值，如 127
        self.moduli = moduli or self.DEFAULT_MODULI[:layers]
        assert len(self.moduli) == layers, f"moduli 数量({len(self.moduli)})必须等于 layers({layers})"
        assert all(m > 2 ** quant_bits for m in self.moduli), "每个模数必须大于 2^quant_bits"

        # 预计算 CRT 打包系数 b_i
        self.P = 1
        for m in self.moduli:
            self.P *= m
        self.crt_coeffs = []
        for i, mi in enumerate(self.moduli):
            Pi = self.P // mi
            # 扩展欧几里得求逆元
            inv = self._mod_inverse(Pi % mi, mi)
            bi = (Pi * inv) % self.P
            self.crt_coeffs.append(bi)

        logger.info(
            f"CRTStackPacking 初始化: layers={layers}, quant_bits={quant_bits}, "
            f"slot_count={slot_count}, P={self.P}, moduli={self.moduli}"
        )

    @staticmethod
    def _mod_inverse(a: int, m: int) -> int:
        """扩展欧几里得算法求模逆元"""
        def egcd(a, b):
            if b == 0:
                return (a, 1, 0)
            g, x1, y1 = egcd(b, a % b)
            return (g, y1, x1 - (a // b) * y1)
        g, x, _ = egcd(a % m, m)
        if g != 1:
            raise ValueError(f"{a} 在模 {m} 下无逆元")
        return x % m

    @property
    def name(self) -> str:
        return f"crtstack_d{self.layers}_q{self.quant_bits}"

    def get_values_per_chunk(self) -> int:
        """CRTStack：每 chunk 存 slot_count * layers 个原始量化值。"""
        return self.slot_count * self.layers

    def _quantize(self, values: np.ndarray, scale: float) -> np.ndarray:
        """对称量化：浮点 → 有符号整数 → 映射到无符号整数"""
        if scale < 1e-12:
            return np.zeros_like(values, dtype=np.int64)
        q = np.round(values / scale).astype(np.int64)
        q = np.clip(q, -int(self.max_q), int(self.max_q))
        # 映射到无符号：[0, 2*max_q]
        return q + int(self.max_q)

    def _dequantize_unsigned(self, uvals: np.ndarray, scale: float) -> np.ndarray:
        """反量化：无符号整数 → 有符号整数 → 浮点"""
        q = uvals.astype(np.float64) - self.max_q
        return q * scale

    def _crt_encode(self, vals: List[int]) -> int:
        """CRT 编码：d 个无符号整数 → 单个整数"""
        x = 0
        for ai, bi in zip(vals, self.crt_coeffs):
            x = (x + ai * bi) % self.P
        return x

    def _crt_decode(self, x: int) -> List[int]:
        """CRT 解码：单个整数 → d 个无符号整数"""
        return [x % mi for mi in self.moduli]

    def pack(self, model_update: Dict[str, torch.Tensor]) -> Tuple[List[np.ndarray], PackingMetadata]:
        # 1) 按固定顺序合并所有参数，并记录每层的 scale
        all_values = []
        shapes = {}
        offsets = {}
        layer_scales = {}
        offset = 0

        for name in sorted(model_update.keys()):
            param = model_update[name]
            flat = param.detach().cpu().numpy().flatten()
            shapes[name] = list(param.shape)
            offsets[name] = (offset, param.numel())

            # 每层独立 scale
            max_abs = float(np.max(np.abs(flat)))
            scale = max_abs / self.max_q if max_abs > 1e-12 else 1.0
            layer_scales[name] = scale

            # 量化并映射到无符号
            uvals = self._quantize(flat, scale)
            all_values.extend(uvals.tolist())
            offset += param.numel()

        total_elements = len(all_values)

        # 2) 每 d 个值一组，CRT 编码为单个整数，再转为 float
        # 每 chunk 存 slot_count 个编码值 → 对应 slot_count * d 个原始值
        values_per_chunk = self.slot_count * self.layers
        chunks = []

        for i in range(0, total_elements, values_per_chunk):
            group = all_values[i : i + values_per_chunk]
            # padding 到 values_per_chunk 的整数倍
            while len(group) % self.layers != 0:
                group.append(0)
            # 每 d 个值编码为 1 个 float
            encoded = []
            for j in range(0, len(group), self.layers):
                x = self._crt_encode(group[j : j + self.layers])
                encoded.append(float(x))
            # padding 到 slot_count
            chunk = np.array(encoded, dtype=np.float64)
            chunk = self._pad_chunk(chunk)
            chunks.append(chunk)

        metadata = PackingMetadata(
            self.name,
            {
                "shapes": shapes,
                "offsets": offsets,
                "total_elements": total_elements,
                "layer_scales": layer_scales,
                "layers": self.layers,
                "quant_bits": self.quant_bits,
                "moduli": self.moduli,
                "P": self.P,
            },
        )
        return chunks, metadata

    def create_zero_chunk(self) -> np.ndarray:
        """CRTStack 的零值 chunk：每个 slot 填充量化零点的 CRT 编码值。
        
        量化空间中，浮点 0 对应无符号值 max_q（因 _quantize 做了 +max_q 偏移）。
        若直接填充浮点 0，unpack 时 _crt_decode(0) 产生全 0 无符号值，
        再经 _dequantize_unsigned(0, scale) 得到 -max_q*scale，严重破坏模型。
        """
        zero_uvals = [int(self.max_q)] * self.layers
        zero_encoded = self._crt_encode(zero_uvals)
        return np.full(self.slot_count, float(zero_encoded), dtype=np.float64)

    def unpack(self, decrypted_chunks: List[np.ndarray], metadata: PackingMetadata) -> Dict[str, torch.Tensor]:
        data = metadata.data
        shapes = data["shapes"]
        offsets = data["offsets"]
        total_elements = data["total_elements"]
        layer_scales = data["layer_scales"]
        layers = data["layers"]

        # 1) 从 chunks 中提取 CRT 编码值并解码
        all_uvals = []
        for chunk in decrypted_chunks:
            for val in chunk[: self.slot_count]:
                if len(all_uvals) >= total_elements:
                    break
                decoded = self._crt_decode(int(round(float(val))))
                all_uvals.extend(decoded[:layers])
        all_uvals = np.array(all_uvals[:total_elements], dtype=np.float64)

        # 2) 按层反量化恢复浮点值
        result = {}
        for name in sorted(shapes.keys()):
            off, numel = offsets[name]
            shape = shapes[name]
            scale = layer_scales[name]
            uvals = all_uvals[off : off + numel]
            result[name] = torch.tensor(self._dequantize_unsigned(uvals, scale).reshape(shape))
        return result


class LayerwiseQuantizedPacking(PackingStrategy):
    """
    逐层量化合并打包 (Layer-wise Quantized Merged Packing)。

    核心设计 (受 BatchCrypt/QuanCrypt-FL 启发):
      1. 逐层独立对称量化：每层用自己的 min-max scale，避免大层拖垮小层
      2. 合并加密：量化后的所有层拼接成一个长数组，按 slot_count 分块加密
      3. 密文数量 = MergedPacking 级别（最少），精度 = 逐层级别（最高）

    相比 TwoTierPacking:
      - TwoTierPacking: per-block scale, block 可能跨层 → 小层精度被大层牺牲
      - LayerwiseQuantizedPacking: per-layer scale, 然后合并 → 每层精度独立保护

    相比 CRTStackPacking:
      - CRTStack: 8-bit 逐层 + CRT 压缩，但压缩后需要整数同态解包
      - LayerwiseQuantized: 16-bit 逐层 + 直接浮点编码，CKKS 原生兼容
    """

    def __init__(self, slot_count: int, quant_bits: int = 16):
        super().__init__(slot_count)
        self.quant_bits = quant_bits
        self.max_q = float(2 ** (quant_bits - 1) - 1)

    @property
    def name(self) -> str:
        return f"layerwise_quantized_q{self.quant_bits}"

    def _quantize_layer(self, values: np.ndarray) -> Tuple[np.ndarray, float]:
        """对单层的所有值做对称 min-max 量化，返回 (量化到[-1,1]的数组, scale)"""
        max_abs = float(np.max(np.abs(values)))
        if max_abs < 1e-12:
            return np.zeros_like(values, dtype=np.float64), 1.0
        scale = max_abs / self.max_q
        q_int = np.round(values / scale).astype(np.float64)
        q_int = np.clip(q_int, -self.max_q, self.max_q)
        q_float = q_int / self.max_q  # 映射到 [-1, 1] 供 CKKS 编码
        return q_float, scale

    def pack(self, model_update: Dict[str, torch.Tensor]) -> Tuple[List[np.ndarray], PackingMetadata]:
        # 1) 逐层量化，记录每层的 scale 和 shape
        shapes = {}
        offsets = {}
        layer_scales = {}
        all_quantized = []  # 所有层的量化值拼接
        offset = 0

        for name in sorted(model_update.keys()):
            param = model_update[name]
            flat = param.detach().cpu().numpy().flatten()
            shapes[name] = list(param.shape)

            # 逐层独立量化
            q_float, scale = self._quantize_layer(flat)
            layer_scales[name] = scale

            offsets[name] = (offset, param.numel())
            all_quantized.extend(q_float.tolist())
            offset += param.numel()

        total_elements = len(all_quantized)

        # 2) 合并后的数组按 slot_count 分块
        chunks = []
        for i in range(0, total_elements, self.slot_count):
            chunk = np.array(all_quantized[i : i + self.slot_count], dtype=np.float64)
            chunk = self._pad_chunk(chunk)
            chunks.append(chunk)

        metadata = PackingMetadata(
            self.name,
            {
                "shapes": shapes,
                "offsets": offsets,
                "total_elements": total_elements,
                "quant_bits": self.quant_bits,
                "layer_scales": layer_scales,
            },
        )
        return chunks, metadata

    def unpack(self, decrypted_chunks: List[np.ndarray], metadata: PackingMetadata) -> Dict[str, torch.Tensor]:
        data = metadata.data
        shapes = data["shapes"]
        offsets = data["offsets"]
        total_elements = data["total_elements"]
        layer_scales = data["layer_scales"]
        quant_bits = data.get("quant_bits", self.quant_bits)
        max_q = float(2 ** (quant_bits - 1) - 1)

        # 1) 拼接所有 chunks
        all_values = np.concatenate([chunk[: self.slot_count] for chunk in decrypted_chunks])[:total_elements]

        # 2) 逐层反量化
        result = {}
        for name in sorted(shapes.keys()):
            off, numel = offsets[name]
            shape = shapes[name]
            scale = layer_scales[name]

            q_float = all_values[off : off + numel]
            # 从 [-1, 1] 还原到量化整数范围
            q_int = np.round(q_float * max_q).astype(np.float64)
            # 反量化到原始值
            block_vals = q_int * scale
            result[name] = torch.tensor(block_vals.reshape(shape))
        return result


class ESAFLPacking(PackingStrategy):
    """
    ESAFL Bit-Packing 适配版。

    核心思想：将多个量化后的整数值通过 bit-shift 打包到单个 64-bit 浮点数的
    精确整数位域中，利用 double 的 53-bit 有效精度实现多值压缩。

    参数：
      - slots2: 每个 CKKS slot 打包的参数值数量，默认 4
      - quant_bits: 量化位宽，默认 8（范围 [-127, 127]，映射到 [0, 254]）
      - pad_bits: 值间 padding 位宽，默认 0（防止同态加法进位污染相邻值域）

    安全约束：slots2 * (quant_bits + pad_bits) <= 53，确保 double 精确整数表示。

    服务器聚合路径：当前项目当 packing_metadata 存在时自动走"明文解密→聚合→重加密"，
    因此 bit-packing 无需在密文域执行同态加法，完全兼容现有架构。
    """

    def __init__(self, slot_count: int, slots2: int = 4, quant_bits: int = 8,
                 pad_bits: int = 0, use_global_scale: bool = True):
        super().__init__(slot_count)
        self.slots2 = slots2
        self.quant_bits = quant_bits
        self.pad_bits = pad_bits
        self.use_global_scale = use_global_scale
        self.bits_per_value = quant_bits + pad_bits
        self.max_q = float(2 ** (quant_bits - 1) - 1)
        self.pack_mask = (1 << quant_bits) - 1

        total_bits = slots2 * self.bits_per_value
        if total_bits > 53:
            logger.warning(
                f"ESAFLPacking: slots2*{self.bits_per_value}={total_bits} bits > 53, "
                f"double 精度可能丢失，建议降低 slots2 或 quant_bits"
            )
        else:
            logger.info(
                f"ESAFLPacking 初始化: slot_count={slot_count}, slots2={slots2}, "
                f"quant_bits={quant_bits}, pad_bits={pad_bits}, total_bits={total_bits}, "
                f"use_global_scale={use_global_scale}"
            )

    @property
    def name(self) -> str:
        return f"esafl_s{self.slots2}_q{self.quant_bits}_p{self.pad_bits}"

    def get_values_per_chunk(self) -> int:
        """每 chunk 存 slot_count * slots2 个原始量化值。"""
        return self.slot_count * self.slots2

    def _quantize(self, values: np.ndarray, scale: float = None) -> Tuple[np.ndarray, float]:
        """对称量化：浮点 → 有符号整数 → 映射到无符号整数。返回 (uvals, scale)。

        Args:
            values: 待量化浮点数组。
            scale: 若提供，直接使用该 scale；否则从 values 自动估计（99.9 百分位裁剪）。
        """
        if not np.isfinite(values).all():
            bad_count = int((~np.isfinite(values)).sum())
            logger.warning(f"[PACK-DEBUG] _quantize input has {bad_count} non-finite values (NaN/Inf)!")
        max_abs = float(np.max(np.abs(values)))
        if max_abs < 1e-12:
            return np.zeros_like(values, dtype=np.int64), 1.0

        if scale is None:
            # 使用百分位数裁剪极端离群点，避免单个极大值拉大量化尺度、
            # 导致大多数小权重被量化到 0。这对 BatchNorm 后的卷积层尤为重要。
            clip_percentile = 99.9
            clip_max = float(np.percentile(np.abs(values), clip_percentile))
            if clip_max < 1e-12:
                clip_max = max_abs
            scale = clip_max / self.max_q

        clipped = np.clip(values, -scale * self.max_q, scale * self.max_q)
        q = np.round(clipped / scale).astype(np.int64)
        q = np.clip(q, -int(self.max_q), int(self.max_q))
        return (q + int(self.max_q)).astype(np.int64), scale

    def _encode_group(self, vals: List[int]) -> int:
        """将 slots2 个无符号整数 bit-shift 打包为一个整数。"""
        x = 0
        for val in reversed(vals):  # 先存低位，解码时顺序一致
            x = (x << self.bits_per_value) | int(val)
        return x

    def _decode_group(self, x: int) -> List[int]:
        """将一个整数 bit-shift 解包为 slots2 个无符号整数。"""
        vals = []
        for i in range(self.slots2):
            vals.append((x >> (i * self.bits_per_value)) & self.pack_mask)
        return vals

    @staticmethod
    def _is_bn_buffer(name: str) -> bool:
        """判断参数名是否对应 BatchNorm 的 running statistics。"""
        return any(key in name for key in ("running_mean", "running_var", "num_batches_tracked"))

    def pack(self, model_update: Dict[str, torch.Tensor]) -> Tuple[List[np.ndarray], PackingMetadata]:
        # 0) 将 BatchNorm 的 running statistics 与可训练参数分离
        #    BN 统计量对量化极度敏感（running_var 必须为正，running_mean 尺度小），
        #    直接打包容易导致 CKKS 编码溢出或解码后模型发散/NaN。
        #    这里把 BN buffer 以明文形式保留在 metadata 中，不参与 bit-packing。
        bn_buffers = {}
        packed_update = {}
        for name, param in model_update.items():
            if self._is_bn_buffer(name):
                # 使用 numpy 保存，避免后续序列化/深拷贝时 torch.Tensor 带来问题
                bn_buffers[name] = param.detach().cpu().numpy().copy()
            else:
                packed_update[name] = param

        # 1) 量化非 BN 参数。
        #    - 全局 scale（默认）：用所有参数的 99.9 百分位统一 scale，适合层间更新
        #      尺度相近的浅层网络（LeNet / CNNFashion）。
        #    - 逐层 scale（use_global_scale=false）：每层独立估计 scale，适合 ResNet 等
        #      深层网络，避免全局大尺度把小更新层压到 0。
        all_values = []
        shapes = {}
        offsets = {}
        layer_scales = {}
        offset = 0

        if self.use_global_scale:
            all_flats = [param.detach().cpu().numpy().flatten() for param in packed_update.values()]
            if all_flats:
                all_abs = np.concatenate([np.abs(f) for f in all_flats])
                global_max_abs = float(np.max(all_abs))
                clip_max = float(np.percentile(all_abs, 99.9))
                if clip_max < 1e-12:
                    clip_max = global_max_abs
                global_scale = clip_max / self.max_q if global_max_abs > 1e-12 else 1.0
            else:
                global_scale = 1.0

        for name in sorted(packed_update.keys()):
            param = packed_update[name]
            flat = param.detach().cpu().numpy().flatten()
            shapes[name] = list(param.shape)
            offsets[name] = (offset, param.numel())

            if self.use_global_scale:
                scale = global_scale
            else:
                # 逐层 scale：仍做 99.9 百分位裁剪，避免单个离群点毁掉整层精度
                _, scale = self._quantize(flat)
            layer_scales[name] = scale

            uvals, _ = self._quantize(flat, scale=scale)
            all_values.extend(uvals.tolist())
            offset += param.numel()

        total_elements = len(all_values)

        # 2) 每 slots2 个值一组，bit-shift 编码为单个整数，再转为 float
        values_per_chunk = self.slot_count * self.slots2
        chunks = []

        for i in range(0, total_elements, values_per_chunk):
            group = all_values[i : i + values_per_chunk]
            # padding 到 values_per_chunk 的整数倍
            while len(group) % self.slots2 != 0:
                group.append(0)
            # 每 slots2 个值编码为 1 个 float
            encoded = []
            for j in range(0, len(group), self.slots2):
                x = self._encode_group(group[j : j + self.slots2])
                encoded.append(float(x))
            # padding 到 slot_count
            chunk = np.array(encoded, dtype=np.float64)
            chunk = self._pad_chunk(chunk)
            chunks.append(chunk)

        metadata = PackingMetadata(
            self.name,
            {
                "shapes": shapes,
                "offsets": offsets,
                "total_elements": total_elements,
                "layer_scales": layer_scales,
                "slots2": self.slots2,
                "quant_bits": self.quant_bits,
                "pad_bits": self.pad_bits,
                "bn_buffers": bn_buffers,
            },
        )
        return chunks, metadata

    def create_zero_chunk(self) -> np.ndarray:
        """ESAFL 零值 chunk：量化空间中浮点 0 对应无符号值 max_q。"""
        zero_uvals = [int(self.max_q)] * self.slots2
        zero_encoded = self._encode_group(zero_uvals)
        return np.full(self.slot_count, float(zero_encoded), dtype=np.float64)

    def unpack(self, decrypted_chunks: List[np.ndarray], metadata: PackingMetadata) -> Dict[str, torch.Tensor]:
        data = metadata.data
        shapes = data["shapes"]
        offsets = data["offsets"]
        total_elements = data["total_elements"]
        layer_scales = data["layer_scales"]
        slots2 = data.get("slots2", self.slots2)
        quant_bits = data.get("quant_bits", self.quant_bits)
        pad_bits = data.get("pad_bits", self.pad_bits)
        bits_per_value = quant_bits + pad_bits
        max_q = float(2 ** (quant_bits - 1) - 1)
        pack_mask = (1 << quant_bits) - 1

        # 1) 从 chunks 中提取编码值并解码
        all_uvals = []
        for chunk in decrypted_chunks:
            for val in chunk[: self.slot_count]:
                if len(all_uvals) >= total_elements:
                    break
                if not np.isfinite(val):
                    logger.warning(f"[PACK-DEBUG] unpack received non-finite val={val}")
                elif abs(float(val) - 8388608.0) < 1.0:
                    logger.warning(f"[PACK-DEBUG] unpack detected TenSEAL NaN artifact (val={val})")
                x = int(round(float(val)))
                decoded = self._decode_group(x)
                for uval in decoded[:slots2]:
                    if len(all_uvals) >= total_elements:
                        break
                    if uval < 0 or uval > 2 * max_q:
                        logger.warning(
                            f"[PACK-DEBUG] decoded uval={uval} out of range [0, {2*max_q}] (x={x})"
                        )
                    all_uvals.append(uval)

        all_uvals = np.array(all_uvals[:total_elements], dtype=np.float64)

        # 2) 按层反量化恢复浮点值（非 BN 参数）
        result = {}
        for name in sorted(shapes.keys()):
            off, numel = offsets[name]
            shape = shapes[name]
            scale = layer_scales[name]
            uvals = all_uvals[off : off + numel]
            q = uvals - max_q  # 映射回有符号
            result[name] = torch.tensor((q * scale).reshape(shape))

        # 3) 恢复 BatchNorm running statistics（以明文保存在 metadata 中）
        bn_buffers = data.get("bn_buffers", {})
        for name, arr in bn_buffers.items():
            result[name] = torch.tensor(arr).clone()
        return result


class ESHEEPPacking:
    """
    ESAFL 论文 §V-B2 EP（Messages Encoding and Polynomials Packing）机制复现。

    仅 PUREPY 模式使用（密文域求和聚合）。与项目自研 ESAFLPacking（53-bit
    double 位域）不同，本类严格按论文公式实现：

      EP.Setup(PP, log q0, N) → (T, pad)：
        pad = ⌈log N⌉ + 1                    （论文下界，防同态加法进位串位）
        T   = ⌊log p / (log q0 + pad)⌋      （每系数 slot 数）

      EP.EcdPack：量化值 u ∈ [0, 2^logq0 − 1]（对称量化 + max_q 偏移，与论文
        [⌊p·φ⁻¹(z)⌉]_{q0} 的 mod-q0 位域同构；论文用 CKKS 典范嵌入 φ 编码，
        这里直接用整数系数——对加法同态求和二者等价，本实现精确且无 FFT 误差）。
        每个系数 β_j 的位布局（论文 Eq. 9，slot 1 在最高位）：
          第 i 个 slot（i ∈ [1, T−1]）存放 u_{i,j}，占 (pad + log q0) bit，
          第 T 个 slot 为零多项式 ϑ（进位余量，论文 Eq. 8-9）。
        β_j = Σ_{i=1}^{T−1} u_{i,j} · 2^{(T−i)(pad+logq0)} < 2^{T(pad+logq0)} ≤ p

      EP.Eval：密文逐系数求和。由 pad 的选取，slot 内和 Σu < N·2^logq0
        < 2^{logq0+pad} 不溢出本 slot 位域，因此 Σβ_j < 2^{T(pad+logq0)} ≤ p，
        mod p 解密不破坏位域（论文 §V-B2 / Eq. 12）。

      EP.DcdUnpk（本实现为 unpack_average）：移位截取各 slot（论文 Eq. 10），
        减 N·max_q 还原有符号量化值和，除以 N 得平均，再反量化。

    注意：论文 Fig. 1 说明一个明文打包 (T−1)×n 个实数（T−1 个数据 slot +
    1 个零多项式 slot），即每系数实际数据容量为 (T−1) 个值。
    """

    def __init__(self, n: int, logq0: int, logp: int, num_clients: int,
                 quant_clip: float = None):
        """
        Args:
            n:           环维度（= 每密文系数个数 / CKKS slot_count）
            logq0:       消息量化位宽（对应 packing.quant_bits 配置键）
            logp:        明文模数 p = 2^logp（esafl.logp）
            num_clients: 客户端总数 N（决定 pad 与聚合进位上界）
            quant_clip:  固定量化裁剪值（所有客户端共享，保证 EP 密文求和
                         语义正确：scale = quant_clip / max_q）。
                         为 None 时退化为逐 pack 的 99.9 百分位自适应 scale
                         （仅适用于 num_sum=1 的单密文解包，如全局状态）；
                         密文域求和聚合时必须在配置中提供 quant_clip。
        """
        self.n = int(n)
        self.logq0 = int(logq0)
        self.logp = int(logp)
        self.N = int(num_clients)
        self.quant_clip = quant_clip
        if self.N < 1:
            raise ValueError("num_clients 必须 ≥ 1")
        self.max_q = (1 << (self.logq0 - 1)) - 1
        # 论文 EP.Setup：pad ≥ ⌈log N⌉ + 1
        self.pad = (self.N - 1).bit_length() + 1
        self.slot_bits = self.pad + self.logq0
        # 论文 EP.Setup：T ≤ ⌊log p / (log q0 + pad)⌋
        self.T = self.logp // self.slot_bits
        if self.T < 2:
            raise ValueError(
                f"EP 参数无效：logp={logp} 过小而 logq0+pad={self.slot_bits}，"
                f"T={self.T} < 2（至少需要 1 个数据 slot + 1 个零 slot）。"
                f"请提高 esafl.logp 或降低 packing.quant_bits / 客户端数"
            )
        self.data_slots = self.T - 1  # 论文：T−1 个数据多项式 + 1 个零多项式
        # 论文进位安全校验：N·(2^logq0 − 1) < 2^(logq0+pad)
        assert (self.N * ((1 << self.logq0) - 1)) < (1 << (self.logq0 + self.pad))
        self.values_per_chunk = self.n * self.data_slots
        self.slot_mask = (1 << self.slot_bits) - 1
        logger.info(
            f"ESHEEPPacking 初始化: n={n}, logq0={logq0}, logp={logp}, N={self.N} | "
            f"pad={self.pad}, T={self.T} (数据 slot {self.data_slots}), "
            f"slot_bits={self.slot_bits}, 单密文容量={self.values_per_chunk} 值"
        )

    @property
    def name(self) -> str:
        return f"eshe_ep_q{self.logq0}_p{self.logp}_N{self.N}"

    # ---------------- EP.EcdPack ----------------
    def pack(self, model_update: Dict[str, torch.Tensor],
             fixed_scale: float = None) -> Tuple[List[np.ndarray], PackingMetadata]:
        """
        量化 + 位域打包。

        Args:
            fixed_scale: 显式指定的量化 scale（客户端更新应使用统一的
                         quant_clip/max_q，保证密文求和语义正确）。
                         None 时用 quant_clip 或 99.9 百分位自适应估计
                         （后者仅适合 num_sum=1 的单密文解包，如全局状态）。

        Returns:
            chunks: List[np.ndarray[int64]]，每个长度 n，系数 β_j < p
            metadata: PackingMetadata（含 shapes/offsets/layer_scales/BN 明文）
        """
        # BatchNorm running statistics 量化敏感，按 ESAFLPacking 惯例明文保存在 metadata
        bn_buffers = {}
        packed_update = {}
        for name, param in model_update.items():
            if any(k in name for k in ("running_mean", "running_var", "num_batches_tracked")):
                bn_buffers[name] = param.detach().cpu().numpy().copy()
            else:
                packed_update[name] = param

        # 量化 scale = clip / max_q。EP 密文求和的正确性前提是所有客户端
        # 共享同一 clip（配置 packing.quant_clip）；否则仅 num_sum=1 场景有意义。
        clip_val = None
        if fixed_scale is not None:
            clip_val = float(fixed_scale)
        elif self.quant_clip is not None:
            clip_val = float(self.quant_clip)
        else:
            logger.warning(
                "ESHEEPPacking: 未配置 quant_clip，使用逐 pack 自适应 scale；"
                "EP 密文求和聚合要求所有客户端共享 scale，请配置 packing.quant_clip"
            )
            all_flats = [p.detach().cpu().numpy().flatten() for p in packed_update.values()]
            if all_flats:
                all_abs = np.concatenate([np.abs(f) for f in all_flats])
                global_max_abs = float(np.max(all_abs))
                clip_max = float(np.percentile(all_abs, 99.9))
                clip_val = clip_max if clip_max >= 1e-12 else global_max_abs
        global_scale = clip_val / self.max_q if clip_val and clip_val > 1e-12 else 1.0

        all_values = []
        shapes = {}
        offsets = {}
        layer_scales = {}
        offset = 0
        for name in sorted(packed_update.keys()):
            param = packed_update[name]
            flat = param.detach().cpu().numpy().flatten()
            shapes[name] = list(param.shape)
            offsets[name] = (offset, param.numel())
            layer_scales[name] = global_scale
            clipped = np.clip(flat, -global_scale * self.max_q,
                              global_scale * self.max_q)
            q = np.round(clipped / global_scale).astype(np.int64)
            q = np.clip(q, -self.max_q, self.max_q)
            all_values.extend((q + self.max_q).tolist())  # 无符号 u ∈ [0, 2^logq0−1]
            offset += param.numel()

        total_elements = len(all_values)
        vpc = self.values_per_chunk
        chunks = []
        for i in range(0, total_elements, vpc):
            group = all_values[i:i + vpc]
            # padding 零值（编码空间 0 对应 u=max_q，即量化 0）
            group.extend([self.max_q] * (vpc - len(group)))
            beta = np.zeros(self.n, dtype=np.int64)
            # 第 i 个数据 slot 占值区间 [(i-1)n, i·n)，置于位 (T-i)·slot_bits（论文 Eq.9）
            for s in range(self.data_slots):
                slot_vals = np.array(group[s * self.n:(s + 1) * self.n], dtype=np.int64)
                beta |= slot_vals << ((self.T - 1 - s) * self.slot_bits)
            chunks.append(beta)

        metadata = PackingMetadata(self.name, {
            "shapes": shapes,
            "offsets": offsets,
            "total_elements": total_elements,
            "layer_scales": layer_scales,
            "quant_bits": self.logq0,
            "logp": self.logp,
            "pad": self.pad,
            "slot_bits": self.slot_bits,
            "T": self.T,
            "data_slots": self.data_slots,
            "num_clients": self.N,
            "bn_buffers": bn_buffers,
        })
        return chunks, metadata

    # ---------------- EP.DcdUnpk（聚合平均版）----------------
    def unpack_average(self, summed_chunks: List[np.ndarray],
                       metadata: PackingMetadata,
                       num_sum: int,
                       zero_point: float = None) -> Dict[str, torch.Tensor]:
        """
        从"密文求和并解密"后的系数恢复聚合平均明文。

        Args:
            summed_chunks: 求和密文解密后的整数系数（每 slot 内为 N 个客户端
                           编码值的整数和，< 2^(logq0+pad)，位域无串位）
            metadata:      pack() 产出的元数据
            num_sum:       参与求和的客户端数 N（论文 Eval 后除 N 得平均）
            zero_point:    无符号编码偏移（默认 num_sum·max_q）。密文差分
                           （delta = ct_b − ct_a）的明文是编码值之差，不含
                           偏移，应传 0。
        """
        data = metadata.data
        shapes = data["shapes"]
        offsets = data["offsets"]
        total_elements = data["total_elements"]
        layer_scales = data["layer_scales"]
        T = data.get("T", self.T)
        slot_bits = data.get("slot_bits", self.slot_bits)
        slot_mask = (1 << slot_bits) - 1
        max_q = float((1 << (data.get("quant_bits", self.logq0) - 1)) - 1)

        # 按 slot 提取整数和（论文 Eq.10 的移位截取），展平为值序列
        all_sums = []
        for chunk in summed_chunks:
            beta = np.asarray(chunk[:self.n], dtype=np.int64)
            for s in range(T - 1):
                shift = (T - 1 - s) * slot_bits
                slot = (beta >> shift) & slot_mask
                all_sums.extend(slot.tolist())
        all_sums = np.array(all_sums[:total_elements], dtype=np.float64)

        # 减无符号偏移（默认 N·max_q）→ 有符号量化值和 → 除 N 平均 → 反量化
        if zero_point is None:
            zero_point = num_sum * max_q
        q_avg = (all_sums - zero_point) / float(num_sum)
        result = {}
        for name in sorted(shapes.keys()):
            off, numel = offsets[name]
            shape = shapes[name]
            result[name] = torch.tensor(
                (q_avg[off:off + numel] * layer_scales[name]).reshape(shape))

        for name, arr in data.get("bn_buffers", {}).items():
            result[name] = torch.tensor(arr).clone()
        return result

    def unpack(self, decrypted_chunks: List[np.ndarray],
               metadata: PackingMetadata) -> Dict[str, torch.Tensor]:
        """单密文（num_sum=1）解包，用于全局状态解密等场景。"""
        return self.unpack_average(decrypted_chunks, metadata, num_sum=1)

    def create_zero_chunk(self) -> np.ndarray:
        """编码空间的零值 chunk：每 slot u=max_q → β = max_q · Σ 2^{(T-i)slot_bits}"""
        beta = np.zeros(self.n, dtype=np.int64)
        for s in range(self.data_slots):
            beta |= np.int64(self.max_q) << ((self.T - 1 - s) * self.slot_bits)
        return beta

    def get_values_per_chunk(self) -> int:
        return self.values_per_chunk


def create_packing_strategy(config: Dict, slot_count: int) -> PackingStrategy:
    """根据配置创建打包策略"""
    global _CONJUGATE_SUPPORTED
    packing_config = config.get("packing", {})
    strategy_name = packing_config.get("strategy", "layerwise")

    if strategy_name == "layerwise":
        return LayerwisePacking(slot_count)
    elif strategy_name == "merged":
        return MergedPacking(slot_count)
    elif strategy_name == "conjugate":
        if _CONJUGATE_SUPPORTED is None:
            _CONJUGATE_SUPPORTED = _check_conjugate_support()
        if not _CONJUGATE_SUPPORTED:
            logger.warning(
                "当前 TenSEAL 版本不支持复数编码，conjugate 策略回退到 merged"
            )
            return MergedPacking(slot_count)
        return ConjugatePacking(slot_count)
    elif strategy_name == "twotier":
        quant_bits = packing_config.get("quant_bits", 16)
        logger.info(f"TwoTierPacking 初始化: quant_bits={quant_bits}, slot_count={slot_count}")
        return TwoTierPacking(slot_count, quant_bits=quant_bits)
    elif strategy_name == "layerwise_quantized":
        quant_bits = packing_config.get("quant_bits", 16)
        logger.info(f"LayerwiseQuantizedPacking 初始化: quant_bits={quant_bits}, slot_count={slot_count}")
        return LayerwiseQuantizedPacking(slot_count, quant_bits=quant_bits)
    elif strategy_name == "crtstack":
        layers = packing_config.get("crt_layers", 4)
        quant_bits = packing_config.get("crt_quant_bits", 8)
        moduli = packing_config.get("crt_moduli", None)
        logger.info(f"CRTStackPacking 初始化: layers={layers}, quant_bits={quant_bits}, slot_count={slot_count}")
        return CRTStackPacking(slot_count, layers=layers, quant_bits=quant_bits, moduli=moduli)
    elif strategy_name == "esafl":
        slots2 = packing_config.get("slots2", 4)
        quant_bits = packing_config.get("quant_bits", 8)
        # 兼容配置中 logq0 与 quant_bits 同义的情况
        if "logq0" in packing_config and quant_bits == 8:
            quant_bits = packing_config.get("logq0", 8)
        pad_bits = packing_config.get("pad_bits", 0)
        use_global_scale = packing_config.get("use_global_scale", True)
        logger.info(
            f"ESAFLPacking 初始化: slots2={slots2}, quant_bits={quant_bits}, "
            f"pad_bits={pad_bits}, use_global_scale={use_global_scale}, slot_count={slot_count}"
        )
        return ESAFLPacking(
            slot_count, slots2=slots2, quant_bits=quant_bits,
            pad_bits=pad_bits, use_global_scale=use_global_scale
        )
    else:
        logger.warning(f"未知打包策略 '{strategy_name}'，使用默认逐层打包")
        return LayerwisePacking(slot_count)
