# ECPFL\-Lite公式推导

### 一、 极简终极版（`ECPFL-Lite`）完整五阶段闭环公式推导

#### 1\. Phase 0：极简离线初始化（仅 2 次 NTT，耗时 $0.32\text{ s}$，单客户端存储 $192\text{ KB}$）

- **全局密钥与种子生成**：KGC 采样全局聚合解密密钥 $S \leftarrow \mathcal{U}(\mathcal{R}_q)$、公共锚点种子 $\sigma_a \leftarrow \{0,1\}^\lambda$（公开）以及客户端群组盲化种子 $\sigma_b \leftarrow \{0,1\}^\lambda$（**对服务器严格保密**）。

- **双多项式分片（**$\mathrm{SS.ShareGen}(S, \tau)$**）**：KGC 在 $\mathcal{R}_q[x]$ 上仅采样 **1 个 **$\tau$** 阶全局密钥共享多项式** $F_S(x)$（满足 $F_S(0) = S$）和 **1 个 **$(\tau-1)$** 阶零共享多项式** $Z(x)$（满足 $Z(0) = 0$）：
$F_S(x) = S + \sum_{m=1}^{\tau} f_{S,m} \cdot x^m \in \mathcal{R}_q[x], \qquad Z(x) = 0 + \sum_{m=1}^{\tau-1} u_m \cdot x^m \in \mathcal{R}_q[x],$
并在客户端公开标量点 $\alpha_i = i \in \mathbb{Z}_q^*$ 处求值（全过程仅需 **2 次多项式求值 = **$0.32\text{ s}$）：
$S_i = F_S(\alpha_i) \in \mathcal{R}_q, \qquad z_i = Z(\alpha_i) \in \mathcal{R}_q, \qquad \forall i \in [N].$

- **常数级分发与永久离线**：KGC 向每个客户端 $i \in [N]$ 仅发送 **3 个环元素与 2 个种子**：
$\mathcal{K}_i^{\text{Lite}} = \bigl(\, S,\; S_i,\; z_i,\; \sigma_a,\; \sigma_b \,\bigr) \quad \text{（仅 } 3 \times 64\text{ KB} = 192\text{ KB，全网总下行仅 } 192\text{ MB} \text{）},$
随后 KGC 永久离线。对于任意规模 $|\mathcal{A}| \ge \tau + 1$ 的客户端子集 $\mathcal{A} \subseteq \mathcal{C}$，其零点拉格朗日系数 $\lambda_i^{\mathcal{A}} = \prod_{u \in \mathcal{A} \setminus \{i\}} \alpha_u (\alpha_u - \alpha_i)^{-1} \bmod q$ 恒满足：
$\Biggl[\sum_{i \in \mathcal{A}} \lambda_i^{\mathcal{A}} \cdot S_i\Biggr]_q = F_S(0) = S, \qquad \Biggl[\sum_{i \in \mathcal{A}} \lambda_i^{\mathcal{A}} \cdot z_i\Biggr]_q = Z(0) = 0.$

#### 2\. Phase 1：包级稀疏共识安全投票（`ESP-Vote` \& `ESP-Tally`）

- 活跃客户端 $i \in \mathcal{S}^{(t)}$（$|\mathcal{S}^{(t)}| \ge \tau + 1$）将二值投票向量嵌入多项式 $v_i^{(t)}(X) = \sum_{j=1}^J v_{i,j}^{(t)} X^{j-1}$，用 $a_0^{(t)} = \mathrm{HE.PRPG}(\sigma_a, t \parallel 0)$ 和零份额 $z_i$ 盲化上传：
$\hat{v}_i^{(t)} = \bigl[\, a_0^{(t)} \cdot \lambda_i^{(t)} z_i + \tilde{p} \cdot e_{i,0}^{(t)} + v_i^{(t)}(X) \,\bigr]_q \in \mathcal{R}_q.$

- 服务器对 $i \in \mathcal{S}^{(t)}$ 求和并模 $p$，因 $a_0^{(t)} \sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} z_i = 0$ 且 $\tilde{p} E_0^{(t)} \bmod p = 0$，精确恢复全局得票多项式 $V^{(t)}(X) = \bigl[\bigl[\sum_{i \in \mathcal{S}^{(t)}} \hat{v}_i^{(t)}\bigr]_q\bigr]_p = \sum_{j=1}^J \nu_j^{(t)} X^{j-1}$ 并广播入选包集合 $\mathcal{K}^{(t)}$。

#### 3\. Phase 2：单密文稀疏包加密上传（`ESP-Enc`）

- 对每个入选包 $j \in \mathcal{K}^{(t)}$，客户端 $i \in \mathcal{S}^{(t)}$ 由 $\sigma_a$ 生成公共锚点 $a_j^{(t)} = \mathrm{HE.PRPG}(\sigma_a, t \parallel j)$，由保密群组种子 $\sigma_b$ 生成包专属盲化乘子 $b_j^{(t)} = \mathrm{HE.PRPG}(\sigma_b, t \parallel j \parallel 0)$，直接计算有效密钥（仅 1 次环乘加，复杂度 $\mathcal{O}(n)$）：
$\tilde{s}_{i,j}^{(t)} = \Phi_i\bigl(\mathcal{S}^{(t)}, b_j^{(t)}\bigr) = \Bigl[\, \lambda_i^{(t)} \bigl(S_i + b_j^{(t)} z_i\bigr) \,\Bigr]_q \in \mathcal{R}_q.$

- 客户端 $i$ 对编码明文 $\mathrm{pt}_{i,j}^{(t)} = \mathrm{Ecd}(\omega_i^{(t)} \mathbf{x}_{i,j}^{(t)}, \Delta)$ 执行单密文 RLWE 加密，并将所有入选包密文 $\{\mathrm{ct}_{i,j}^{(t)}\}_{j \in \mathcal{K}^{(t)}}$ 原子化打包上传：
$\mathrm{ct}_{i,j}^{(t)} = \mathrm{HE.Enc}\bigl(a_j^{(t)}, \tilde{s}_{i,j}^{(t)}, \mathrm{pt}_{i,j}^{(t)}\bigr) = \bigl[\, a_j^{(t)} \cdot \tilde{s}_{i,j}^{(t)} + \tilde{p} \cdot e_{i,j}^{(t)} + \mathrm{pt}_{i,j}^{(t)} \,\bigr]_q \in \mathcal{R}_q.$

#### 4\. Phase 3：全局同态聚合与一步差值掉线补偿（`ESP-Comp` \& `ESP-Agg`）

设完成 Phase 2 原子化上传的存活客户端集为 $\widehat{\mathcal{S}}^{(t)} \subseteq \mathcal{S}^{(t)}$（$|\widehat{\mathcal{S}}^{(t)}| \ge \tau + 1$，掉线集 $\mathcal{D}^{(t)} = \mathcal{S}^{(t)} \setminus \widehat{\mathcal{S}}^{(t)}$ 满足 $|\mathcal{D}^{(t)}| = 0$ 或 $|\mathcal{D}^{(t)}| \ge 2$）：

- **情况 A：同步无掉线（**$\mathcal{D}^{(t)} = \emptyset \implies \widehat{\mathcal{S}}^{(t)} = \mathcal{S}^{(t)}$**，零额外通信）**
服务器直接将收到的密文相加，一行推导闭环：
$\begin{aligned}C_j^{(t)} &= \Biggl[\sum_{i \in \mathcal{S}^{(t)}} \mathrm{ct}_{i,j}^{(t)}\Biggr]_q = \Biggl[\, a_j^{(t)} \Bigl(\underbrace{\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} S_i}_{= S} + b_j^{(t)} \underbrace{\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} z_i}_{= 0}\Bigr) + \tilde{p} \sum_{i \in \mathcal{S}^{(t)}} e_{i,j}^{(t)} + \sum_{i \in \mathcal{S}^{(t)}} \mathrm{pt}_{i,j}^{(t)} \,\Biggr]_q \\&= \bigl[\, a_j^{(t)} \cdot S + \tilde{p} \cdot E_j^{(t)} + \mathrm{pt}_j^{(t)} \,\bigr]_q.\end{aligned}$

- **情况 B：异步掉线补偿（**$|\mathcal{D}^{(t)}| \ge 2 \implies \widehat{\mathcal{S}}^{(t)} \subset \mathcal{S}^{(t)}$**）**

    1. **存活客户端生成差值补偿密文**：每个存活客户端 $i \in \widehat{\mathcal{S}}^{(t)}$ 计算存活集拉格朗日系数 $\widehat{\lambda}_i^{(t)}$ 与新鲜盲化乘子 $\hat{b}_j^{(t)} = \mathrm{HE.PRPG}(\sigma_b, t \parallel j \parallel 1)$，得到存活集目标有效密钥 $\widehat{s}_{i,j}^{(t)} = \Phi_i(\widehat{\mathcal{S}}^{(t)}, \hat{b}_j^{(t)}) = \bigl[\widehat{\lambda}_i^{(t)}(S_i + \hat{b}_j^{(t)} z_i)\bigr]_q$，并上传新旧有效密钥之差的加密补偿项 $\delta_{i,j}^{(t)}$：
    $\begin{aligned}\kappa_{i,j}^{(t)} &= \bigl[\, \widehat{s}_{i,j}^{(t)} - \tilde{s}_{i,j}^{(t)} \,\bigr]_q = \Bigl[\, (\widehat{\lambda}_i^{(t)} - \lambda_i^{(t)}) S_i + \bigl(\widehat{\lambda}_i^{(t)} \hat{b}_j^{(t)} - \lambda_i^{(t)} b_j^{(t)}\bigr) z_i \,\Bigr]_q, \\\delta_{i,j}^{(t)} &= \bigl[\, a_j^{(t)} \cdot \kappa_{i,j}^{(t)} + \tilde{p} \cdot \hat{e}_{i,j}^{(t)} \,\bigr]_q \in \mathcal{R}_q.\end{aligned}$

    2. **服务器端闭环聚合推导（单客户端级直接对消，零集合差运算）**：
    服务器将存活客户端的原密文与补偿密文相加：
    $\begin{aligned}C_j^{(t)} &= \Biggl[\sum_{i \in \widehat{\mathcal{S}}^{(t)}} \bigl(\mathrm{ct}_{i,j}^{(t)} + \delta_{i,j}^{(t)}\bigr)\Biggr]_q \\&= \Biggl[\, a_j^{(t)} \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \bigl(\tilde{s}_{i,j}^{(t)} + \widehat{s}_{i,j}^{(t)} - \tilde{s}_{i,j}^{(t)}\bigr) + \tilde{p} \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \bigl(e_{i,j}^{(t)} + \hat{e}_{i,j}^{(t)}\bigr) + \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \mathrm{pt}_{i,j}^{(t)} \,\Biggr]_q \\&= \Biggl[\, a_j^{(t)} \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \widehat{\lambda}_i^{(t)}\bigl(S_i + \hat{b}_j^{(t)} z_i\bigr) + \tilde{p} \cdot \widehat{E}_j^{(t)} + \mathrm{pt}_j^{(t)} \,\Biggr]_q \\&= \Biggl[\, a_j^{(t)} \Bigl(\underbrace{\sum_{i \in \widehat{\mathcal{S}}^{(t)}} \widehat{\lambda}_i^{(t)} S_i}_{= S} + \hat{b}_j^{(t)} \underbrace{\sum_{i \in \widehat{\mathcal{S}}^{(t)}} \widehat{\lambda}_i^{(t)} z_i}_{= 0}\Bigr) + \tilde{p} \cdot \widehat{E}_j^{(t)} + \mathrm{pt}_j^{(t)} \,\Biggr]_q \\&= \bigl[\, a_j^{(t)} \cdot S + \tilde{p} \cdot \widehat{E}_j^{(t)} + \mathrm{pt}_j^{(t)} \,\bigr]_q.\end{aligned}$

#### 5\. Phase 4：跨轮次密文预取与一步本地解密（`ECP-Fetch` \& `ECP-Sync`，无二轮解密份额传输）

- 预采样客户端 $i \in \mathcal{P}^{(t^*)}$ 在后台空闲期异步拉取缺失轮次 $r \in \mathcal{H}_{i,j}$ 的聚合包密文 $C_j^{(r)}$，在本地环 $\mathcal{R}_q$ 上累加为单条预取密文：
$C_{\mathrm{pre},j} = \Biggl[\sum_{r \in \mathcal{H}_{i,j}} C_j^{(r)}\Biggr]_q = \bigl[\, A_{\mathrm{pre},j} \cdot S + \tilde{p} \cdot E_{\mathrm{pre},j} + \mathrm{pt}_{\mathrm{pre},j} \,\bigr]_q, \quad \text{其中 } A_{\mathrm{pre},j} = \Biggl[\sum_{r \in \mathcal{H}_{i,j}} a_j^{(r)}\Biggr]_q.$

- 重返训练时，客户端直接用本地持有的 $S$ 执行 **1 次环乘与双模约减（无需向服务器上传或广播任何解密份额！）**，一步恢复出跨轮累积梯度明文：
$\mathrm{HE.Dec}\bigl(A_{\mathrm{pre},j}, S, C_{\mathrm{pre},j}\bigr) = \bigl[\bigl[\, C_{\mathrm{pre},j} - A_{\mathrm{pre},j} \cdot S \,\bigr]_q\bigr]_p = \mathrm{pt}_{\mathrm{pre},j}.$

---

# 问题答疑

### 最终每个客户端到底持有哪些密钥信息？还要持有 $s_i$ 吗？

**不需要再持有 **$s_i$**！** 在 **ECPFL\-Lite** 中，每个客户端 $i$ 手里**只持有 3 个环元素**（外加 2 个 128\-bit 伪随机种子 $\sigma_a, \sigma_b$）：



1. **全局聚合解密密钥 **$S \in \mathcal{R}_q$：仅用于下载聚合密文后进行**本地一步解密**（减去 $a_j^{(t)} S$）。



1. **聚合密钥的 Shamir 份额 **$S_i = F_S(\alpha_i) \in \mathcal{R}_q$：其中 $F_S(0) = S$，用来替代原来的个体加密密钥 $s_i$。



1. **零共享（Zero\-Sharing）份额 **$z_i = Z(\alpha_i) \in \mathcal{R}_q$：其中 $Z(0) = 0$，用来给每个包的加密密钥加一层“聚合后自动归零”的随机掩码。



> **为什么不再需要个体密钥 **$s_i$**？**
> 
> 在原方案中，$S = \sum_{k=1}^N s_k$，因为每轮只抽样部分客户端 $\mathcal{S}^{(t)}$ 参与，未参与客户端的 $s_k$ 缺失，所以才需要用其他人的份额去补齐缺失的 $s_k$。而在 **ECPFL\-Lite** 中，KGC 直接把总密钥 $S$ 切分成 Shamir 份额 $S_i = F_S(\alpha_i)$——只要任意 $\vert{}\mathcal{S}^{(t)}\vert{} \ge \tau$ 个客户端按拉格朗日系数加权求和 $\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} S_i$，就能直接凑出完整的 $S$！因此个体密钥 $s_i$ 彻底失去存在的必要，客户端只需存 $(S, S_i, z_i)$ 这 3 个环元素（共 $3 \times 64~\mathrm{KB} = 0.19~\mathrm{MB}$）。
> 
> 
> 
> 

### 此时加密密钥变成 $S$ 的份额 $S_i$ 了吗？为什么还要构造 $\tilde{s}_{i,j}^{(t)}$ 加密，而不能直接拿 $S_i$（或 $\lambda_i^{(t)} S_i$）加密？

是的，客户端的底层秘密从 $s_i$ 变成了 $S_i$，但**绝对不能直接用 **$S_i$** 或 **$\lambda_i^{(t)} S_i$** 去加密多个包（Pack）**，必须构造逐包变化的等效加密密钥：



$\tilde{s}_{i,j}^{(t)} = \Bigl[\lambda_i^{(t)} \bigl(S_i + b_j^{(t)} z_i\bigr)\Bigr]_q$

原因有两个：



- **为什么要乘 **$\lambda_i^{(t)}$**？** 因为服务器只会把收到的密文直接相加（$\sum_{i \in \mathcal{S}^{(t)}} \mathrm{ct}_{i,j}^{(t)}$）。如果不乘拉格朗日系数 $\lambda_i^{(t)}$，服务器加出来的密钥项是 $\sum S_i$（毫无意义的随机值，不等于 $S$）；只有乘了 $\lambda_i^{(t)}$，服务器把密文直接相加时，密钥项才会自动满足拉格朗日插值 $\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} S_i = F_S(0) = S$。



- **为什么不能只用 **$\lambda_i^{(t)} S_i$**，而必须加上 **$b_j^{(t)} z_i$**？（防止跨包消元攻击）** 一个大模型会被切成 $J$ 个包（例如 CIFAR\-10 有 $J=67$ 个包）。如果在同一轮 $t$ 中，客户端对第 $j_1$ 个包和第 $j_2$ 个包都用同一个 $\lambda_i^{(t)} S_i$ 加密：



- $\mathrm{ct}_{i,j_1}^{(t)} = a_{j_1}^{(t)} (\lambda_i^{(t)} S_i) + \tilde{p} e_{i,j_1}^{(t)} + \mathrm{pt}_{i,j_1}^{(t)}, \qquad \mathrm{ct}_{i,j_2}^{(t)} = a_{j_2}^{(t)} (\lambda_i^{(t)} S_i) + \tilde{p} e_{i,j_2}^{(t)} + \mathrm{pt}_{i,j_2}^{(t)}$

- 注意：**其他合谋客户端知道公共多项式 **$a_{j_1}^{(t)}, a_{j_2}^{(t)}$（因为它们也有种子 $\sigma_a$）！合谋客户端只需计算交叉相消：



- $a_{j_2}^{(t)} \cdot \mathrm{ct}_{i,j_1}^{(t)} - a_{j_1}^{(t)} \cdot \mathrm{ct}_{i,j_2}^{(t)}$

- 就能把未知的秘密项 $a_{j_1}^{(t)} a_{j_2}^{(t)} \lambda_i^{(t)} S_i$ **彻底抵消为 0**，从而直接暴露客户端 $i$ 的明文关系！同理，跨轮次（round $t_1, t_2$）也能把 $S_i$ 解出来。 而加上 $b_j^{(t)} z_i$ 后，因为每个包 $j$ 的 $b_j^{(t)} = \mathrm{HE.PRPG}(\sigma_b, 0 \parallel t \parallel j)$ 都不一样，每个包等效使用的是一个**完全不同的随机化密钥** $\tilde{s}_{i,j}^{(t)}$，合谋客户端面对 $J$ 个方程却有 2 个未知秘密环元素 $(S_i, z_i)$，交叉相消后 $z_i$ 项依然消不掉，彻底堵死了跨包/跨轮消元漏洞。



### 拉格朗日系数 $\lambda_i^{(t)}$ 是需要集合确定才能乘的吗？如果上传密文之后有人掉线（集合才最终确定），为什么上传前就能乘 $\lambda_i^{(t)}$，且为什么要加 $b_j^{(t)} z_i$？

这正是本协议两阶段集合（Phase 1 确认集 $\mathcal{S}^{(t)}$ vs\. Phase 2 存活集 $\widehat{\mathcal{S}}^{(t)}$）的设计精妙之处：



**上传密文前，已经有一个“已确认的投票在线集合” **$\mathcal{S}^{(t)}$： 在每轮开始时，服务器先让在线客户端完成轻量级投票（Phase 1），此时所有成功投票的客户端构成**已知集合 **$\mathcal{S}^{(t)}$（服务器已广播 $\mathcal{S}^{(t)}$）。因此，客户端在 Phase 2 加密上传模型包时，**先按这个已知集合 **$\mathcal{S}^{(t)}$** 计算拉格朗日系数 **$\lambda_i^{(t)}$，并乘进 $\tilde{s}_{i,j}^{(t)} = \lambda_i^{(t)}(S_i + b_j^{(t)} z_i)$ 里上传密文。



1. **情况一（大概率正常情况）：Phase 2 密文上传期间没有人新掉线（**$\widehat{\mathcal{S}}^{(t)} = \mathcal{S}^{(t)}$**）**： 此时预先乘好的 $\lambda_i^{(t)}$ 完全准确！服务器直接把收到的密文相加：



$\sum_{i \in \mathcal{S}^{(t)}} \tilde{s}_{i,j}^{(t)} = \underbrace{\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} S_i}_{=\,S} + b_j^{(t)} \underbrace{\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} z_i}_{=\,0} = S$

不需要任何第二轮通信，一步到位完成聚合！



2. **情况二（小概率异常情况）：Phase 2 上传大密文途中有人掉线了（存活集合变成 **$\widehat{\mathcal{S}}^{(t)} \subsetneq \mathcal{S}^{(t)}$**）**： 这时密文已经传上去了，里面乘的旧系数 $\lambda_i^{(t)}$ 无法凑出 $S$。服务器只需广播真正存活的集合 $\widehat{\mathcal{S}}^{(t)}$，存活客户端按新集合算出新系数 $\widehat{\lambda}_i^{(t)}$，并补发一个极小的差值补偿密文 $\delta_{i,j}^{(t)}$，其内部密钥差值为：



$\kappa_{i,j}^{(t)} = \bigl(\widehat{\lambda}_i^{(t)} - \lambda_i^{(t)}\bigr) S_i + \bigl(\widehat{\lambda}_i^{(t)} \hat{b}_j^{(t)} - \lambda_i^{(t)} b_j^{(t)}\bigr) z_i$

把原密文密钥 $\tilde{s}_{i,j}^{(t)}$ 和补偿密钥 $\kappa_{i,j}^{(t)}$ 一加，旧的 $\lambda_i^{(t)}$ 项正负完全抵消，直接变成新集合下的 $\widehat{\lambda}_i^{(t)}(S_i + \hat{b}_j^{(t)} z_i)$，对存活集合 $\widehat{\mathcal{S}}^{(t)}$ 求和再次精确等于 $S$！



### **为什么掉线补偿阶段更离不开 **$b_j^{(t)} z_i$** 和 **$\hat{b}_j^{(t)} z_i$**？** 

如果没有零共享掩码 $z_i$，那么原密文里用的是 $\lambda_i^{(t)} S_i$，掉线补偿密文里用的是 $(\widehat{\lambda}_i^{(t)} - \lambda_i^{(t)}) S_i$。因为 $\lambda_i^{(t)}$ 和 $\widehat{\lambda}_i^{(t)}$ 都是**公开标量**，攻击者只要把原密文和补偿密文按公开标量比例一减，就能消掉 $S_i$ 直接破译单客户端明文！而引入 $b_j^{(t)} z_i$（上传阶段）与 $\hat{b}_j^{(t)} z_i$（补偿阶段，$\hat{b}_j^{(t)} \neq b_j^{(t)}$）后，上传密钥与补偿密钥在 $(S_i, z_i)$ 上线性无关（行列式 $\lambda_i^{(t)}\widehat{\lambda}_i^{(t)}(\hat{b}_j^{(t)} - b_j^{(t)}) \neq 0$），攻击者既消不掉 $S_i$，也解不出 $S_i$ 和 $z_i$。



