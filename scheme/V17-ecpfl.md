# ECPFL 最新定稿版（V16 单密文结构）全流程方案、零跳步公式推导与全篇论文正文

> **文档说明**：
> 本文档基于最新修订定稿的**单环元素密文结构（Single-Ring-Element Ciphertext Structure）**及全部 12 项修改要求整理而成，包含三个核心部分：
> 1. **第一部分：全流程架构闭环与核心设计机制精讲**（涵盖五阶段实体交互闭环、抗 $\kappa \le \tau - 2$ 合谋门限、固定活跃集权重规则 $\omega_i^{(t)}$、$a_0^{(t)}$ 域分离机制、$b_j^{(t)}z_i$ 随包刷新掩码机制，以及为什么跨轮交叉相乘在 $\gcd(p, q)=1$ 下无法恢复个人投票位图）。
> 2. **第二部分：全篇核心公式“零跳步”逐行数学推导（Zero-Skip Step-by-Step Derivations）**（从基础一步加解密、同轮跨包差分漏洞、拉格朗日恒等式、Phase 1 投票掩码抵消、Phase 2/3 同步聚合、Phase 3 异步掉线补偿聚合，到 Phase 4 跨轮预取累加与一步解密，每一步代数变形均完整展开、绝不跳步）。
> 3. **第三部分：最新定稿版全篇论文英文正文 + 伪代码 + 表格 + 实验数据审计对照（Abstract 至 Section VII）**（与 `ECPFL_Clean_Submission.pdf` 完全同步）。

---

## 第一部分：全流程架构闭环与核心设计机制精讲

### 1.1 系统五阶段端到端闭环工作流（Phase 0 – Phase 4）

ECPFL 包含三类实体：**离线可信密钥生成中心（KGC）**、**半诚实中央服务器（Server）** 与 **$N$ 个异构边缘客户端（$\mathcal{C} = [N] = \{1, \dots, N\}$）**。在训练全过程中，**客户端之间无任何点对点（P2P）通信，也不需要上传任何解密份额**。

```
[Phase 0: 系统离线初始化 (仅执行一次)]
  KGC 采样独立加密私钥 s_i <- U(R_q)，计算全局聚合解密密钥 S = [\sum_{i=1}^N s_i]_q，生成伪随机种子 (\sigma_a, \sigma_b)；
  在常数评估点 \alpha_i = i \in [N] 上，利用 (\tau-1) 次多项式 F_k(x) (F_k(0)=s_k) 和 \Psi(x) (\Psi(0)=0) 生成份额 {s_{k,i}}_{k=1}^N 与零份额 z_i；
  KGC 通过安全信道向每个客户端 i 分发 (s_i, S, \sigma_a, \sigma_b, {s_{k,i}}_{k=1}^N, z_i)，随后立即擦除所有共享多项式并永久离线。

[第 t 轮联邦训练 (t = 1, 2, ..., T)]
  ├── 预采样与活跃集确认：
  │     服务器提前 R 轮预采样候选池 \mathcal{P}^{(t)} (大小 \lceil \beta K \rceil)；
  │     在第 t 轮开始时，K = |\mathcal{S}^{(t)}| \ge \tau 个在线响应客户端构成确认活跃集 \mathcal{S}^{(t)} \subseteq \mathcal{P}^{(t)}，
  │     未参训集合为 \bar{\mathcal{S}}^{(t)} = \mathcal{C} \setminus \mathcal{S}^{(t)}，固定聚合权重为 \omega_i^{(t)} = n_i / \sum_{u \in \mathcal{S}^{(t)}} n_u。
  │
  ├── Phase 4b (活跃客户端模型同步 ECP-Sync)：
  │     每个活跃客户端 i \in \mathcal{S}^{(t)} 补齐截至 t-1 轮未缓存的稀疏包密文，对本地缓存 \mathcal{L}_{i,j} 中的历史密文做模 q 同态累加，
  │     利用全局密钥 S 对每个非空包执行一次一步解密，更新本地模型 w_i <- w_i + \tilde{g}_{pre}。
  │
  ├── Phase 1 (包级稀疏共识安全投票 ESP-Vote & ESP-Tally)：
  │     1. 活跃客户端 i \in \mathcal{S}^{(t)} 本地训练 \mathcal{E} 轮得到 w_i^{(t)}，计算增量 \Delta w_i^{(t)} = w_i^{(t)} - w_i，
  │        加上未加权残差得到 x_i^{(t)} = \Delta w_i^{(t)} + r_i^{(t-1)}；
  │     2. 将 x_i^{(t)} 划分为 J = \lceil 2d/n \rceil 个包（每包 4096 个参数），按 \ell_2 范数选出 Top-\zeta 个包生成投票多项式 v_i^{(t)}(X)；
  │     3. 用 a_0^{(t)} = HE.PRPG(\sigma_b, t || 0) 加密上传掩码投票 \hat{v}_i^{(t)} = [a_0^{(t)} \lambda_i^{(t)} z_i + \tilde{p} e_{i,0}^{(t)} + v_i^{(t)}(X)]_q；
  │     4. 服务器对 i \in \mathcal{S}^{(t)} 求和并模 q、模 p，恢复得票数 \nu_j^{(t)}，按 UN / RK-\theta / TH-\theta 广播全局共识包集合 \mathcal{K}^{(t)}。
  │
  ├── Phase 2 (稀疏包加密上传与双衰减残差更新 ESP-Enc)：
  │     1. 客户端按固定权重缩放更新：\tilde{g}_i^{(t)} = \omega_i^{(t)} x_i^{(t)}，并用未加权 x_i^{(t)} 更新未入选包的双衰减残差 r_i^{(t)}；
  │     2. 对每个入选包 j \in \mathcal{K}^{(t)}，编码 pt_{i,j}^{(t)} = Ecd(\tilde{g}_{i,j}^{(t)}, \Delta)，
  │        用有效密钥 \tilde{s}_{i,j}^{(t)} = [s_i + \lambda_i^{(t)} \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_{k,i} + \lambda_i^{(t)} b_j^{(t)} z_i]_q
  │        加密上传单环元素密文 ct_{i,j}^{(t)} = [a_j^{(t)} \cdot \tilde{s}_{i,j}^{(t)} + \tilde{p} \cdot e_{i,j}^{(t)} + pt_{i,j}^{(t)}]_q。
  │
  ├── Phase 3 (全局同态聚合与掉线密钥补偿 ESP-Comp & ESP-Agg)：
  │     设完成 Phase 2 上传的存活客户端集为 \widehat{\mathcal{S}}^{(t)} = \mathcal{S}^{(t)} \setminus \mathcal{D}^{(t)} (|\widehat{\mathcal{S}}^{(t)}| \ge \tau)：
  │     ├── 同步无掉线情况 (\mathcal{D}^{(t)} = \emptyset)：服务器直接求和 C_j^{(t)} = [\sum_{i \in \mathcal{S}^{(t)}} ct_{i,j}^{(t)}]_q = [a_j^{(t)} S + \tilde{p} E_j^{(t)} + pt_j^{(t)}]_q；
  │     └── 异步有掉线情况 (\mathcal{D}^{(t)} \neq \emptyset)：服务器广播存活集 \widehat{\mathcal{S}}^{(t)}，存活客户端 i \in \widehat{\mathcal{S}}^{(t)} 计算新拉格朗日系数 \widehat{\lambda}_i^{(t)}，
  │                                               上传纯密钥补偿密文 \delta_{i,j}^{(t)} = [a_j^{(t)} \cdot \kappa_{i,j}^{(t)} + \tilde{p} \cdot \hat{e}_{i,j}^{(t)}]_q，
  │                                               服务器求和 C_j^{(t)} = [\sum_{i \in \widehat{\mathcal{S}}^{(t)}} (ct_{i,j}^{(t)} + \delta_{i,j}^{(t)})]_q = [a_j^{(t)} S + \tilde{p} \widehat{E}_j^{(t)} + pt_j^{(t)}]_q。
  │
  └── Phase 4a (滑动队列入队与空闲客户端后台预取 ECP-Queue & ECP-Fetch)：
        服务器将 (t, \mathcal{K}^{(t)}, C^{(t)}) 推入容量为 R 的滑动队列 \mathcal{Q}；
        预采样候选池 i \in \mathcal{P}^{(t+R)} 在后台空闲期异步下载缺失轮次的稀疏包密文 C_j^{(r)} 存入本地缓存 \mathcal{L}_{i,j}。
```

---

### 1.2 四大核心密码学与系统设计机制详解

#### 机制 1：为什么将合谋上限设为 $\kappa \le \tau - 2$（而非 $\tau - 1$）？
- 在 $(\tau, N)$-Shamir 秘密共享中，秘密多项式 $F_k(x)$ 和零共享多项式 $\Psi(x)$ 的次数均为 $\tau - 1$（需要 $\tau$ 个点才能唯一插值还原）。
- 但对于零共享多项式 $\Psi(x)$，其在 $x = 0$ 处的取值 $\Psi(0) = 0$ 是**全网公开已知的**！如果允许 $\kappa = \tau - 1$ 个客户端合谋，她们手头的 $\tau - 1$ 个零份额 $\{z_i\}_{i \in \mathcal{K}_{\mathrm{cor}}}$ 加上公开点 $\Psi(0) = 0$ 就凑够了 $\tau$ 个评估点，从而能够直接通过拉格朗日插值还原出整个多项式 $\Psi(x)$，进而算出所有诚实客户端的零份额 $z_h = \Psi(\alpha_h)$。
- **将合谋上限设定为 $\kappa \le \tau - 2$ 带来双重收益**：
  1. **保护零共享多项式 $\Psi(x)$**：$\kappa \le \tau - 2$ 个合谋客户端加上公开点 $\Psi(0) = 0$ 最多只有 $(\tau - 2) + 1 = \tau - 1 < \tau$ 个插值点，$\Psi(x)$ 至少保留一个未知的环自由度，合谋者无法通过份额插值恢复诚实客户端的 $z_h = \Psi(\alpha_h)$。
  2. **自动保证每轮至少有 2 个诚实存活客户端**：由于每轮存活上传者满足 $|\widehat{\mathcal{S}}^{(t)}| \ge \tau$，在 $\kappa \le \tau - 2$ 下，每轮存活的诚实客户端数量自动满足 $|\mathcal{H}^{(t)}| = |\widehat{\mathcal{S}}^{(t)} \setminus \mathcal{K}_{\mathrm{cor}}| \ge \tau - (\tau - 2) = 2$。因此合谋者解密全局聚合密文 $C_j^{(t)}$ 并减去自身贡献后，永远只能得到至少 2 个诚实客户端的更新之和 $\sum_{h \in \mathcal{H}^{(t)}} \mathrm{pt}_{h,j}^{(t)}$，无法分离任何单个诚实客户端的明文更新。

#### 机制 2：为什么全文采用“固定活跃集权重规则”（Fixed Active-Set Weight Rule）？
- 在 Phase 1 确认本轮活跃集 $\mathcal{S}^{(t)}$ 时，每个活跃客户端 $i \in \mathcal{S}^{(t)}$ 的聚合权重即固定为：
  $$\omega_i^{(t)} = \frac{n_i}{\sum_{u \in \mathcal{S}^{(t)}} n_u}, \qquad \sum_{i \in \mathcal{S}^{(t)}} \omega_i^{(t)} = 1$$
- **为什么不在 Phase 3 掉线后重归一化权重？**
  1. 如果在 Phase 3 掉线后将权重重归一化为 $\widehat{\omega}_i^{(t)} = n_i / \sum_{k \in \widehat{\mathcal{S}}^{(t)}} n_k$，要么需要存活客户端在补偿密文 $\delta_{i,j}^{(t)}$ 中重新编码并上传明文差值 $\Delta\mathrm{pt}_{i,j}^{(t)} = \mathrm{Ecd}((\widehat{\omega}_i^{(t)} - \omega_i^{(t)})\mathbf{x}_{i,j}^{(t)}, \Delta)$（这不仅引入定点取整误差 $\mathrm{Ecd}(\omega_i^{(t)}\mathbf{x}) + \mathrm{Ecd}((\widehat{\omega}_i^{(t)}-\omega_i^{(t)})\mathbf{x}) \neq \mathrm{Ecd}(\widehat{\omega}_i^{(t)}\mathbf{x})$，而且在补偿密文中暴露了额外明文信息），要么需要在解密后除以总权重 $\Omega^{(r)} = \sum_{i \in \widehat{\mathcal{S}}^{(r)}} \omega_i^{(r)}$（这会导致不同轮次 $r$ 的缩放比例 $\Omega^{(r)}$ 不同，从而无法在 Phase 4 跨多轮直接相加密文并一步解密！）。
  2. 采用固定活跃集权重 $\omega_i^{(t)}$ 后：Phase 3 的补偿密文 $\delta_{i,j}^{(t)} = \bigl[a_j^{(t)} \cdot \kappa_{i,j}^{(t)} + \tilde{p} \cdot \hat{e}_{i,j}^{(t)}\bigr]_q$ 是**纯密钥补偿密文（不含任何明文项）**，且每一轮的聚合明文 $\mathrm{pt}_j^{(r)} = \sum_{i \in \widehat{\mathcal{S}}^{(r)}} \mathrm{Ecd}(\omega_i^{(r)} \mathbf{x}_{i,j}^{(r)}, \Delta)$ 具有完全一致的跨轮尺度，使得 ECP 模块可以直接跨轮累加密文并一步解码！

#### 机制 3：为什么投票掩码乘以 $a_0^{(t)}$，且跨轮交叉相乘不会泄露个人投票？
- **域分离与掩码构造**：Phase 1 投票只需上传 1 个打包了 $J$ 个二进制位的多项式 $v_i^{(t)}(X) = \sum_{j=1}^J v_{i,j}^{(t)} X^{j-1}$，因此专门使用预留索引 $0$ 生成 $a_0^{(t)} = \mathrm{HE.PRPG}(\sigma_b, t \parallel 0)$，与 Phase 2 的梯度包索引 $j \in \{1, \dots, J\}$ 严格域分离。
- **为什么跨轮交叉相乘 $D = [A_2 \hat{v}_h^{(1)} - A_1 \hat{v}_h^{(2)}]_q$ 无法通过模 $p$ 恢复投票？**
  设 $A_t = a_0^{(t)} \lambda_h^{(t)} \in \mathcal{R}_q$。若观察者对同一诚实客户端 $h$ 在第 1、2 轮的投票做交叉相乘消去 $z_h$：
  $$D = \bigl[ A_2 \hat{v}_h^{(1)} - A_1 \hat{v}_h^{(2)} \bigr]_q = \Bigl[\, \tilde{p}\bigl(A_2 e_{h,0}^{(1)} - A_1 e_{h,0}^{(2)}\bigr) + \bigl(A_2 v_h^{(1)}(X) - A_1 v_h^{(2)}(X)\bigr) \,\Bigr]_q$$
  由于 $A_1, A_2 \in \mathcal{R}_q$ 的系数高达 $\mathcal{O}(q)$，乘积 $\tilde{p}(A_2 e_{h,0}^{(1)} - A_1 e_{h,0}^{(2)})$ 的未约化整数系数膨胀至 $\mathcal{O}(\tilde{p} \cdot n \cdot q \cdot B_e) \gg q/2$，在模 $q$ 约化 $[\cdot]_q$ 时必然触发未知的整数多项式倍回绕 $k(X) \cdot q$（其中 $k(X) \in \mathcal{R}$ 未知）：
  $$D = \tilde{p}\bigl(A_2 e_{h,0}^{(1)} - A_1 e_{h,0}^{(2)}\bigr) + \bigl(A_2 v_h^{(1)}(X) - A_1 v_h^{(2)}(X)\bigr) + k(X) \cdot q$$
  因为 RNS 模数 $q = \prod_{\ell=1}^L q_\ell$ 由大奇素数构成，而明文模数 $p$ 满足 $\gcd(p, q) = 1$（即 $p \nmid q$），对 $D$ 取 $\bmod p$ 时，虽然 $\tilde{p}(\cdot) \bmod p = 0$，但回绕余项 $k(X) \cdot q \bmod p \neq 0$ 无法消去，从而完全掩盖了 $A_2 v_h^{(1)}(X) - A_1 v_h^{(2)}(X)$。

#### 机制 4：为什么有效密钥中的零份额 $z_i$ 必须乘以随包刷新的多项式 $b_j^{(t)}$？
- 根据 Colin de Verdière 等人~\cite{colin2026tfhesd} 的证明，若有效密钥仅嵌入无掩码的拉格朗日组合 $s_i + \lambda_i^{(t)} \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_{k,i}$，跨多轮不同活跃集观察密文即可通过线性方程组解出静态私钥 $s_i$ 与份额 $\{s_{k,i}\}$。
- 但若仅加上静态的 $\lambda_i^{(t)} z_i$（不乘 $b_j^{(t)}$），由于 $z_i$ 在同一轮的所有包 $j \in \mathcal{K}^{(t)}$ 中完全相同，持有种子 $\sigma_a$（即知道 $a_j^{(t)}$）的客户端可以对同一轮两个不同包 $j_1 \neq j_2$ 的密文做线性组合，消去公用的 $\lambda_i^{(t)} z_i$。
- 乘上随包刷新的 $b_j^{(t)} = \mathrm{HE.PRPG}(\sigma_b, t \parallel j)$ 后：
  - **对单个客户端不同包 $j_1 \neq j_2$**：掩码 $b_{j_1}^{(t)} z_i \neq b_{j_2}^{(t)} z_i$ 随包变化，彻底阻止跨包消元；
  - **对同一包 $j$ 的跨客户端聚合**：所有客户端在包 $j$ 上共享同一个 $b_j^{(t)}$，求和时 $b_j^{(t)}$ 作为公因式提到求和号外：$\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} b_j^{(t)} z_i = b_j^{(t)} \sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} z_i = 0$，自动归零！

---

## 第二部分：全篇核心公式“零跳步”逐行数学推导（Zero-Skip Derivations）

### 推导 1：基础单环元素一步加解密与同轮多包掩码复用漏洞（Section III-C3）

#### （1）加密、同态聚合与一步解密完整展开
- **密钥生成**：KGC 独立采样 $N$ 个加密密钥 $s_i \leftarrow \mathcal{U}(\mathcal{R}_q)$（$i \in [N]$），计算全局聚合解密密钥：
  $$S = \Biggl[ \sum_{i=1}^N s_i \Biggr]_q \in \mathcal{R}_q$$
- **单客户端包加密（式 (4)）**：在第 $t$ 轮，客户端 $i$ 使用 $a_j^{(t)} = \mathrm{HE.PRPG}(\sigma_a, t \parallel j)$ 对第 $j$ 个包的明文多项式 $\mathrm{pt}_{i,j}^{(t)} = \mathrm{Ecd}(\tilde{\mathbf{g}}_{i,j}^{(t)}, \Delta)$ 进行加密：
  $$\mathrm{ct}_{i,j}^{(t)} = \mathrm{HE.Enc}\bigl(a_j^{(t)}, s_i, \mathrm{pt}_{i,j}^{(t)}\bigr) = \Bigl[\, a_j^{(t)} \cdot s_i + \tilde{p} \cdot e_{i,j}^{(t)} + \mathrm{pt}_{i,j}^{(t)} \,\Bigr]_q \tag{D1.1}$$
  其中 $e_{i,j}^{(t)} \leftarrow \chi_e$ 为小系数误差多项式，$\tilde{p}$ 为明文模数 $p$ 的整数倍（即 $p \mid \tilde{p}$，存在整数 $m$ 使得 $\tilde{p} = m \cdot p$）。
- **服务器同态聚合（式 (5)–(6)）**：当全集 $[N]$ 参与时，服务器将 $N$ 个客户端的密文在 $\mathcal{R}_q$ 上相加，逐行展开如下：
  $$\begin{aligned}
  C_j^{(t)} &= \mathrm{HE.Eval}\Bigl(\bigl\{\mathrm{ct}_{i,j}^{(t)}\bigr\}_{i \in [N]}\Bigr) = \Biggl[ \sum_{i=1}^N \mathrm{ct}_{i,j}^{(t)} \Biggr]_q \\
  &= \Biggl[ \sum_{i=1}^N \Bigl( a_j^{(t)} \cdot s_i + \tilde{p} \cdot e_{i,j}^{(t)} + \mathrm{pt}_{i,j}^{(t)} \Bigr) \Biggr]_q \\
  &= \Biggl[ \sum_{i=1}^N \bigl(a_j^{(t)} \cdot s_i\bigr) + \sum_{i=1}^N \bigl(\tilde{p} \cdot e_{i,j}^{(t)}\bigr) + \sum_{i=1}^N \mathrm{pt}_{i,j}^{(t)} \Biggr]_q \\
  &= \Biggl[ a_j^{(t)} \cdot \underbrace{\Biggl(\sum_{i=1}^N s_i\Biggr)}_{\equiv\, S \pmod q} + \tilde{p} \cdot \underbrace{\Biggl(\sum_{i=1}^N e_{i,j}^{(t)}\Biggr)}_{=\, E_j^{(t)}} + \underbrace{\sum_{i=1}^N \mathrm{pt}_{i,j}^{(t)}}_{=\, \mathrm{pt}_j^{(t)}} \Biggr]_q \\
  &= \Bigl[\, a_j^{(t)} \cdot S + \tilde{p} \cdot E_j^{(t)} + \mathrm{pt}_j^{(t)} \,\Bigr]_q
  \end{aligned} \tag{D1.2}$$
- **客户端一步解密（式 (7)）**：持有 $(S, \sigma_a)$ 的客户端本地生成 $a_j^{(t)} = \mathrm{HE.PRPG}(\sigma_a, t \parallel j)$，计算：
  $$\begin{aligned}
  \mathrm{HE.Dec}\bigl(a_j^{(t)}, S, C_j^{(t)}\bigr)
  &= \Bigl[\bigl[\, C_j^{(t)} - a_j^{(t)} \cdot S \,\bigr]_q\Bigr]_p \\
  &= \Bigl[\bigl[\, \bigl(a_j^{(t)} \cdot S + \tilde{p} \cdot E_j^{(t)} + \mathrm{pt}_j^{(t)}\bigr) - a_j^{(t)} \cdot S \,\bigr]_q\Bigr]_p \\
  &= \Bigl[\bigl[\, \tilde{p} \cdot E_j^{(t)} + \mathrm{pt}_j^{(t)} \,\bigr]_q\Bigr]_p
  \end{aligned} \tag{D1.3}$$
  **无回绕消噪条件**：只要参数满足无穷范数条件 $\|\tilde{p} \cdot E_j^{(t)} + \mathrm{pt}_j^{(t)}\|_\infty < q/2$，则多项式 $\tilde{p} \cdot E_j^{(t)} + \mathrm{pt}_j^{(t)}$ 的每一个系数都严格落在中心化区间 $(-q/2, q/2)$ 内，因此内层模 $q$ 约化 $\bigl[\tilde{p} \cdot E_j^{(t)} + \mathrm{pt}_j^{(t)}\bigr]_q$ 不发生任何模 $q$ 回绕，直接等于整数环 $\mathcal{R}$ 上的多项式 $\tilde{p} \cdot E_j^{(t)} + \mathrm{pt}_j^{(t)}$。随后执行外层模 $p$ 约化 $[\cdot]_p$，由于 $p \mid \tilde{p}$（即 $\tilde{p} \equiv 0 \pmod p$）且 $\|\mathrm{pt}_j^{(t)}\|_\infty < p/2$：
  $$\Bigl[\, \tilde{p} \cdot E_j^{(t)} + \mathrm{pt}_j^{(t)} \,\Bigr]_p = \Bigl[\, \underbrace{\tilde{p} \cdot E_j^{(t)}}_{\equiv\, 0 \pmod p} + \mathrm{pt}_j^{(t)} \,\Bigr]_p = \mathrm{pt}_j^{(t)}$$
  最后调用 CKKS 解码函数 $\tilde{\mathbf{g}}_j^{(t)} = \mathrm{Dcd}(\mathrm{pt}_j^{(t)}, \Delta) = \Delta^{-1} \cdot \varphi(\mathrm{pt}_j^{(t)})$ 即可恢复聚合浮点更新向量。

#### （2）若同一轮所有包复用同一个 $a^{(t)}$ 的跨包密钥抵消漏洞推导
假设在单步解密协议中不为每个包 $j$ 派生独立的 $a_j^{(t)}$，而是对同一轮的兩個不同包 $j_1 \neq j_2 \in [J]$ 复用同一个 $a^{(t)}$：
$$\mathrm{ct}_{i,j_1}^{(t)} = \bigl[\, a^{(t)} \cdot s_i + \tilde{p} \cdot e_{i,j_1}^{(t)} + \mathrm{pt}_{i,j_1}^{(t)} \,\bigr]_q, \qquad \mathrm{ct}_{i,j_2}^{(t)} = \bigl[\, a^{(t)} \cdot s_i + \tilde{p} \cdot e_{i,j_2}^{(t)} + \mathrm{pt}_{i,j_2}^{(t)} \,\bigr]_q$$
任何观察者只需将这两个密文在 $\mathcal{R}_q$ 上直接相减：
$$\begin{aligned}
\bigl[\, \mathrm{ct}_{i,j_1}^{(t)} - \mathrm{ct}_{i,j_2}^{(t)} \,\bigr]_q
&= \Bigl[\, \bigl(a^{(t)} \cdot s_i + \tilde{p} \cdot e_{i,j_1}^{(t)} + \mathrm{pt}_{i,j_1}^{(t)}\bigr) - \bigl(a^{(t)} \cdot s_i + \tilde{p} \cdot e_{i,j_2}^{(t)} + \mathrm{pt}_{i,j_2}^{(t)}\bigr) \,\Bigr]_q \\
&= \Bigl[\, \underline{a^{(t)} \cdot s_i - a^{(t)} \cdot s_i} + \tilde{p} \cdot \bigl(e_{i,j_1}^{(t)} - e_{i,j_2}^{(t)}\bigr) + \bigl(\mathrm{pt}_{i,j_1}^{(t)} - \mathrm{pt}_{i,j_2}^{(t)}\bigr) \,\Bigr]_q \\
&= \Bigl[\, \tilde{p} \cdot \bigl(e_{i,j_1}^{(t)} - e_{i,j_2}^{(t)}\bigr) + \bigl(\mathrm{pt}_{i,j_1}^{(t)} - \mathrm{pt}_{i,j_2}^{(t)}\bigr) \,\Bigr]_q
\end{aligned}$$
因为 $\|\tilde{p}(e_{i,j_1}^{(t)} - e_{i,j_2}^{(t)}) + (\mathrm{pt}_{i,j_1}^{(t)} - \mathrm{pt}_{i,j_2}^{(t)})\|_\infty < q/2$，再取模 $p$ 即得：
$$\Bigl[\bigl[\, \mathrm{ct}_{i,j_1}^{(t)} - \mathrm{ct}_{i,j_2}^{(t)} \,\bigr]_q\Bigr]_p = \bigl[\, \mathrm{pt}_{i,j_1}^{(t)} - \mathrm{pt}_{i,j_2}^{(t)} \,\bigr]_p$$
私钥项 $a^{(t)} \cdot s_i$ 在无需知道 $s_i$ 的情况下被完全抵消！而我们采用 $a_j^{(t)} = \mathrm{HE.PRPG}(\sigma_a, t \parallel j)$ 使 $a_{j_1}^{(t)} \neq a_{j_2}^{(t)}$，彻底消除了这一同轮跨包相减漏洞。

---

### 推导 2：分圆环 $\mathcal{R}_q$ 上的可逆 Shamir 拉格朗日插值恒等式（Section III-C3）

1. **为什么评估点差值 $\alpha_i - \alpha_u$ 在 $\mathcal{R}_q$ 中一定可逆？**
   遵循 Mouchet 等人~\cite{mouchet2023threshold} 的构造，设 RNS 密文模数 $q = \prod_{\ell=1}^L q_\ell$，其中每个素因子 $q_\ell$ 均满足 $q_\ell > N$（例如 $N \le 1000$，而 40-bit/60-bit RNS 素数 $q_\ell > 2^{40} \gg 1000$）。
   我们选取常数多项式作为评估点：$\alpha_i = i \in \mathcal{R}_q$（$i \in \{1, 2, \dots, N\}$）。
   对任意两个不同客户端 $i \neq u \in [N]$，其评估点之差为非零整数 $\alpha_i - \alpha_u = i - u$，且满足：
   $$0 < |i - u| < N < q_\ell, \qquad \forall \ell \in \{1, \dots, L\}$$
   因为 $|i - u|$ 严格小于 $q$ 的每一个素因子 $q_\ell$，所以 $i - u$ 与每一个 $q_\ell$ 都互素，从而与乘积 $q = \prod_{\ell=1}^L q_\ell$ 互素：
   $$\gcd(\alpha_i - \alpha_u, q) = \gcd(i - u, q) = 1$$
   由扩展欧几里得算法，整数 $(i - u)^{-1} \bmod q$ 在 $\mathbb{Z}_q^\times$ 中唯一存在，作为常数多项式自然也是分圆环 $\mathcal{R}_q = \mathbb{Z}_q[X]/(X^n+1)$ 中的可逆元（Unit）。

2. **拉格朗日插值恢复 $s_k$ 与归零 $z_i$ 的逐行推导**
   对任意大小 $|\mathcal{S}^{(t)}| \ge \tau$ 的客户端子集 $\mathcal{S}^{(t)} \subseteq \mathcal{C}$，定义客户端 $i \in \mathcal{S}^{(t)}$ 在原点 $x = 0$ 处的拉格朗日插值系数为：
   $$\lambda_i^{(t)} = \prod_{u \in \mathcal{S}^{(t)} \setminus \{i\}} (-\alpha_u)(\alpha_i - \alpha_u)^{-1} \pmod q \tag{D2.1}$$
   - 对每个客户端 $k \in [N]$ 的秘密共享多项式 $F_k(x) = s_k + \sum_{m=1}^{\tau-1} f_{k,m} x^m \in \mathcal{R}_q[x]$，由于 $\deg(F_k) = \tau - 1 < \tau \le |\mathcal{S}^{(t)}|$，且 $s_{k,i} = F_k(\alpha_i)$，由拉格朗日插值公式在 $x = 0$ 处求值：
     $$\Biggl[ \sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} s_{k,i} \Biggr]_q = \Biggl[ \sum_{i \in \mathcal{S}^{(t)}} F_k(\alpha_i) \prod_{u \in \mathcal{S}^{(t)} \setminus \{i\}} \frac{0 - \alpha_u}{\alpha_i - \alpha_u} \Biggr]_q = F_k(0) = s_k \tag{D2.2}$$
   - 对零共享多项式 $\Psi(x) = 0 + \sum_{m=1}^{\tau-1} \psi_m x^m \in \mathcal{R}_q[x]$，由于 $\deg(\Psi) = \tau - 1 < \tau \le |\mathcal{S}^{(t)}|$，且 $z_i = \Psi(\alpha_i)$，在 $x = 0$ 处求值：
     $$\Biggl[ \sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} z_i \Biggr]_q = \Biggl[ \sum_{i \in \mathcal{S}^{(t)}} \Psi(\alpha_i) \prod_{u \in \mathcal{S}^{(t)} \setminus \{i\}} \frac{0 - \alpha_u}{\alpha_i - \alpha_u} \Biggr]_q = \Psi(0) = 0 \tag{D2.3}$$
   完全同理，当集合替换为存活上传者集合 $\widehat{\mathcal{S}}^{(t)}$（$|\widehat{\mathcal{S}}^{(t)}| \ge \tau$）及对应系数 $\widehat{\lambda}_i^{(t)} = \prod_{u \in \widehat{\mathcal{S}}^{(t)} \setminus \{i\}} (-\alpha_u)(\alpha_i - \alpha_u)^{-1} \bmod q$ 时，恒有：
   $$\Biggl[ \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \widehat{\lambda}_i^{(t)} s_{k,i} \Biggr]_q = F_k(0) = s_k, \qquad \Biggl[ \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \widehat{\lambda}_i^{(t)} z_i \Biggr]_q = \Psi(0) = 0 \tag{D2.4}$$

---

### 推导 3：Phase 1 零共享安全投票掩码抵消与计票恢复（Section IV-C2，式 (9)–(10)）

1. **单客户端掩码投票构造（式 (9)）**：
   每个活跃客户端 $i \in \mathcal{S}^{(t)}$ 将 $J$ 维二进制投票向量 $\mathbf{v}_i^{(t)} = (v_{i,1}^{(t)}, \dots, v_{i,J}^{(t)}) \in \{0, 1\}^J$ 嵌入多项式低 $J$ 项系数：
   $$v_i^{(t)}(X) = \sum_{j=1}^J v_{i,j}^{(t)} X^{j-1} \in \mathcal{R}_p$$
   并使用 $a_0^{(t)} = \mathrm{HE.PRPG}(\sigma_b, t \parallel 0)$ 上传掩码投票多项式：
   $$\hat{v}_i^{(t)} = \Bigl[\, a_0^{(t)} \cdot \lambda_i^{(t)} z_i + \tilde{p} \cdot e_{i,0}^{(t)} + v_i^{(t)}(X) \,\Bigr]_q \in \mathcal{R}_q \tag{D3.1}$$

2. **服务器同态求和与零份额抵消（式 (10) 零跳步展开）**：
   服务器收集所有 $i \in \mathcal{S}^{(t)}$ 的 $\hat{v}_i^{(t)}$，依次执行模 $q$ 求和与模 $p$ 约化：
   $$\begin{aligned}
   V^{(t)}(X) &= \Biggl[\biggl[\, \sum_{i \in \mathcal{S}^{(t)}} \hat{v}_i^{(t)} \,\biggr]_q\Biggr]_p \\
   &= \Biggl[\biggl[\, \sum_{i \in \mathcal{S}^{(t)}} \Bigl( a_0^{(t)} \cdot \lambda_i^{(t)} z_i + \tilde{p} \cdot e_{i,0}^{(t)} + v_i^{(t)}(X) \Bigr) \,\biggr]_q\Biggr]_p \\
   &= \Biggl[\biggl[\, \sum_{i \in \mathcal{S}^{(t)}} \bigl(a_0^{(t)} \cdot \lambda_i^{(t)} z_i\bigr) + \sum_{i \in \mathcal{S}^{(t)}} \bigl(\tilde{p} \cdot e_{i,0}^{(t)}\bigr) + \sum_{i \in \mathcal{S}^{(t)}} v_i^{(t)}(X) \,\biggr]_q\Biggr]_p
   \end{aligned}$$
   因为 $a_0^{(t)}$ 对所有 $i \in \mathcal{S}^{(t)}$ 均相同（与下标 $i$ 无关），将 $a_0^{(t)}$ 提取到第一项求和号外，并代入式 (D2.3) 的 $\bigl[\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} z_i\bigr]_q = 0$：
   $$\begin{aligned}
   V^{(t)}(X) &= \Biggl[\biggl[\, a_0^{(t)} \cdot \underbrace{\Biggl(\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} z_i\Biggr)}_{\equiv\, \Psi(0) \,=\, 0 \pmod q} + \tilde{p} \cdot \underbrace{\Biggl(\sum_{i \in \mathcal{S}^{(t)}} e_{i,0}^{(t)}\Biggr)}_{=\, E_0^{(t)}} + \sum_{i \in \mathcal{S}^{(t)}} v_i^{(t)}(X) \,\biggr]_q\Biggr]_p \\
   &= \Biggl[\biggl[\, 0 + \tilde{p} \cdot E_0^{(t)} + \sum_{i \in \mathcal{S}^{(t)}} v_i^{(t)}(X) \,\biggr]_q\Biggr]_p
   \end{aligned}$$
   当满足无回绕条件 $\|\tilde{p} E_0^{(t)} + \sum_{i \in \mathcal{S}^{(t)}} v_i^{(t)}(X)\|_\infty < q/2$ 且 $|\mathcal{S}^{(t)}| < p$、$p \mid \tilde{p}$ 时，内层 $[\cdot]_q$ 不发生模 $q$ 回绕，外层 $[\cdot]_p$ 消去 $\tilde{p} E_0^{(t)}$：
   $$\begin{aligned}
   V^{(t)}(X) &= \Biggl[\, \underbrace{\tilde{p} \cdot E_0^{(t)}}_{\equiv\, 0 \pmod p} + \sum_{i \in \mathcal{S}^{(t)}} \sum_{j=1}^J v_{i,j}^{(t)} X^{j-1} \,\Biggr]_p \\
   &= \sum_{j=1}^J \Biggl( \underbrace{\sum_{i \in \mathcal{S}^{(t)}} v_{i,j}^{(t)}}_{=\, \nu_j^{(t)} \in [0, K]} \Biggr) X^{j-1} = \sum_{j=1}^J \nu_j^{(t)} X^{j-1}
   \end{aligned} \tag{D3.2}$$
   服务器直接读取 $V^{(t)}(X)$ 的前 $J$ 个系数，即可精确获得每个包 $j$ 的得票总数 $\nu_j^{(t)}$。

---

### 推导 4：Phase 2 稀疏包加密与 Phase 3 同步无掉线聚合（Section IV-C3 & IV-C4，式 (11)–(13)）

1. **有效密钥与上传密文构造（式 (11)）**：
   对于每个入选包 $j \in \mathcal{K}^{(t)}$，客户端 $i \in \mathcal{S}^{(t)}$ 编码 $\mathrm{pt}_{i,j}^{(t)} = \mathrm{Ecd}(\omega_i^{(t)} \mathbf{x}_{i,j}^{(t)}, \Delta)$，使用 $a_j^{(t)} = \mathrm{HE.PRPG}(\sigma_a, t \parallel j)$ 和 $b_j^{(t)} = \mathrm{HE.PRPG}(\sigma_b, t \parallel j)$ 构造有效密钥并加密：
   $$\tilde{s}_{i,j}^{(t)} = \biggl[\, s_i + \lambda_i^{(t)} \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_{k,i} + \lambda_i^{(t)} b_j^{(t)} z_i \,\biggr]_q \tag{D4.1}$$
   $$\mathrm{ct}_{i,j}^{(t)} = \Bigl[\, a_j^{(t)} \cdot \tilde{s}_{i,j}^{(t)} + \tilde{p} \cdot e_{i,j}^{(t)} + \mathrm{pt}_{i,j}^{(t)} \,\Bigr]_q \tag{D4.2}$$

2. **同步无掉线场景（$\mathcal{D}^{(t)} = \emptyset, \widehat{\mathcal{S}}^{(t)} = \mathcal{S}^{(t)}$）聚合推导（式 (13) 零跳步展开）**：
   当所有确认活跃客户端 $i \in \mathcal{S}^{(t)}$ 均完成上传时，服务器对 $\mathrm{ct}_{i,j}^{(t)}$ 求和，将式 (D4.1) 和 (D4.2) 代入：
   $$\begin{aligned}
   C_j^{(t)} &= \mathrm{HE.Eval}\Bigl(\bigl\{\mathrm{ct}_{i,j}^{(t)}\bigr\}_{i \in \mathcal{S}^{(t)}}\Bigr) = \Biggl[ \sum_{i \in \mathcal{S}^{(t)}} \mathrm{ct}_{i,j}^{(t)} \Biggr]_q \\
   &= \Biggl[ \sum_{i \in \mathcal{S}^{(t)}} \Bigl( a_j^{(t)} \cdot \tilde{s}_{i,j}^{(t)} + \tilde{p} \cdot e_{i,j}^{(t)} + \mathrm{pt}_{i,j}^{(t)} \Bigr) \Biggr]_q \\
   &= \Biggl[ a_j^{(t)} \cdot \Biggl( \sum_{i \in \mathcal{S}^{(t)}} \tilde{s}_{i,j}^{(t)} \Biggr) + \tilde{p} \sum_{i \in \mathcal{S}^{(t)}} e_{i,j}^{(t)} + \sum_{i \in \mathcal{S}^{(t)}} \mathrm{pt}_{i,j}^{(t)} \Biggr]_q
   \end{aligned} \tag{D4.3}$$
   现在单独把括号内的有效密钥之和 $\sum_{i \in \mathcal{S}^{(t)}} \tilde{s}_{i,j}^{(t)}$ 完整展开：
   $$\begin{aligned}
   \sum_{i \in \mathcal{S}^{(t)}} \tilde{s}_{i,j}^{(t)}
   &\equiv \sum_{i \in \mathcal{S}^{(t)}} \Biggl( s_i + \lambda_i^{(t)} \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_{k,i} + \lambda_i^{(t)} b_j^{(t)} z_i \Biggr) \pmod q \\
   &\equiv \sum_{i \in \mathcal{S}^{(t)}} s_i + \sum_{i \in \mathcal{S}^{(t)}} \Biggl( \lambda_i^{(t)} \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_{k,i} \Biggr) + \sum_{i \in \mathcal{S}^{(t)}} \bigl(\lambda_i^{(t)} b_j^{(t)} z_i\bigr) \pmod q
   \end{aligned} \tag{D4.4}$$
   - **对式 (D4.4) 的第二项交换有限双重求和顺序**（外层 $i \in \mathcal{S}^{(t)}$ 与内层 $k \in \bar{\mathcal{S}}^{(t)}$ 互不依赖），并代入式 (D2.2)：
     $$\sum_{i \in \mathcal{S}^{(t)}} \Biggl( \lambda_i^{(t)} \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_{k,i} \Biggr) = \sum_{k \in \bar{\mathcal{S}}^{(t)}} \Biggl( \underbrace{\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} s_{k,i}}_{=\, F_k(0) \,=\, s_k} \Biggr) = \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_k \tag{D4.5}$$
   - **对式 (D4.4) 的第三项提取与 $i$ 无关的公因式 $b_j^{(t)}$**，并代入式 (D2.3)：
     $$\sum_{i \in \mathcal{S}^{(t)}} \bigl(\lambda_i^{(t)} b_j^{(t)} z_i\bigr) = b_j^{(t)} \cdot \Biggl( \underbrace{\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} z_i}_{=\, \Psi(0) \,=\, 0} \Biggr) = b_j^{(t)} \cdot 0 = 0 \tag{D4.6}$$
   - **将式 (D4.5) 和 (D4.6) 代回式 (D4.4)**，并注意 $\mathcal{S}^{(t)} \cup \bar{\mathcal{S}}^{(t)} = \mathcal{C} = [N]$ 且 $\mathcal{S}^{(t)} \cap \bar{\mathcal{S}}^{(t)} = \emptyset$：
     $$\sum_{i \in \mathcal{S}^{(t)}} \tilde{s}_{i,j}^{(t)} \equiv \sum_{i \in \mathcal{S}^{(t)}} s_i + \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_k + 0 = \sum_{u=1}^N s_u \equiv S \pmod q \tag{D4.7}$$
   将式 (D4.7) 代回式 (D4.3)，即得同步聚合结果（式 (13)）：
   $$C_j^{(t)} = \Bigl[\, a_j^{(t)} \cdot S + \tilde{p} \cdot E_j^{(t)} + \mathrm{pt}_j^{(t)} \,\Bigr]_q \tag{D4.8}$$
   其中 $E_j^{(t)} = \sum_{i \in \mathcal{S}^{(t)}} e_{i,j}^{(t)}$，$\mathrm{pt}_j^{(t)} = \sum_{i \in \mathcal{S}^{(t)}} \mathrm{pt}_{i,j}^{(t)}$。

---

### 推导 5：Phase 3 异步上传掉线补偿聚合（Section IV-C4，式 (14)–(15) 零跳步推导）

当上传阶段发生中途掉线（$\mathcal{D}^{(t)} = \mathcal{S}^{(t)} \setminus \widehat{\mathcal{S}}^{(t)} \neq \emptyset$），只有存活集合 $\widehat{\mathcal{S}}^{(t)}$（$|\widehat{\mathcal{S}}^{(t)}| \ge \tau$）完成了 $\mathrm{ct}_{i,j}^{(t)}$ 的上传。此时：
- 所有未完成上传的客户端集合为：$k \notin \widehat{\mathcal{S}}^{(t)} \Longleftrightarrow k \in \bar{\mathcal{S}}^{(t)} \cup \mathcal{D}^{(t)}$；
- 全体客户端集合划分为无交并集：$\mathcal{C} = \widehat{\mathcal{S}}^{(t)} \cup \bigl(\mathcal{C} \setminus \widehat{\mathcal{S}}^{(t)}\bigr)$，即：
  $$\sum_{i \in \widehat{\mathcal{S}}^{(t)}} s_i + \sum_{k \notin \widehat{\mathcal{S}}^{(t)}} s_k = \sum_{u=1}^N s_u = S \tag{D5.1}$$

#### 第 1 步：存活客户端构造掉线补偿密钥项 $\kappa_{i,j}^{(t)}$ 与纯密钥补偿密文 $\delta_{i,j}^{(t)}$（式 (14)）
服务器广播存活集合 $\widehat{\mathcal{S}}^{(t)}$。每个存活客户端 $i \in \widehat{\mathcal{S}}^{(t)}$ 计算基于 $\widehat{\mathcal{S}}^{(t)}$ 的新拉格朗日系数 $\widehat{\lambda}_i^{(t)} = \prod_{u \in \widehat{\mathcal{S}}^{(t)} \setminus \{i\}} (-\alpha_u)(\alpha_i - \alpha_u)^{-1} \bmod q$，构造补偿密钥项 $\kappa_{i,j}^{(t)}$ 并上传补偿密文 $\delta_{i,j}^{(t)}$：
$$\kappa_{i,j}^{(t)} = \biggl[\, \widehat{\lambda}_i^{(t)} \sum_{k \notin \widehat{\mathcal{S}}^{(t)}} s_{k,i} - \lambda_i^{(t)} \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_{k,i} + \bigl(\widehat{\lambda}_i^{(t)} - \lambda_i^{(t)}\bigr) b_j^{(t)} z_i \,\biggr]_q \tag{D5.2}$$
$$\delta_{i,j}^{(t)} = \Bigl[\, a_j^{(t)} \cdot \kappa_{i,j}^{(t)} + \tilde{p} \cdot \hat{e}_{i,j}^{(t)} \,\Bigr]_q \tag{D5.3}$$

#### 第 2 步：计算单个存活客户端 $i \in \widehat{\mathcal{S}}^{(t)}$ 的密文之和 $\mathrm{ct}_{i,j}^{(t)} + \delta_{i,j}^{(t)}$
将式 (D4.2) 的 $\mathrm{ct}_{i,j}^{(t)}$ 与式 (D5.3) 的 $\delta_{i,j}^{(t)}$ 相加：
$$\begin{aligned}
\mathrm{ct}_{i,j}^{(t)} + \delta_{i,j}^{(t)}
&\equiv \Bigl( a_j^{(t)} \cdot \tilde{s}_{i,j}^{(t)} + \tilde{p} \cdot e_{i,j}^{(t)} + \mathrm{pt}_{i,j}^{(t)} \Bigr) + \Bigl( a_j^{(t)} \cdot \kappa_{i,j}^{(t)} + \tilde{p} \cdot \hat{e}_{i,j}^{(t)} \Bigr) \pmod q \\
&\equiv a_j^{(t)} \cdot \Bigl( \tilde{s}_{i,j}^{(t)} + \kappa_{i,j}^{(t)} \Bigr) + \tilde{p} \cdot \bigl( e_{i,j}^{(t)} + \hat{e}_{i,j}^{(t)} \bigr) + \mathrm{pt}_{i,j}^{(t)} \pmod q
\end{aligned} \tag{D5.4}$$

#### 第 3 步：展开单个客户端的密钥之和 $\tilde{s}_{i,j}^{(t)} + \kappa_{i,j}^{(t)}$，验证旧 $\lambda_i^{(t)}$ 项的精确抵消
将式 (D4.1) 的 $\tilde{s}_{i,j}^{(t)}$ 和式 (D5.2) 的 $\kappa_{i,j}^{(t)}$ 代入 $\tilde{s}_{i,j}^{(t)} + \kappa_{i,j}^{(t)}$，并将 $\bigl(\widehat{\lambda}_i^{(t)} - \lambda_i^{(t)}\bigr) b_j^{(t)} z_i$ 展开为 $\widehat{\lambda}_i^{(t)} b_j^{(t)} z_i - \lambda_i^{(t)} b_j^{(t)} z_i$：
$$\begin{aligned}
\tilde{s}_{i,j}^{(t)} + \kappa_{i,j}^{(t)}
&\equiv \Biggl( s_i + \underline{\lambda_i^{(t)} \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_{k,i}} + \underline{\underline{\lambda_i^{(t)} b_j^{(t)} z_i}} \Biggr) \\
&\quad + \Biggl( \widehat{\lambda}_i^{(t)} \sum_{k \notin \widehat{\mathcal{S}}^{(t)}} s_{k,i} - \underline{\lambda_i^{(t)} \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_{k,i}} + \widehat{\lambda}_i^{(t)} b_j^{(t)} z_i - \underline{\underline{\lambda_i^{(t)} b_j^{(t)} z_i}} \Biggr) \pmod q
\end{aligned}$$
观察上式：
- 带单下划线的两项：$+\lambda_i^{(t)} \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_{k,i}$ 与 $-\lambda_i^{(t)} \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_{k,i}$ 一正一负，**完全抵消为 $0$**；
- 带双下划线的两项：$+\lambda_i^{(t)} b_j^{(t)} z_i$ 与 $-\lambda_i^{(t)} b_j^{(t)} z_i$ 一正一负，**完全抵消为 $0$**。

于是，单个存活客户端 $i \in \widehat{\mathcal{S}}^{(t)}$ 的修正后密钥简化为：
$$\tilde{s}_{i,j}^{(t)} + \kappa_{i,j}^{(t)} \equiv s_i + \widehat{\lambda}_i^{(t)} \sum_{k \notin \widehat{\mathcal{S}}^{(t)}} s_{k,i} + \widehat{\lambda}_i^{(t)} b_j^{(t)} z_i \pmod q \tag{D5.5}$$

#### 第 4 步：对所有存活客户端 $i \in \widehat{\mathcal{S}}^{(t)}$ 求和并交换双重求和次序（式 (15)）
将式 (D5.5) 对 $i \in \widehat{\mathcal{S}}^{(t)}$ 求和：
$$\begin{aligned}
\sum_{i \in \widehat{\mathcal{S}}^{(t)}} \bigl(\tilde{s}_{i,j}^{(t)} + \kappa_{i,j}^{(t)}\bigr)
&\equiv \sum_{i \in \widehat{\mathcal{S}}^{(t)}} s_i + \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \Biggl( \widehat{\lambda}_i^{(t)} \sum_{k \notin \widehat{\mathcal{S}}^{(t)}} s_{k,i} \Biggr) + \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \bigl(\widehat{\lambda}_i^{(t)} b_j^{(t)} z_i\bigr) \pmod q \\
&\equiv \sum_{i \in \widehat{\mathcal{S}}^{(t)}} s_i + \sum_{k \notin \widehat{\mathcal{S}}^{(t)}} \Biggl( \underbrace{\sum_{i \in \widehat{\mathcal{S}}^{(t)}} \widehat{\lambda}_i^{(t)} s_{k,i}}_{=\, F_k(0) \,=\, s_k \text{（由 D2.4）}} \Biggr) + b_j^{(t)} \cdot \Biggl( \underbrace{\sum_{i \in \widehat{\mathcal{S}}^{(t)}} \widehat{\lambda}_i^{(t)} z_i}_{=\, \Psi(0) \,=\, 0 \text{（由 D2.4）}} \Biggr) \pmod q \\
&\equiv \sum_{i \in \widehat{\mathcal{S}}^{(t)}} s_i + \sum_{k \notin \widehat{\mathcal{S}}^{(t)}} s_k + 0 \equiv \sum_{u=1}^N s_u = S \pmod q
\end{aligned} \tag{D5.6}$$
将式 (D5.6) 代入式 (D5.4) 对 $i \in \widehat{\mathcal{S}}^{(t)}$ 的总和，即得异步掉线补偿聚合公式（式 (15)）：
$$\begin{aligned}
C_j^{(t)} &= \Biggl[ \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \Bigl( \mathrm{ct}_{i,j}^{(t)} + \delta_{i,j}^{(t)} \Bigr) \Biggr]_q \\
&= \Biggl[ a_j^{(t)} \cdot \underbrace{\sum_{i \in \widehat{\mathcal{S}}^{(t)}} \bigl(\tilde{s}_{i,j}^{(t)} + \kappa_{i,j}^{(t)}\bigr)}_{=\, S} + \tilde{p} \cdot \underbrace{\sum_{i \in \widehat{\mathcal{S}}^{(t)}} \bigl(e_{i,j}^{(t)} + \hat{e}_{i,j}^{(t)}\bigr)}_{=\, \widehat{E}_j^{(t)}} + \underbrace{\sum_{i \in \widehat{\mathcal{S}}^{(t)}} \mathrm{pt}_{i,j}^{(t)}}_{=\, \mathrm{pt}_j^{(t)}} \Biggr]_q \\
&= \Bigl[\, a_j^{(t)} \cdot S + \tilde{p} \cdot \widehat{E}_j^{(t)} + \mathrm{pt}_j^{(t)} \,\Bigr]_q
\end{aligned} \tag{D5.7}$$

---

### 推导 6：Phase 4 跨轮密文预取累加与一步本地解密（Section IV-D2，式 (16)–(17) 零跳步推导）

1. **跨轮密文同态累加（式 (16)）**：
   由式 (D4.8) 和式 (D5.7) 可知，无论第 $r$ 轮是同步完成还是经历掉线补偿，其包 $j \in \mathcal{K}^{(r)}$ 的聚合密文均具有统一形式：
   $$C_j^{(r)} = \Bigl[\, a_j^{(r)} \cdot S + \tilde{p} \cdot E_j^{(r)} + \mathrm{pt}_j^{(r)} \,\Bigr]_q$$
   （若第 $r$ 轮有掉线，则 $E_j^{(r)} = \widehat{E}_j^{(r)}$）。
   设重参训客户端 $i \in \mathcal{S}^{(t)}$ 对包 $j$ 缓存的缺失轮次索引集为 $\mathcal{H}_{i,j} = \{r \mid (r, C_j^{(r)}) \in \mathcal{L}_{i,j}\}$。客户端对 $r \in \mathcal{H}_{i,j}$ 执行模 $q$ 同态加法：
   $$\begin{aligned}
   C_{\mathrm{pre},j} &= \mathrm{HE.Eval}\Bigl(\bigl\{C_j^{(r)}\bigr\}_{r \in \mathcal{H}_{i,j}}\Bigr) = \Biggl[ \sum_{r \in \mathcal{H}_{i,j}} C_j^{(r)} \Biggr]_q \\
   &= \Biggl[ \sum_{r \in \mathcal{H}_{i,j}} \Bigl( a_j^{(r)} \cdot S + \tilde{p} \cdot E_j^{(r)} + \mathrm{pt}_j^{(r)} \Bigr) \Biggr]_q \\
   &= \Biggl[ \sum_{r \in \mathcal{H}_{i,j}} \bigl(a_j^{(r)} \cdot S\bigr) + \sum_{r \in \mathcal{H}_{i,j}} \bigl(\tilde{p} \cdot E_j^{(r)}\bigr) + \sum_{r \in \mathcal{H}_{i,j}} \mathrm{pt}_j^{(r)} \Biggr]_q
   \end{aligned}$$
   由于全局解密密钥 $S$ 与轮次下标 $r$ 无关，利用环乘法右分配律将 $S$ 提取到第一项求和号右侧：
   $$\begin{aligned}
   C_{\mathrm{pre},j} &= \Biggl[ \underbrace{\Biggl( \sum_{r \in \mathcal{H}_{i,j}} a_j^{(r)} \Biggr)}_{\equiv\, A_{\mathrm{pre},j} \pmod q} \cdot S + \tilde{p} \cdot \underbrace{\Biggl( \sum_{r \in \mathcal{H}_{i,j}} E_j^{(r)} \Biggr)}_{=\, E_{\mathrm{pre},j}} + \underbrace{\sum_{r \in \mathcal{H}_{i,j}} \mathrm{pt}_j^{(r)}}_{=\, \mathrm{pt}_{\mathrm{pre},j}} \Biggr]_q \\
   &= \Bigl[\, A_{\mathrm{pre},j} \cdot S + \tilde{p} \cdot E_{\mathrm{pre},j} + \mathrm{pt}_{\mathrm{pre},j} \,\Bigr]_q
   \end{aligned} \tag{D6.1}$$

2. **客户端一步本地解密与解码（式 (17)）**：
   客户端利用种子 $\sigma_a$ 生成各缺失轮次的 $a_j^{(r)} = \mathrm{HE.PRPG}(\sigma_a, r \parallel j)$ 并求和得到 $A_{\mathrm{pre},j} = \bigl[\sum_{r \in \mathcal{H}_{i,j}} a_j^{(r)}\bigr]_q$，然后用全局密钥 $S$ 执行一步解密：
   $$\begin{aligned}
   \mathrm{HE.Dec}\bigl(A_{\mathrm{pre},j}, S, C_{\mathrm{pre},j}\bigr)
   &= \Bigl[\bigl[\, C_{\mathrm{pre},j} - A_{\mathrm{pre},j} \cdot S \,\bigr]_q\Bigr]_p \\
   &= \Bigl[\bigl[\, \bigl(A_{\mathrm{pre},j} \cdot S + \tilde{p} \cdot E_{\mathrm{pre},j} + \mathrm{pt}_{\mathrm{pre},j}\bigr) - A_{\mathrm{pre},j} \cdot S \,\bigr]_q\Bigr]_p \\
   &= \Bigl[\bigl[\, \tilde{p} \cdot E_{\mathrm{pre},j} + \mathrm{pt}_{\mathrm{pre},j} \,\bigr]_q\Bigr]_p
   \end{aligned}$$
   当满足 $\|\tilde{p} E_{\mathrm{pre},j} + \mathrm{pt}_{\mathrm{pre},j}\|_\infty < q/2$ 且 $p \mid \tilde{p}$ 时，内层 $[\cdot]_q$ 无回绕，外层 $[\cdot]_p$ 消去 $\tilde{p} E_{\mathrm{pre},j}$，精确恢复：
   $$\mathrm{pt}_{\mathrm{pre},j} = \sum_{r \in \mathcal{H}_{i,j}} \mathrm{pt}_j^{(r)} = \sum_{r \in \mathcal{H}_{i,j}} \sum_{u \in \widehat{\mathcal{S}}^{(r)}} \mathrm{Ecd}\bigl(\omega_u^{(r)} \mathbf{x}_{u,j}^{(r)}, \Delta\bigr) \tag{D6.2}$$
   由于编码映射 $\mathrm{Ecd}(\cdot, \Delta)$ 与解码映射 $\mathrm{Dcd}(\cdot, \Delta) = \Delta^{-1} \varphi(\cdot)$ 均为线性映射，客户端只需调用一次 $\mathrm{Dcd}(\mathrm{pt}_{\mathrm{pre},j}, \Delta)$ 即可恢复多轮累积浮点更新：
   $$\tilde{\mathbf{g}}_{\mathrm{pre},j} = \mathrm{Dcd}\bigl(\mathrm{pt}_{\mathrm{pre},j}, \Delta\bigr) = \sum_{r \in \mathcal{H}_{i,j}} \mathrm{Dcd}\bigl(\mathrm{pt}_j^{(r)}, \Delta\bigr) = \sum_{r \in \mathcal{H}_{i,j}} \tilde{\mathbf{g}}_j^{(r)} \tag{D6.3}$$

---

## 第三部分：最新定稿版全篇论文英文正文（Abstract 至 Section VII）

> 以下内容与最新编译的 `ECPFL_Clean_Submission.pdf` 完全一致。

### Title & Abstract

**Title:**
**ECPFL: Efficient Ciphertext Prefetching for Secure Cross-Device Federated Learning**

**Abstract:**
Cross-device federated learning (FL) is hindered by the substantial communication burden between a central server and heterogeneous, bandwidth-limited edge devices. While upstream sparsification and downstream prefetching each provide partial relief, integrating them into homomorphically encrypted FL creates a fundamental structural conflict: naively encrypting dynamically sparsified updates destroys the strict spatial alignment required by Single Instruction Multiple Data (SIMD) operations and leaves multi-key aggregation vulnerable to upload-phase client dropouts. To address these issues, we propose ECPFL, a secure aggregation framework built on Cheon-Kim-Kim-Song (CKKS) homomorphic encryption that extends one-step aggregate decryption to partial participation and upload-phase dropout scenarios without any peer-to-peer client communication, while jointly reducing upstream and downstream communication. First, we develop Efficient Sparse Packing (ESP), which combines a Shamir zero-sharing-based secure voting mechanism that aligns selected parameter packs across clients with a dropout-resilient key-compensation mechanism that restores the exact aggregate encryption key contribution under fixed active-set aggregation weights without exchanging decryption shares. Building on this, we introduce Efficient Ciphertext Prefetching (ECP), which lets intermittently available clients asynchronously download and accumulate sparse encrypted model updates during idle periods and recover the missed global updates through one local decryption per accumulated pack, substantially reducing synchronization latency while protecting individual updates against an honest-but-curious server and colluding client subsets. Comprehensive evaluations on MNIST, Fashion-MNIST, CIFAR-10, and SVHN demonstrate that ECPFL preserves baseline model accuracy while reducing the online communication volume by up to $10.7\times$ and accelerating end-to-end training time by up to $5.7\times$ over compared baselines.

**IEEEkeywords:**
Federated learning, homomorphic encryption, ciphertext prefetching, sparse packing, voting mechanism, dropout resilience

---

### Section I. Introduction

Federated learning (FL) has become a popular way to train shared models without moving raw data off personal devices~\cite{bonawitz2019towards}. Extending FL to the edge, cross-device FL connects millions of smartphones, wearables, and Internet of Things (IoT) devices, letting each device help train the model locally. By processing data where it is generated, this method is well-suited to privacy-sensitive applications and has driven progress in areas like healthcare~\cite{zhang2022homomorphic}, finance~\cite{li2020federated}, and smart edge computing~\cite{rahman2026tackling}. However, as shown in Fig.~\ref{fig:background}, cross-device FL must coordinate heterogeneous edge devices over unstable, bandwidth-constrained links and non-IID local datasets~\cite{ye2025breaking}, \cite{he2025ace}, \cite{wang2026heterogeneous}.

A primary bottleneck in cross-device FL is bidirectional communication overhead between edge devices and the server~\cite{kairouz2021advances}, \cite{wu2024security}. To ease this burden, two main strategies have been studied: sampling only a portion of devices to join in each round~\cite{cho2022towards}, \cite{li2025fedphe}, \cite{chai2020tifl}, \cite{wolfrath2022haccs}, \cite{lai2021oort}, \cite{he2023gluefl}, and compressing the updates using techniques like quantization~\cite{liu2024dynamic}, sparsification~\cite{xu2025harnessing}, low-rank decomposition~\cite{dong2023privacy}, or sketching~\cite{rothchild2020fetchsgd}. Yet, recent studies~\cite{yan2025fedfetch} show that if device sampling is combined with compressed downloads, the benefits can disappear: devices that skip some rounds end up with outdated models and must download large updates to catch up, making the total communication almost as large as full-model transmission after a few rounds.

Privacy leakage is another significant challenge in cross-device FL. Studies show that exchanging gradients or model updates does not ensure privacy, as adversaries can reconstruct sensitive information from these updates~\cite{zhu2019deep}, \cite{geiping2020inverting}, \cite{zhao2020idlg}, \cite{guo2025exploring}. To counteract this, three main privacy-preserving strategies have emerged: differential privacy (DP)~\cite{mcmahan2017learning}, secure multi-party computation (SMPC)~\cite{bonawitz2017practical}, and homomorphic encryption (HE)~\cite{gentry2009fully}. HE, in particular, provides strong cryptographic protection for secure aggregation by enabling computation on encrypted data. The Cheon-Kim-Kim-Song (CKKS) scheme~\cite{cheon2017homomorphic}, built on the Ring Learning With Errors (RLWE) assumption~\cite{lyubashevsky2010ideal}, is well-suited for machine learning tasks, supporting approximate arithmetic and Single Instruction Multiple Data (SIMD) packing. Utilizing SIMD packing, CKKS minimizes per-ciphertext costs and increases throughput compared to slot-wise encryption~\cite{cheon2018bootstrapping}. Recent advances~\cite{li2025fedphe}, \cite{wu2025esafl} have adopted CKKS packing for efficient secure aggregation, reducing upstream ciphertext size through sparsification and compact single-ring-element polynomial encoding. Multi-key HE (MKHE) extensions further allow aggregation across ciphertexts encrypted with different client keys, without requiring server-side decryption~\cite{cai2023secfed}.

However, existing HE-based FL systems focus predominantly on upstream compression, treating the downstream transmission of encrypted global models as an inherent and unavoidable cost. Plaintext FL frameworks mitigate this latency by prefetching updates during idle periods, but extending this mechanism to the ciphertext domain introduces fundamental algebraic constraints: packed homomorphic ciphertexts are indivisible, so encrypted payloads cannot be partitioned or transmitted in fragments without severe dimensional expansion and decryption overhead. This rigidity creates a downstream transmission bottleneck, which is further compounded by the structural misalignment and dropout sensitivity of upstream sparsification. Specifically, pack-level sparsification~\cite{sattler2019sparse}, \cite{sattler2019robust} disrupts the SIMD slot alignment required for joint decryption in MKHE, while upload-phase dropouts---even after active clients are confirmed in the voting phase---leave missing key shares that break Lagrange interpolation and prevent direct one-step decryption. Existing remedies rely on Trusted Execution Environments (TEEs)~\cite{cai2023secfed}, online auxiliary servers~\cite{yuan2026fedout}, or interactive peer-to-peer decryption-share exchanges, all of which introduce extra trust assumptions or communication bottlenecks.

To address these limitations, we propose \textsc{ECPFL}, a secure and communication-efficient FL framework that extends one-step aggregate decryption to partial participation and upload-phase dropout scenarios through two integrated mechanisms: Efficient Sparse Packing (ESP) and Efficient Ciphertext Prefetching (ECP). By integrating Shamir secret sharing over cyclotomic rings into a compact single-ring-element encryption structure~\cite{wu2025esafl}, \textsc{ECPFL} eliminates peer-to-peer client communication during training. Upstream, \textsc{ESP} integrates a Shamir zero-sharing-based secure voting mechanism to align selected parameter packs with a dropout-resilient key-compensation mechanism in which surviving clients locally supply compensation ciphertexts to restore the exact aggregate encryption key contribution under fixed active-set weights. Downstream, as depicted in Fig.~\ref{fig:background}, \textsc{ECP} exploits the additive homomorphism of encrypted model updates to allow intermittently participating clients to asynchronously download and accumulate sparse ciphertexts during idle periods, recovering multiple rounds of global updates through a single local decryption operation.

We summarize our core contributions as follows:
- We propose \textsc{ECPFL}, a client--server secure aggregation framework that supports partial participation and upload-phase dropouts without peer-to-peer client interaction. An offline KGC distributes Shamir shares once during setup, and surviving clients locally reconstruct the exact aggregate encryption key contribution via one-round compensation ciphertexts, enabling non-interactive one-step aggregate decryption.
- We design \textsc{ESP}, which co-designs Shamir zero-sharing-based pack-level consensus voting with masked Lagrange key-share embedding in a single-ring-element ciphertext structure. \textsc{ESP} resolves SIMD slot misalignment and upload-phase key mismatches under fixed active-set weights while protecting individual updates and vote bitmaps against an honest-but-curious server and up to $\kappa \le \tau - 2$ colluding clients.
- We develop \textsc{ECP}, which extends asynchronous update prefetching to the ciphertext domain for intermittently participating clients. By homomorphically accumulating sparse round-level ciphertexts over $\mathcal{R}_q$ during idle windows, rejoining clients synchronize multi-round updates via a single local decryption per pack without exposing plaintexts to the server.
- We evaluate \textsc{ECPFL} on four datasets under heterogeneous and non-IID settings. \textsc{ECPFL} maintains accuracy within a small margin of the dense baseline while reducing the online communication volume by up to $10.7\times$ and the end-to-end training time by up to $5.7\times$ compared with state-of-the-art baselines.

---

### Section II. Related Work

We review the related work from the following five aspects:

**Multi-Key Homomorphic Encryption in FL:** HE provides a mathematically rigorous foundation for privacy-preserving FL. Single-key CKKS schemes, such as FedSHE~\cite{pan2024fedshe} and FedPHE~\cite{li2025fedphe}, support approximate arithmetic and ciphertext packing, but rely on a globally shared secret key, leaving the system vulnerable to honest-but-curious clients. MKHE mitigates this risk by enabling independent key pairs per client~\cite{chen2019efficient}, \cite{damgaard2012multiparty}, \cite{wu2025secure}. For example, ESAFL~\cite{wu2025esafl} packs multiple encoded message polynomials into a single ring element and achieves one-step decryption without exchanging decryption shares, but as a cross-silo framework it fundamentally requires full client participation. In contrast, MASER~\cite{al2025maser} aligns sparse masks via majority voting yet still requires decryption-share transmission, while FedOut~\cite{yuan2026fedout} achieves dropout resilience through two non-colluding online servers. Overall, existing MKHE schemes either mandate full participation or incur interactive decryption-share overhead, failing to simultaneously support partial client sampling, upload-phase dropouts, and non-interactive one-step decryption in cross-device FL.

**Threshold Homomorphic Encryption in FL:** Threshold HE employs Shamir secret sharing to distribute secret keys, allowing any qualified client subset to restore missing key contributions. Mouchet *et al.*~\cite{mouchet2023threshold} instantiated RLWE threshold access structures over $\mathcal{R}_q$ using constant integer evaluation points, while ATASSES~\cite{chang2025atasses} and CDKS-LSS~\cite{wang2026cdks} studied approximate secret sharing and exceptional sequences over cyclotomic rings to guarantee invertible Lagrange interpolation. More recently, Colin de Verdière *et al.*~\cite{colin2026tfhesd} formalized synchronous threshold FHE and proved that unmasked Lagrange weighting leaks secret keys across different participant sets; Kim *et al.*~\cite{kim2026tfhead} then mitigated this leakage using ring-based Shamir zero-sharing in the asynchronous setting. However, these schemes all perform key restoration during interactive online decryption, which exposes the plaintext aggregate to the server and incurs additional communication rounds. Embedding masked threshold key-contribution restoration directly into upstream encryption for non-interactive one-step decryption remains unexplored.

**Gradient Compression:** To alleviate the communication bottleneck in FL, various gradient compression techniques have been proposed, including quantization~\cite{alistarh2017qsgd}, \cite{bao2025efskip}, low-rank decomposition~\cite{richtarik2024error}, \cite{dorfman2023docofl}, and sparsification~\cite{haddadpour2021federated}, \cite{kumar2023noniid}, \cite{kim2024spafl}. Among these, Top-$k$ sparsification with residual compensation~\cite{stich2018sparsified} has proven highly effective. For encrypted FL, DSVFL~\cite{li2025enhancing} introduced FTop-$k$, utilizing an accumulable residual buffer to recover accuracy. However, DSVFL applies sparsification before Paillier encryption, strictly limiting downstream homomorphic operations to simple addition, whereas heterogeneous top-index selections across clients destroy SIMD slot alignment in packed CKKS ciphertexts and leak local gradient structures~\cite{xu2025harnessing}, \cite{liu2021flame}.

**Downstream Prefetching:** In cross-device environments with high heterogeneity, synchronizing stale local models often offsets the bandwidth benefits achieved through client sampling and compression. To address this synchronization delay, FedFetch~\cite{yan2025fedfetch} introduces an adaptive downstream prefetching strategy in which the server presamples future participants with over-commitment and schedules background downloads of compressed updates during client idle windows. However, FedFetch operates exclusively on plaintext updates, only handles pre-round unavailability rather than upload-phase dropouts after active-set confirmation, and cannot directly accumulate or decrypt packed multi-round ciphertexts without severe noise accumulation and repeated decryption latency.

**Client Selection:** Client selection is the strategy by which the server chooses the active participating subset at each round, critically determining both convergence speed and training time in cross-device FL. Uniform Random selection~\cite{mcmahan2017communication} ignores system heterogeneity and allows slow clients to stall training; recent frameworks therefore introduce targeted selection criteria, including Power-of-Choice (PoC)~\cite{cho2022towards}, tier-based selection (TiFL)~\cite{chai2020tifl}, heterogeneity-aware clustered selection (HACCS)~\cite{wolfrath2022haccs}, and utility-guided selection (Oort)~\cite{lai2021oort}. Furthermore, GlueFL~\cite{he2023gluefl} employs a Sticky sampling strategy that prioritizes recently active clients with fresh local models, while FedPHE~\cite{li2025fedphe} integrates CKKS with locality-sensitive hashing (LSH)-based Sketch-Clustering. Yet, biased selection can skew global representation under non-independent and identically distributed (non-IID) data, and existing encrypted selection methods still force newly sampled clients to synchronously download full encrypted models upon joining.

---

### Section III. Preliminaries and Motivation

#### III-A. Notations
Table~\ref{tab:notations} summarizes the primary notations used to formalize the \textsc{ECPFL} architecture. In the context of our SIMD homomorphic operations, we use the terms *pack* and *batch* interchangeably to represent a vector of scalars embedded into a single polynomial ring element.

| Notation | Description | Notation | Description |
| :--- | :--- | :--- | :--- |
| $\mathcal{C}, N$ | Registered client set $[N] = \{1,\dots,N\}$ and client count | $\mathbf{W}^{(t)}, \mathbf{w}_i^{(t)}$ | Global model and local model of client $i$ at round $t$ |
| $\mathcal{P}^{(t)}, \mathcal{S}^{(t)}$ | Presampled candidate pool and confirmed active set | $\Delta\mathbf{w}_i^{(t)}, \mathbf{r}_i^{(t)}$ | Local model increment ($\mathbf{w}_i^{(t)} - \mathbf{W}^{(t)}$) and residual buffer |
| $\widehat{\mathcal{S}}^{(t)}, \mathcal{D}^{(t)}$ | Surviving Phase-2 uploader set and upload-phase dropout set | $\mathbf{x}_i^{(t)}, \tilde{\mathbf{g}}_i^{(t)}$ | Compensated update and weighted update ($\omega_i^{(t)} \mathbf{x}_i^{(t)}$) |
| $\bar{\mathcal{S}}^{(t)}$ | Unselected inactive client set ($\mathcal{C} \setminus \mathcal{S}^{(t)}$) | $\omega_i^{(t)}, J$ | Fixed active-set weight over $\mathcal{S}^{(t)}$ and total pack count |
| $\mathcal{R}_q, \Delta$ | Ciphertext polynomial ring $\mathbb{Z}_q[X]/(X^n+1)$ and scaling factor | $\mathbf{v}_i^{(t)}, \hat{v}_i^{(t)}$ | Binary pack-vote vector and masked vote polynomial |
| $S, s_i$ | Global aggregate decryption key and secret key of client $i$ | $V^{(t)}(X), \mathcal{K}^{(t)}$ | Aggregated vote polynomial and consensus pack index set |
| $\sigma_a, \sigma_b$ | Pseudorandom seeds for pack-CRP and masking polynomials | $\mathrm{pt}_{i,j}^{(t)}, \mathrm{ct}_{i,j}^{(t)}$ | Encoded plaintext polynomial and uploaded pack-$j$ ciphertext |
| $a_0^{(t)}, a_j^{(t)}, b_j^{(t)}$ | Voting public polynomial, pack-$j$ CRP, and masking polynomial | $\delta_{i,j}^{(t)}$ | Pure key-compensation ciphertext for pack $j$ |
| $s_{k,i}, z_i$ | Shamir share of $s_k$ held by client $i$ and zero-share of client $i$ | $C_j^{(t)}, \mathrm{pt}_j^{(t)}$ | Server-aggregated ciphertext and plaintext polynomial for pack $j$ |
| $\lambda_i^{(t)}, \widehat{\lambda}_i^{(t)}$ | Lagrange interpolation weights over $\mathcal{S}^{(t)}$ and $\widehat{\mathcal{S}}^{(t)}$ | $\tilde{\mathbf{g}}_j^{(t)}, \tilde{\mathbf{g}}_{\mathrm{pre}}$ | Decoded global pack-$j$ update and prefetched model increment |
| $\tilde{s}_{i,j}^{(t)}, \kappa_{i,j}^{(t)}$ | Effective encryption key and dropout compensation key term | $C_{\mathrm{pre},j}, A_{\mathrm{pre},j}$ | Cross-round accumulated ciphertext and public polynomial |

#### III-B. Cross-Device Federated Learning
In cross-device FL, each client $i \in \mathcal{C} = [N]$ holds a private local dataset $\mathcal{D}_i$ of size $n_i = |\mathcal{D}_i|$ and trains a model with parameters $\mathbf{w} \in \mathbb{R}^d$. At round $t$, the server selects $K = |\mathcal{S}^{(t)}|$ active clients $\mathcal{S}^{(t)} \subseteq \mathcal{C}$, with inactive set $\bar{\mathcal{S}}^{(t)} = \mathcal{C} \setminus \mathcal{S}^{(t)}$ and surviving uploader set $\widehat{\mathcal{S}}^{(t)} = \mathcal{S}^{(t)} \setminus \mathcal{D}^{(t)}$ after upload-phase dropouts $\mathcal{D}^{(t)}$. Starting from $\mathbf{W}^{(t)}$, each active client $i \in \mathcal{S}^{(t)}$ runs $\mathcal{E}$ local optimization epochs on $\mathcal{D}_i$ to obtain $\mathbf{w}_i^{(t)}$ and computes its local model increment $\Delta \mathbf{w}_i^{(t)} = \mathbf{w}_i^{(t)} - \mathbf{W}^{(t)}$. This state-subtraction formulation abstracts away optimizer-specific internal states and enables pure additive synchronization. Upon confirming the active set $\mathcal{S}^{(t)}$ in Phase~1, each active client $i \in \mathcal{S}^{(t)}$ is assigned a fixed aggregation weight $\omega_i^{(t)} = n_i / \sum_{u \in \mathcal{S}^{(t)}} n_u$ satisfying $\sum_{i \in \mathcal{S}^{(t)}} \omega_i^{(t)} = 1$. The server aggregates the weighted increments from the surviving uploaders $\widehat{\mathcal{S}}^{(t)}$ to update the global model:
$$\mathbf{W}^{(t+1)} = \mathbf{W}^{(t)} + \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \omega_i^{(t)} \Delta\mathbf{w}_i^{(t)}, \quad (1)$$
which preserves the pre-committed client weights $\omega_i^{(t)}$ without requiring plaintext weight renormalization when upload-phase dropouts occur ($\widehat{\mathcal{S}}^{(t)} \subset \mathcal{S}^{(t)}$), and reduces to standard full active-set aggregation when $\widehat{\mathcal{S}}^{(t)} = \mathcal{S}^{(t)}$.

In practice, cross-device FL faces constrained upload and download bandwidth, frequent upload-phase client dropouts, severe device heterogeneity, and non-IID local data distributions.

#### III-C. CKKS Encoding and Additive Encryption
Our scheme builds upon CKKS slot encoding~\cite{cheon2017homomorphic} and the compact single-ring-element RLWE multi-key additively homomorphic encryption construction of ESAFL~\cite{wu2025esafl}, integrated with Shamir secret sharing over cyclotomic rings~\cite{shamir1979how}, \cite{mouchet2023threshold}, \cite{colin2026tfhesd} for privacy-preserving aggregation.

**1) Ring Learning With Errors (RLWE):**
The security of CKKS relies on the decisional RLWE (dRLWE) assumption~\cite{lyubashevsky2010ideal}. Let $\mathcal{R} = \mathbb{Z}[X]/(X^n + 1)$ denote the cyclotomic ring where the ring degree $n$ is a power of two, and let $\mathcal{R}_q = \mathbb{Z}_q[X]/(X^n + 1)$ be its residue ring modulo $q$. We define $\chi_s$ and $\chi_e$ as error distributions over $\mathcal{R}$ that output small polynomials with infinity norms strictly bounded by $B_s$ and $B_e$, respectively, and let $\mathcal{U}(X)$ denote the uniform distribution over a finite set $X$. The dRLWE assumption states that paired samples $(\mathbf{b}, \mathbf{a}) \in \mathcal{R}_q^2$, formulated as $\mathbf{b} = [-\mathbf{a} \cdot s + e]_q$ where the mask $\mathbf{a} \leftarrow \mathcal{U}(\mathcal{R}_q)$ is uniform alongside a secret $s \leftarrow \chi_s$ and an error $e \leftarrow \chi_e$, are computationally indistinguishable from truly random pairs sampled uniformly from $\mathcal{U}(\mathcal{R}_q^2)$.

**2) CKKS Encoding and Slot Packing:**
CKKS utilizes an isometric ring isomorphism $\varphi: \mathbb{R}[X]/(X^n+1) \rightarrow \mathbb{C}^{n/2}$ to map real or complex valued vectors into integral coefficient polynomials. This mapping enables slot packing, where the encoding function $\mathrm{Ecd}(\cdot, \Delta)$ transforms a vector $\mathbf{z} \in \mathbb{C}^{n/2}$ into a plaintext polynomial $m(X) \in \mathcal{R}_q$ using a precision scaling factor $\Delta > 1$:
$$m(X) = \mathrm{Ecd}(\mathbf{z}, \Delta) = \lfloor \Delta \cdot \varphi^{-1}(\mathbf{z}) \rceil \in \mathcal{R}_q. \quad (2)$$
This approach facilitates SIMD batching by packing $n/2$ independent scalar values into a single ciphertext (splitting a $d$-dimensional model into $J = \lceil 2d/n \rceil$ packs) while supporting coefficient-wise embedding for binary vote vectors. Finally, the decoding function $\mathrm{Dcd}(\cdot, \Delta)$ approximately recovers the encoded vector $\mathbf{z}$ via:
$$\mathbf{z} = \mathrm{Dcd}(m(X), \Delta) = \Delta^{-1} \cdot \varphi(m(X)). \quad (3)$$

**3) Additive Encryption and Secret Sharing:**
\textsc{ECPFL} employs a multi-key additively homomorphic encryption (AHE) scheme built upon RLWE, following the efficient single-ring-element construction of~\cite{wu2025esafl}. Each client $i$ possesses its own encryption key $s_i$, while the aggregate decryption key is the sum of all key shares.

**Key Generation ($\mathrm{HE.KeyGen}$).** The key generation algorithm outputs $N$ encryption keys $s_i$, an aggregate decryption key $S$, and a secret seed $\sigma_a$ (alongside a secondary masking seed $\sigma_b$). The $N$ encryption keys $s_i$ are independently sampled from $\mathcal{U}(\mathcal{R}_q)$. The aggregate decryption key is $S = \bigl[\sum_{i=1}^{N} s_i\bigr]_q$.

**Encryption ($\mathrm{HE.Enc}$).** At round $t$, client $i$ encrypts the $j$-th batch plaintext polynomial $\mathrm{pt}_{i,j}^{(t)}$ using its encryption key $s_i$ and the public polynomial $a_j^{(t)} = \mathrm{HE.PRPG}(\sigma_a, t \parallel j)$ as:
$$\mathrm{ct}_{i,j}^{(t)} = \mathrm{HE.Enc}\bigl(a_j^{(t)}, s_i, \mathrm{pt}_{i,j}^{(t)}\bigr) = \Bigl[a_j^{(t)} \cdot s_i + \tilde{p} \cdot e_{i,j}^{(t)} + \mathrm{pt}_{i,j}^{(t)}\Bigr]_q, \quad (4)$$
where $e_{i,j}^{(t)} \leftarrow \chi_e$ and $\tilde{p}$ is a multiple of the plaintext modulus $p$ ($p \mid \tilde{p}$). Here, $a_j^{(t)} = \mathrm{HE.PRPG}(\sigma_a, t \parallel j)$ is the round- and pack-specific public polynomial derived from the pseudorandom polynomial generator ($\mathrm{HE.PRPG}$) with seed $\sigma_a$ and concatenation operator $\parallel$, and $[\cdot]_q$ denotes centered reduction modulo $q$ into $(-q/2, q/2]$.

**Multi-Pack Mask-Reuse Vulnerability.** In the original one-step decryption protocol~\cite{wu2025esafl}, reusing a single round-level polynomial $a^{(t)}$ across multiple packs $j_1 \neq j_2 \in [J]$ within the same round creates a severe *cross-pack key-cancellation vulnerability*: any curious client holding seed $\sigma_a$ can subtract two pack ciphertexts from the same client $i$ to cancel the secret key term $a^{(t)} \cdot s_i$ entirely, yielding $[\mathrm{ct}_{i,j_1}^{(t)} - \mathrm{ct}_{i,j_2}^{(t)}]_q = [\tilde{p}(e_{i,j_1}^{(t)} - e_{i,j_2}^{(t)}) + (\mathrm{pt}_{i,j_1}^{(t)} - \mathrm{pt}_{i,j_2}^{(t)})]_q$ and directly exposing the plaintext difference $(\mathrm{pt}_{i,j_1}^{(t)} - \mathrm{pt}_{i,j_2}^{(t)}) \bmod p$. Generating an independent $a_j^{(t)} = \mathrm{HE.PRPG}(\sigma_a, t \parallel j)$ per pack $j$ ensures $a_{j_1}^{(t)} \neq a_{j_2}^{(t)}$ and eliminates this cross-pack cancellation.

**Homomorphic Aggregation ($\mathrm{HE.Eval}$).** The evaluation algorithm $\mathrm{HE.Eval}$ adds $N$ ciphertexts $\{\mathrm{ct}_{i,j}^{(t)}\}_{i \in [N]}$ and outputs an aggregated ciphertext:
$$C_j^{(t)} = \mathrm{HE.Eval}\Bigl(\bigl\{\mathrm{ct}_{i,j}^{(t)}\bigr\}_{i \in [N]}\Bigr) = \Biggl[\sum_{i=1}^{N} \mathrm{ct}_{i,j}^{(t)}\Biggr]_q. \quad (5)$$
This operation enables the server to aggregate encrypted local updates without decryption. By expanding Eq.~(5) and substituting Eq.~(4), the aggregated ciphertext satisfies:
$$C_j^{(t)} = \Bigl[a_j^{(t)} \cdot S + \tilde{p} \cdot E_j^{(t)} + \mathrm{pt}_j^{(t)}\Bigr]_q, \quad (6)$$
where $E_j^{(t)} = \sum_{i=1}^{N} e_{i,j}^{(t)}$ and $\mathrm{pt}_j^{(t)} = \sum_{i=1}^{N} \mathrm{pt}_{i,j}^{(t)}$ are the aggregated error and plaintext polynomial, respectively. This linear structure enables one-step decryption without client interaction.

**One-Step Decryption ($\mathrm{HE.Dec}$)**~\cite{wu2025esafl}**.** The client can decrypt in a single step, without any interactive share-exchange protocol. Specifically, the decryption algorithm $\mathrm{HE.Dec}$ recovers the aggregated plaintext polynomial from $C_j^{(t)}$ for batch $j$ using the aggregate decryption key $S$:
$$\mathrm{pt}_j^{(t)} = \mathrm{HE.Dec}\bigl(a_j^{(t)}, S, C_j^{(t)}\bigr) = \Bigl[\bigl[C_j^{(t)} - a_j^{(t)} \cdot S\bigr]_q\Bigr]_p, \quad (7)$$
where $[\cdot]_{q,p} = [[\cdot]_q]_p$ denotes centered reduction modulo $q$ followed by modulo $p$. The modulo $p$ operation precisely eliminates the accumulated noise $\tilde{p} \cdot E_j^{(t)}$ (provided $p \mid \tilde{p}$ and $\|\tilde{p} \cdot E_j^{(t)} + \mathrm{pt}_j^{(t)}\|_\infty < q/2$), ensuring error-free polynomial decryption, after which the client applies $\tilde{\mathbf{g}}_j^{(t)} = \mathrm{Dcd}(\mathrm{pt}_j^{(t)}, \Delta)$ to recover the aggregated float update vector.

**Shamir Secret Sharing over $\mathcal{R}_q$**~\cite{shamir1979how}, \cite{mouchet2023threshold}, \cite{colin2026tfhesd}**.** In cross-device FL, partial participation ($\mathcal{S}^{(t)} \subset \mathcal{C}$) and upload-phase dropouts ($\mathcal{D}^{(t)} \neq \emptyset$) leave missing key shares $\{s_k\}_{k \notin \widehat{\mathcal{S}}^{(t)}}$, preventing direct one-step decryption via $S$. Following the practical threshold access-structure instantiation over $\mathcal{R}_q$ in~\cite{mouchet2023threshold}, we assign constant polynomial evaluation points $\alpha_i = i$ for $i \in [N]$ under an RNS modulus $q = \prod_{\ell=1}^{L} q_\ell$ whose prime factors all satisfy $q_\ell > N$ (e.g., $N \le 1000 < q_\ell$). Since every pairwise difference satisfies $0 < |\alpha_i - \alpha_j| < N < q_\ell$, we have $\gcd(\alpha_i - \alpha_j, q) = 1$, ensuring that $(\alpha_i - \alpha_j)^{-1} \bmod q$ is always invertible in $\mathcal{R}_q^{\times}$. For threshold $\tau$, each secret $s_k \in \mathcal{R}_q$ is shared via a degree-$(\tau-1)$ polynomial $F_k(x)$ with $F_k(0) = s_k$ as $s_{k,i} = F_k(\alpha_i)$, and a degree-$(\tau-1)$ zero-polynomial $\Psi(x)$ with $\Psi(0) = 0$ yields zero-shares $z_i = \Psi(\alpha_i)$. Any subset $\mathcal{S}^{(t)} \subseteq \mathcal{C}$ of size $|\mathcal{S}^{(t)}| \ge \tau$ interpolates $s_k = \bigl[\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} s_{k,i}\bigr]_q$ and $\bigl[\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} z_i\bigr]_q = 0$ via public Lagrange weights $\lambda_i^{(t)} = \prod_{u \in \mathcal{S}^{(t)} \setminus \{i\}} (-\alpha_u)(\alpha_i - \alpha_u)^{-1} \pmod q$.

#### III-D. Gradient Prefetching in FL
Prefetching mitigates communication latency in FL by strategically shifting downstream payload transfers to idle bandwidth periods. FedFetch~\cite{yan2025fedfetch} introduces a plaintext prefetching framework where an inactive client scheduled to re-participate after $R$ rounds downloads the plaintext global model updates $\Delta\mathbf{W}^{(t+r)} = \mathbf{W}^{(t+r+1)} - \mathbf{W}^{(t+r)}$ during idle periods. Extending this paradigm to the ciphertext domain requires inactive clients to prefetch and homomorphically accumulate the globally aggregated ciphertexts $C^{(t+r)}$ over the cyclotomic ring $\mathcal{R}_q$:
$$C_{\mathrm{pre}} = \Biggl[\sum_{r=0}^{R-1} C^{(t+r)}\Biggr]_q. \quad (8)$$
The additive closure of $\mathcal{R}_q$ enables bounded-dimension homomorphic summation, avoiding ciphertext expansion.

#### III-E. Motivation and Challenges
While plaintext frameworks like FedFetch~\cite{yan2025fedfetch} mitigate downstream latency by allowing clients to asynchronously prefetch compressed server updates, transmitting these unencrypted payloads inherently compromises privacy guarantees. Furthermore, attempting to realize end-to-end bidirectional efficiency in the MKHE domain through the pairing of upstream update sparsification and downstream ciphertext prefetching poses three structural challenges:
- **Q1 (Alignment Dilemma):** *Heterogeneous clients tend to select different important parameters, resulting in misaligned sparse indices. How can we align their selections to enable correct pack-wise ciphertext aggregation without leaking individual selection profiles?*
- **Q2 (Dropout Dilemma):** *Partial client sampling and upload-phase client dropouts leave missing key shares in multi-key aggregation, while unmasked Lagrange interpolation across varying participant subsets leaks secret keys. How can we restore the exact aggregate key contribution $a_j^{(t)}S$ across both synchronous and asynchronous participation settings without interactive decryption rounds?*
- **Q3 (Sparsity and Prefetching Paradox):** *CKKS ciphertext size is independent of plaintext sparsity, so sparse updates still incur full communication cost. How can we redesign pack-level packing and prefetching to turn algorithmic sparsity into real bandwidth savings with one-step local decryption?*

To address these challenges, we present \textsc{ECPFL}, combining ESP and ECP. ESP tackles Q1 and Q2 through a Shamir zero-sharing-based secure voting mechanism and a dropout-resilient and secure pack-level sparse ciphertext upload mechanism (Section~\ref{sec:vptopk}), and ECP tackles Q3 via pack-level prefetching and cross-round homomorphic accumulation (Section~\ref{sec:cipherfetch}).

---

### Section IV. Scheme Design

#### IV-A. Overview
Over $T$ rounds, following FedFetch~\cite{yan2025fedfetch}, the server presamples a candidate pool $\mathcal{P}^{(t)} \subseteq \mathcal{C}$ of size $\lceil \beta K \rceil$ (with over-commitment factor $\beta \ge 1$) $R$ rounds in advance to absorb pre-round stragglers. At round $t$, $K = |\mathcal{S}^{(t)}| \ge \tau$ responsive candidates form the confirmed active set $\mathcal{S}^{(t)} \subseteq \mathcal{P}^{(t)}$ for Phase-1 voting, while $\widehat{\mathcal{S}}^{(t)} \subseteq \mathcal{S}^{(t)}$ ($|\widehat{\mathcal{S}}^{(t)}| \ge \tau$) denotes the surviving clients that complete Phase-2 upload after upload-phase dropouts $\mathcal{D}^{(t)} = \mathcal{S}^{(t)} \setminus \widehat{\mathcal{S}}^{(t)}$, satisfying $\widehat{\mathcal{S}}^{(t)} \subseteq \mathcal{S}^{(t)} \subseteq \mathcal{P}^{(t)} \subseteq \mathcal{C}$.

**Protocol Details.** Fig.~\ref{fig:architecture} provides the architectural overview, and Alg.~\ref{alg:main} details the main procedure of \textsc{ECPFL}:
- **Phase 0: System Initialization.** The Key Generation Center (KGC) generates independent encryption keys $s_i \leftarrow \mathcal{U}(\mathcal{R}_q)$, a shared aggregate decryption key $S$, pseudorandom seeds $(\sigma_a, \sigma_b)$, Shamir key shares $\{s_{k,i}\}_{k=1}^N$, and a zero-share $z_i$. It incrementally distributes these parameters to clients through secure channels, erases the temporary sharing polynomials after delivery, and remains permanently offline thereafter.
- **Phase 1: Pack-Level Consensus Voting.** Active clients synchronize their local models via prefetched ciphertexts, compute local model increments $\Delta\mathbf{w}_i^{(t)} = \mathbf{w}_i^{(t)} - \mathbf{W}^{(t)}$, add their unweighted residual $\mathbf{r}_i^{(t-1)}$ to form $\mathbf{x}_i^{(t)} = \Delta\mathbf{w}_i^{(t)} + \mathbf{r}_i^{(t-1)}$, and apply pack-level Top-$\zeta$ sparsification guided by the $\ell_2$-norm to generate binary vote masks, which are protected via our Shamir zero-sharing-based secure voting mechanism. The server collects these masks, tallies the votes, and broadcasts the global consensus mask $\mathcal{K}^{(t)}$.
- **Phase 2: Sparse Packs Upload.** Guided by the global consensus mask $\mathcal{K}^{(t)}$, clients weight their aligned sparse updates using the fixed active-set weight $\omega_i^{(t)} = n_i / \sum_{u \in \mathcal{S}^{(t)}} n_u$ as $\tilde{\mathbf{g}}_i^{(t)} = \omega_i^{(t)} \mathbf{x}_i^{(t)}$ to ensure strict slot correspondence. They encrypt the aligned packs via our dropout-resilient pack-level sparse ciphertext upload mechanism using effective key $\tilde{s}_{i,j}^{(t)}$ and upload the resulting ciphertexts to the server.
- **Phase 3: Homomorphic Aggregation.** In the synchronous setting ($\mathcal{D}^{(t)}=\emptyset$), the server directly sums the uploaded ciphertexts to restore the aggregate key contribution $a_j^{(t)}S$ via Shamir interpolation. In the asynchronous setting with upload-phase dropouts ($\mathcal{D}^{(t)} \neq \emptyset$), the server broadcasts the finalized surviving set $\widehat{\mathcal{S}}^{(t)}$, and surviving clients $\widehat{\mathcal{S}}^{(t)}$ compute the local dropout compensation key term $\kappa_{i,j}^{(t)}$ and supply pure key-compensation ciphertexts $\delta_{i,j}^{(t)}$ to restore the exact aggregate key contribution $a_j^{(t)}S$ without revealing $S$ to the server.
- **Phase 4: Ciphertexts Prefetching.** The server temporally caches the sparse global update ciphertexts $C^{(t)}$ over a sliding window of $R$ rounds. Presampled clients proactively download and homomorphically accumulate these sparse updates during idle windows. Upon becoming active, clients perform a one-step decryption per accumulated pack to synchronize their local models via $\mathbf{w}_i \leftarrow \mathbf{w}_i + \tilde{\mathbf{g}}_{\mathrm{pre}}$.

```
Algorithm 1: ECPFL Main Procedure
Input: Datasets {D_i}_{i=1}^N, initial W^{(0)}, rounds T, window R, threshold \tau
Output: Synchronized global model across clients
1: KGC sends (s_i, S, \sigma_a, \sigma_b, {s_{k,i}}_{k=1}^N, z_i) to each i \in C
2: Server sets Q <- \emptyset; each i \in C sets w_i <- W^{(0)}, r_i <- 0
3: for t = 1, 2, ..., T do
4:   Server samples S^{(t)} \subseteq P^{(t)}, P^{(t+R)}; sets \omega_i^{(t)} <- n_i / \sum_{u \in S^{(t)}} n_u
5:   foreach active client i \in S^{(t)} in parallel do
6:     Synchronize model w_i <- ECP-Sync(i, t, S, \sigma_a)
7:     Train w_i^{(t)} on D_i for E epochs; set \Delta w_i^{(t)} <- w_i^{(t)} - w_i
8:     Upload (\hat{v}_i^{(t)}, x_i^{(t)}) <- ESP-Vote(i, t, \Delta w_i^{(t)}, r_i, \zeta)
9:   Server broadcasts K^{(t)} <- ESP-Tally({\hat{v}_i^{(t)}}_{i \in S^{(t)}})
10:  foreach surviving client i \in \widehat{S}^{(t)} \subseteq S^{(t)} in parallel do
11:    Upload {ct_{i,j}^{(t)}} <- ESP-Enc(i, t, x_i^{(t)}, \omega_i^{(t)}, K^{(t)})
12:  if D^{(t)} = S^{(t)} \setminus \widehat{S}^{(t)} \neq \emptyset then
13:    Server broadcasts \widehat{S}^{(t)} to surviving uploaders
14:    Each i \in \widehat{S}^{(t)} uploads {\delta_{i,j}^{(t)}} <- ESP-Comp(i, t, \widehat{S}^{(t)}, K^{(t)})
15:  Server computes {C_j^{(t)}} <- ESP-Agg(t, \widehat{S}^{(t)}, K^{(t)})
16:  Server updates queue ECP-Queue(t, C^{(t)}, K^{(t)})
17:  Each i \in P^{(t+R)} runs ECP-Fetch(i, t, Q) in background
```

```
Algorithm 2: ESP Upstream Module
Parameter: J, q, p, \Delta, \gamma_d, \gamma_s, client keys (s_i, {s_{k,i}}, z_i, \sigma_a, \sigma_b)
1: Function ESP-Vote(i, t, \Delta w_i^{(t)}, r_i, \zeta)
2:   Set x_i^{(t)} <- \Delta w_i^{(t)} + r_i; select Top-\zeta packs for v_i^{(t)}(X)
3:   Compute masked vote \hat{v}_i^{(t)} via Eq. (9); return (\hat{v}_i^{(t)}, x_i^{(t)})
4: Function ESP-Tally({\hat{v}_i^{(t)}}_{i \in S^{(t)}})
5:   Recover V^{(t)}(X) via Eq. (10); return consensus set K^{(t)}
6: Function ESP-Enc(i, t, x_i^{(t)}, \omega_i^{(t)}, K^{(t)})
7:   Scale \tilde{g}_i^{(t)} <- \omega_i^{(t)} x_i^{(t)}; update r_i via Eq. (12) and t_{last,i} <- t
8:   foreach selected pack j \in K^{(t)} do
9:     Encode pt_{i,j}^{(t)} <- Ecd(\tilde{g}_{i,j}^{(t)}, \Delta); encrypt ct_{i,j}^{(t)} via Eq. (11)
10:  return {ct_{i,j}^{(t)}}_{j \in K^{(t)}}
11: Function ESP-Comp(i, t, \widehat{S}^{(t)}, K^{(t)})
12:   Update \widehat{\lambda}_i^{(t)} over \widehat{S}^{(t)}; form (\kappa_{i,j}^{(t)}, \delta_{i,j}^{(t)}) via Eq. (14)
13:   return {\delta_{i,j}^{(t)}}_{j \in K^{(t)}}
14: Function ESP-Agg(t, \widehat{S}^{(t)}, K^{(t)})
15:   Compute C_j^{(t)} for j \in K^{(t)} via Eq. (13) or Eq. (15)
16:   return {C_j^{(t)}}_{j \in K^{(t)}}
```

#### IV-B. Threat Model and Security Goals
**1) Threat Model:**
\textsc{ECPFL} involves three types of entities. We define the trust boundaries and adversarial behaviors of the involved entities as follows:
- **Key Generation Center (KGC).** The KGC is a fully trusted third party that operates only once at initialization (Phase~0). It samples one degree-$(\tau-1)$ Shamir sharing polynomial $F_k(x)$ per client secret $s_k$ and one degree-$(\tau-1)$ zero-sharing polynomial $\Psi(x)$ with $\Psi(0)=0$, distributes the evaluations together with $(s_i, S, \sigma_a, \sigma_b, z_i)$ to the clients over secure channels, and erases all temporary polynomials immediately after delivery, so the $\mathcal{O}(N^2)$ share matrix is never persistently stored. Each client stores only its own key material and $\mathcal{O}(N)$ shares, from which it locally derives the share sums needed for arbitrary participation and dropout sets. The KGC remains permanently offline thereafter.
- **Honest-but-Curious Server.** The server is an honest-but-curious central aggregator. It faithfully executes the prescribed consensus tallying, ciphertext aggregation, queue maintenance, and prefetch scheduling procedures, but it may attempt to infer private local model updates, individual vote bitmaps, or global model parameters from all messages and metadata it observes.
- **Honest-but-Curious Clients.** Clients execute local training, voting, encryption, decryption, and residual updates honestly, but up to $\kappa \le \tau - 2$ colluding clients may pool their secret keys, Shamir shares, PRPG seeds, and public transcripts to infer honest clients' private updates, secret keys, or individual vote bitmaps.

**2) Adversarial Capabilities:**
We consider a semi-honest adversary $\mathcal{A}$ that may corrupt either the central server (denoted $\mathcal{A}_{\mathrm{srv}}$), any subset $\mathcal{K}_{\mathrm{cor}} \subset \mathcal{C}$ of at most $\kappa \le \tau - 2$ colluding clients (denoted $\mathcal{A}_{\mathrm{cli}}$), or external passive eavesdroppers. Following standard single-step multi-key HE FL models~\cite{wu2025esafl}, \cite{li2025fedphe}, we assume the server does not collude with corrupted clients, because every registered client holds $(S, \sigma_a)$ to perform non-interactive one-step decryption of global aggregates. Corrupted parties follow the protocol specification but pool their internal views to infer private information of honest clients $\mathcal{H}^{(t)} = \widehat{\mathcal{S}}^{(t)} \setminus \mathcal{K}_{\mathrm{cor}}$. Because $|\mathcal{S}^{(t)}| \ge |\widehat{\mathcal{S}}^{(t)}| \ge \tau$ and $\kappa \le \tau - 2$, every valid round automatically contains at least $|\mathcal{H}^{(t)}| \ge \tau - (\tau - 2) = 2$ honest surviving clients. Secure channels exist only between the KGC and individual clients during Phase~0 initialization; all training-phase messages are transmitted over public client--server channels observable by the server and external eavesdroppers. By design, the server knows the public participation and consensus sets $(\mathcal{P}^{(t)}, \mathcal{S}^{(t)}, \bar{\mathcal{S}}^{(t)}, \widehat{\mathcal{S}}^{(t)}, \mathcal{K}^{(t)})$.

**3) Security Goals:**
\textsc{ECPFL} is designed to achieve the following security guarantees:
- **Individual ciphertext privacy.** For each honest client $h \in \mathcal{H}^{(t)}$, the uploaded pack ciphertext $\mathrm{ct}_{h,j}^{(t)}$ computationally conceals the weighted local update $\mathrm{pt}_{h,j}^{(t)}$ against both $\mathcal{A}_{\mathrm{srv}}$ and any coalition $\mathcal{A}_{\mathrm{cli}}$ of $\kappa \le \tau - 2$ colluding clients under the dRLWE assumption and $(\tau, N)$-Shamir secret sharing with pack-specific zero-share masking.
- **Server obliviousness.** In the absence of client--server collusion, the server $\mathcal{A}_{\mathrm{srv}}$ cannot recover the plaintext of any individual client's update $\mathrm{pt}_{i,j}^{(t)}$ or the aggregated global update $\mathrm{pt}_j^{(t)}$.
- **Collusion resistance.** Against any coalition $\mathcal{A}_{\mathrm{cli}}$ of $\kappa \le \tau - 2$ colluding clients, the secret keys $\{s_h\}$, zero-shares $\{z_h\}$, and individual plaintexts $\mathrm{pt}_{h,j}^{(t)}$ of honest clients $h \in \mathcal{H}^{(t)}$ ($|\mathcal{H}^{(t)}| \ge 2$) remain unrecoverable; decrypting the global aggregate $C_j^{(t)}$ reveals at most the honest sum $\sum_{h \in \mathcal{H}^{(t)}} \mathrm{pt}_{h,j}^{(t)}$.
- **Voting and compensation privacy.** Individual vote bitmaps $\mathbf{v}_h^{(t)}$ are protected against $\mathcal{A}_{\mathrm{srv}}$ and $\kappa \le \tau - 2$ colluding clients via Shamir zero-sharing and RLWE noise perturbation (revealing only the global tally $\nu_j^{(t)}$ and the honest vote sum), while pure key-compensation ciphertexts $\delta_{h,j}^{(t)}$ restore $a_j^{(t)}S$ without exposing honest clients' long-term keys or shares.
- **Cross-round prefetching privacy.** The $R$-round prefetched aggregate $C_{\mathrm{pre},j}$ reveals no plaintext information to the server or external eavesdroppers, and allows authorized clients to recover only the per-round aggregates and their cross-round sum without isolating any single client's update.

#### IV-C. ESP: Efficient Sparse Packing
**1) Local Compensation and Consensus Voting:**
To avoid the severe SIMD disruption caused by traditional element-wise sparsification, \textsc{ESP} operates strictly at the pack level. From the $\lceil \beta K \rceil$ presampled candidates in $\mathcal{P}^{(t)}$, the first $K$ responsive clients form the confirmed active set $\mathcal{S}^{(t)} \subseteq \mathcal{P}^{(t)}$ ($|\mathcal{S}^{(t)}| = K \ge \tau$). Each client $i \in \mathcal{S}^{(t)}$ integrates its historical unweighted pack-level residual $\mathbf{r}_i^{(t-1)}$ into the current local model increment $\Delta\mathbf{w}_{i}^{(t)} = \mathbf{w}_i^{(t)} - \mathbf{W}^{(t)}$ to compute the unweighted compensated update $\mathbf{x}_{i}^{(t)} = \Delta\mathbf{w}_{i}^{(t)} + \mathbf{r}_{i}^{(t-1)}$. The client partitions $\mathbf{x}_i^{(t)}$ into $J$ packs and identifies the Top-$\zeta$ packs ($\zeta \in (0,1]$) based on their $\ell_2$-norms, encoding this selection into a binary vote bitmap $\mathbf{v}_i^{(t)} = (v_{i,1}^{(t)}, \dots, v_{i,J}^{(t)}) \in \{0, 1\}^J$. The server aggregates the bitmaps to compute a global voting score $\nu_j^{(t)} = \sum_{i \in \mathcal{S}^{(t)}} v_{i,j}^{(t)}$ for each pack $j$ and derives the consensus mask $\mathcal{K}^{(t)} \subseteq [J]$ (indicator vector $\mathbf{k}^{(t)} \in \{0, 1\}^J$) via:
- **Union (\textsc{ECPFL-UN}):** $\mathcal{K}^{(t)} = \bigl\{ j \in [J] \;\big|\; \nu_j^{(t)} \ge 1 \bigr\}$.
- **Rank (\textsc{ECPFL-RK-}$\theta$):** $\mathcal{K}^{(t)} = \bigl\{ j \in [J] \;\big|\; \nu_j^{(t)} \ge \vartheta^{(t)} \bigr\}$, where $\vartheta^{(t)}$ is the $\lceil \theta J \rceil$-th largest score.
- **Threshold (\textsc{ECPFL-TH-}$\theta$):** $\mathcal{K}^{(t)} = \bigl\{ j \in [J] \;\big|\; \nu_j^{(t)} \ge \theta \cdot |\mathcal{S}^{(t)}| \bigr\}$.

**2) Shamir Zero-Sharing Secure Voting:**
Because $J \ll n$, each active client $i \in \mathcal{S}^{(t)}$ embeds its $J$-bit vote bitmap into the lower $J$ coefficients of $v_i^{(t)}(X) = \sum_{j=1}^J v_{i,j}^{(t)} X^{j-1} \in \mathcal{R}_p$ and generates $a_0^{(t)} = \mathrm{HE.PRPG}(\sigma_b, t \parallel 0) \in \mathcal{R}_q$ using reserved index $0$ for domain separation from pack indices $j \in [J]$. Using its Lagrange weight $\lambda_i^{(t)}$ for $\mathcal{S}^{(t)}$ and a fresh error polynomial $e_{i,0}^{(t)} \leftarrow \chi_e$, client $i$ uploads a single masked vote polynomial:
$$\hat{v}_i^{(t)} = \Bigl[\, a_0^{(t)} \cdot \lambda_i^{(t)} z_i + \tilde{p}\cdot e_{i,0}^{(t)} + v_i^{(t)}(X) \,\Bigr]_q \in \mathcal{R}_q. \quad (9)$$
Summing $\hat{v}_i^{(t)}$ on the server factors out $a_0^{(t)}$ and invokes $\bigl[\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} z_i\bigr]_q = \Psi(0) = 0$:
$$V^{(t)}(X) = \Biggl[\biggl[\, \sum_{i \in \mathcal{S}^{(t)}} \hat{v}_i^{(t)} \,\biggr]_q\Biggr]_p = \Biggl[ a_0^{(t)} \!\underbrace{\sum_{i \in \mathcal{S}^{(t)}} \!\lambda_i^{(t)} z_i}_{=\,0} + \tilde{p} E_0^{(t)} + \!\sum_{i \in \mathcal{S}^{(t)}} \!v_i^{(t)}(X) \Biggr]_{q,p} = \sum_{j=1}^J \nu_j^{(t)} X^{j-1}. \quad (10)$$

**3) Dropout-Resilient Sparse Ciphertext Upload:**
Upon receiving $\mathcal{K}^{(t)}$, active clients scale their unweighted compensated update by the fixed active-set aggregation weight $\omega_i^{(t)} = n_i / \sum_{u \in \mathcal{S}^{(t)}} n_u$ to form $\tilde{\mathbf{g}}_i^{(t)} = \omega_i^{(t)} \mathbf{x}_i^{(t)}$ and encode $\mathrm{pt}_{i,j}^{(t)} = \mathrm{Ecd}(\tilde{\mathbf{g}}_{i,j}^{(t)}, \Delta)$ for each $j \in \mathcal{K}^{(t)}$. Client $i$ derives pack-specific polynomials $a_j^{(t)} = \mathrm{HE.PRPG}(\sigma_a, t \parallel j)$ and $b_j^{(t)} = \mathrm{HE.PRPG}(\sigma_b, t \parallel j)$ and encrypts $\mathrm{pt}_{i,j}^{(t)}$ under effective key $\tilde{s}_{i,j}^{(t)}$:
$$\begin{aligned}
\tilde{s}_{i,j}^{(t)} &= \biggl[\, s_i + \lambda_i^{(t)} \!\sum_{k \in \bar{\mathcal{S}}^{(t)}} s_{k,i} + \lambda_i^{(t)} b_j^{(t)} z_i \,\biggr]_q, \\
\mathrm{ct}_{i,j}^{(t)} &= \mathrm{HE.Enc}\bigl(a_j^{(t)}, \tilde{s}_{i,j}^{(t)}, \mathrm{pt}_{i,j}^{(t)}\bigr) = \Bigl[\, a_j^{(t)} \cdot \tilde{s}_{i,j}^{(t)} + \tilde{p} \cdot e_{i,j}^{(t)} + \mathrm{pt}_{i,j}^{(t)} \,\Bigr]_q.
\end{aligned} \quad (11)$$
Finally, the client updates its local residual using the unweighted update $\mathbf{x}_i^{(t)}$ via dual-decay residual compensation:
$$\mathbf{r}_i^{(t)} = \gamma_d \,\gamma_s^{\ell_i^{(t)}-1}\Bigl(\mathbf{x}_i^{(t)} \odot \bigl(\mathbf{1} - \mathbf{k}^{(t)}\bigr)\Bigr), \quad (12)$$
where $\ell_i^{(t)} = t - t_{\mathrm{last},i} \ge 1$ is the number of gap rounds since the client's last participation round $t_{\mathrm{last},i}$.

**4) Global Homomorphic Aggregation:**
- **Synchronous Setting ($\mathcal{D}^{(t)} = \emptyset$, $\widehat{\mathcal{S}}^{(t)} = \mathcal{S}^{(t)}$):**
$$\begin{aligned}
C_j^{(t)} &= \mathrm{HE.Eval}\bigl(\{\mathrm{ct}_{i,j}^{(t)}\}\bigr) = \Biggl[\sum_{i \in \mathcal{S}^{(t)}} \mathrm{ct}_{i,j}^{(t)}\Biggr]_q \\
&= \biggl[ a_j^{(t)} \Bigl( \sum_{i \in \mathcal{S}^{(t)}} \!s_i + \!\sum_{k \in \bar{\mathcal{S}}^{(t)}} \underbrace{\sum_{i \in \mathcal{S}^{(t)}} \!\lambda_i^{(t)} s_{k,i}}_{=\,s_k} + b_j^{(t)} \!\underbrace{\sum_{i \in \mathcal{S}^{(t)}} \!\lambda_i^{(t)} z_i}_{=\,0} \Bigr) + \tilde{p} \sum_{i \in \mathcal{S}^{(t)}} e_{i,j}^{(t)} + \sum_{i \in \mathcal{S}^{(t)}} \mathrm{pt}_{i,j}^{(t)} \Biggr]_q \\
&= \Bigl[\, a_j^{(t)} S + \tilde{p} E_j^{(t)} + \mathrm{pt}_j^{(t)} \,\Bigr]_{q}.
\end{aligned} \quad (13)$$
- **Asynchronous Setting ($\mathcal{D}^{(t)} \neq \emptyset$, $\widehat{\mathcal{S}}^{(t)} = \mathcal{S}^{(t)} \setminus \mathcal{D}^{(t)}$):**
Each surviving client $i \in \widehat{\mathcal{S}}^{(t)}$ ($|\widehat{\mathcal{S}}^{(t)}| \ge \tau$) computes updated Lagrange weights $\widehat{\lambda}_i^{(t)}$, forms the local dropout compensation key term $\kappa_{i,j}^{(t)}$, and uploads a pure key-compensation ciphertext $\delta_{i,j}^{(t)}$ with fresh error $\hat{e}_{i,j}^{(t)} \leftarrow \chi_e$:
$$\begin{aligned}
\kappa_{i,j}^{(t)} &= \biggl[ \widehat{\lambda}_i^{(t)} \!\sum_{k \notin \widehat{\mathcal{S}}^{(t)}}\! s_{k,i} - \lambda_i^{(t)} \!\sum_{k \in \bar{\mathcal{S}}^{(t)}}\! s_{k,i} + \bigl(\widehat{\lambda}_i^{(t)} - \lambda_i^{(t)}\bigr) b_j^{(t)} z_i \biggr]_q, \\
\delta_{i,j}^{(t)} &= \Bigl[ a_j^{(t)} \cdot \kappa_{i,j}^{(t)} + \tilde{p} \cdot \hat{e}_{i,j}^{(t)} \Bigr]_q.
\end{aligned} \quad (14)$$
Summing $\mathrm{ct}_{i,j}^{(t)} + \delta_{i,j}^{(t)}$ over $i \in \widehat{\mathcal{S}}^{(t)}$ cancels the stale $\lambda_i^{(t)}$ terms and restores the exact aggregate key contribution $a_j^{(t)}S$:
$$\begin{aligned}
C_j^{(t)} &= \Biggl[ \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \Bigl( \mathrm{ct}_{i,j}^{(t)} + \delta_{i,j}^{(t)} \Bigr) \Biggr]_q \\
&= \biggl[ a_j^{(t)} \Bigl( \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \!s_i + \!\sum_{k \notin \widehat{\mathcal{S}}^{(t)}} \underbrace{\sum_{i \in \widehat{\mathcal{S}}^{(t)}} \!\widehat{\lambda}_i^{(t)} s_{k,i}}_{=\,s_k} + b_j^{(t)} \!\underbrace{\sum_{i \in \widehat{\mathcal{S}}^{(t)}} \!\widehat{\lambda}_i^{(t)} z_i}_{=\,0} \Bigr) + \tilde{p} \widehat{E}_j^{(t)} + \mathrm{pt}_j^{(t)} \Biggr]_q \\
&= \Bigl[\, a_j^{(t)} S + \tilde{p} \widehat{E}_j^{(t)} + \mathrm{pt}_j^{(t)} \,\Bigr]_q,
\end{aligned} \quad (15)$$
where $\widehat{E}_j^{(t)} = \sum_{i \in \widehat{\mathcal{S}}^{(t)}} (e_{i,j}^{(t)} + \hat{e}_{i,j}^{(t)})$ and $\mathrm{pt}_j^{(t)} = \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \mathrm{pt}_{i,j}^{(t)} = \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \mathrm{Ecd}(\omega_i^{(t)} \mathbf{x}_{i,j}^{(t)}, \Delta)$.

#### IV-D. ECP: Ciphertext Prefetching
```
Algorithm 3: ECP Download Module
Parameter: Prefetch horizon R, pack count J, scaling factor \Delta
1: Function ECP-Queue(t, C^{(t)}, K^{(t)})
2:   Push (t, K^{(t)}, C^{(t)}) to Q; evict entries with r <= t - R
3: Function ECP-Fetch(i, t, Q)
4:   foreach (r, K^{(r)}, C^{(r)}) \in Q with t_{last,i} <= r <= t do
5:     Append uncached {(r, C_j^{(r)})}_{j \in K^{(r)}} to buffers {L_{i,j}}
6: Function ECP-Sync(i, t, S, \sigma_a)
7:   Fetch uncached packs in [t_{last,i}, t-1]; set \tilde{g}_{pre} <- 0
8:   foreach pack j \in [J] with L_{i,j} \neq \emptyset do
9:     Form (A_{pre,j}, C_{pre,j}) over H_{i,j} via Eq. (16)
10:    Decrypt pt_{pre,j} (Eq. (17)); set \tilde{g}_{pre,j} <- Dcd(pt_{pre,j}, \Delta)
11:  Clear {L_{i,j}} <- \emptyset and return w_i + \tilde{g}_{pre}
```

For any selected pack $j$, let $\mathcal{H}_{i,j} = \{r \mid (r, C_j^{(r)}) \in \mathcal{L}_{i,j}\}$ denote the set of missed rounds in which pack $j$ was selected. The composite ciphertext $C_{\mathrm{pre},j}$ is computed via $\mathrm{HE.Eval}$ as:
$$\begin{aligned}
C_{\mathrm{pre},j} &= \mathrm{HE.Eval}\Bigl(\bigl\{C_j^{(r)}\bigr\}_{r \in \mathcal{H}_{i,j}}\Bigr) = \Biggl[\sum_{r \in \mathcal{H}_{i,j}} C_{j}^{(r)}\Biggr]_q \\
&= \Biggl[\, \underbrace{\Biggl( \sum_{r \in \mathcal{H}_{i,j}} a_j^{(r)} \Biggr)}_{A_{\mathrm{pre},j}} S + \tilde{p} \underbrace{\sum_{r \in \mathcal{H}_{i,j}} E_j^{(r)}}_{E_{\mathrm{pre},j}} + \underbrace{\sum_{r \in \mathcal{H}_{i,j}} \mathrm{pt}_j^{(r)}}_{\mathrm{pt}_{\mathrm{pre},j}} \,\Biggr]_q = \Bigl[\, A_{\mathrm{pre},j} S + \tilde{p} E_{\mathrm{pre},j} + \mathrm{pt}_{\mathrm{pre},j} \,\Bigr]_{q},
\end{aligned} \quad (16)$$
and decrypted in a single step per pack via:
$$\mathrm{pt}_{\mathrm{pre},j} = \mathrm{HE.Dec}\bigl(A_{\mathrm{pre},j}, S, C_{\mathrm{pre},j}\bigr) = \Bigl[\bigl[ C_{\mathrm{pre},j} - A_{\mathrm{pre},j} S \bigr]_{q}\Bigr]_{p} = \Bigl[\bigl[\, \tilde{p} E_{\mathrm{pre},j} + \mathrm{pt}_{\mathrm{pre},j} \,\bigr]_{q}\Bigr]_p = \mathrm{pt}_{\mathrm{pre},j}. \quad (17)$$
Because each round's $\mathrm{pt}_j^{(r)}$ already embeds the fixed active-set aggregation weights $\omega_i^{(r)}$, the client directly decodes $\tilde{\mathbf{g}}_{\mathrm{pre},j} = \mathrm{Dcd}(\mathrm{pt}_{\mathrm{pre},j}, \Delta) = \sum_{r \in \mathcal{H}_{i,j}} \tilde{\mathbf{g}}_j^{(r)}$ in one step, concatenates $\{\tilde{\mathbf{g}}_{\mathrm{pre},j}\}$ into $\tilde{\mathbf{g}}_{\mathrm{pre}}$, and updates $\mathbf{w}_i \leftarrow \mathbf{w}_i + \tilde{\mathbf{g}}_{\mathrm{pre}}$.

---

### Section V. Security Analysis (FedPHE-Style System & Protocol Analysis)

In this section, we analyze the security and correctness of \textsc{ECPFL} following the system-level security analysis methodology of FedPHE~\cite{li2025fedphe} and ESAFL~\cite{wu2025esafl}. We first evaluate entity-level resilience against semi-honest clients, a semi-honest server, and colluding client subsets, and then establish the correctness and privacy guarantees of the \textsc{ESP} and \textsc{ECP} protocol mechanisms.

#### V-A. Entity-Level Security Guarantees
**1) Resilience Against Semi-Honest Clients:**
An authorized client $i \in \mathcal{C}$ holds its own secret key $s_i$, the aggregate decryption key $S = \bigl[\sum_{u=1}^N s_u\bigr]_q$, the pseudorandom seeds $(\sigma_a, \sigma_b)$, its Shamir shares $\{s_{k,i}\}_{k=1}^N$, and its zero-share $z_i$. While $(S, \sigma_a)$ enables client $i$ to perform one-step decryption on a completed global aggregate $C_j^{(t)}$, it does not allow client $i$ to directly decrypt another honest client $h$'s individual uploaded ciphertext $\mathrm{ct}_{h,j}^{(t)} = [a_j^{(t)} \tilde{s}_{h,j}^{(t)} + \tilde{p} e_{h,j}^{(t)} + \mathrm{pt}_{h,j}^{(t)}]_q$. Specifically, subtracting $a_j^{(t)} S$ or $a_j^{(t)} s_i$ from $\mathrm{ct}_{h,j}^{(t)}$ leaves the unknown masking term $a_j^{(t)} \tilde{s}_{h,j}^{(t)} + \tilde{p} e_{h,j}^{(t)}$, where $\tilde{s}_{h,j}^{(t)} = [s_h + \lambda_h^{(t)} \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_{k,h} + \lambda_h^{(t)} b_j^{(t)} z_h]_q$ depends on client $h$'s private key $s_h$, uncorrupted Shamir shares $\{s_{k,h}\}$, and pack-masked zero-share $b_j^{(t)} z_h$. Moreover, because each pack $j \in \mathcal{K}^{(t)}$ uses distinct public polynomials $a_j^{(t)} = \mathrm{HE.PRPG}(\sigma_a, t \parallel j)$ and $b_j^{(t)} = \mathrm{HE.PRPG}(\sigma_b, t \parallel j)$, a curious client cannot cancel $s_h$ or $\lambda_h^{(t)} z_h$ across two packs $j_1 \neq j_2$ of the same round, nor can it form an unmasked linear system in $\lambda_h^{(t)}$ across rounds with different active sets $\mathcal{S}^{(t)}$~\cite{colin2026tfhesd}, \cite{kim2026tfhead}.

**2) Resilience Against Semi-Honest Server:**
The server $\mathcal{A}_{\mathrm{srv}}$ receives masked vote polynomials $\hat{v}_i^{(t)}$, sparse pack ciphertexts $\mathrm{ct}_{i,j}^{(t)}$, pure key-compensation ciphertexts $\delta_{i,j}^{(t)}$, and the public participation and consensus sets $(\mathcal{P}^{(t)}, \mathcal{S}^{(t)}, \widehat{\mathcal{S}}^{(t)}, \mathcal{K}^{(t)})$, but never accesses the aggregate key $S$, client keys $\{s_i, s_{k,i}, z_i\}$, or private seeds $(\sigma_a, \sigma_b)$. In each round $t$, every individual ciphertext $\mathrm{ct}_{i,j}^{(t)}$ is masked by $a_j^{(t)} \tilde{s}_{i,j}^{(t)} + \tilde{p} e_{i,j}^{(t)}$, and the completed global aggregate takes the form:
$$C_j^{(t)} = \Bigl[a_j^{(t)} S + \tilde{p} E_j^{(t)} + \mathrm{pt}_j^{(t)}\Bigr]_q. \quad (18)$$
Without the secret seed $\sigma_a$ and the aggregate key $S$, the public polynomial $a_j^{(t)}$ is pseudorandom over $\mathcal{R}_q$, and under the dRLWE assumption the masking term $a_j^{(t)} S + \tilde{p} E_j^{(t)}$ computationally conceals $\mathrm{pt}_j^{(t)}$. Consequently, under our non-collusion assumption between the server and clients, the server is oblivious to both individual updates $\mathrm{pt}_{i,j}^{(t)}$ and the aggregated global update $\mathrm{pt}_j^{(t)}$.

**3) Resilience Against Client Collusion:**
Consider a coalition $\mathcal{A}_{\mathrm{cli}}$ of $\kappa \le \tau - 2$ colluding clients $\mathcal{K}_{\mathrm{cor}} \subset \mathcal{C}$. For each honest client $h \in \mathcal{H}^{(t)} = \widehat{\mathcal{S}}^{(t)} \setminus \mathcal{K}_{\mathrm{cor}}$, the secret key $s_h = F_h(0)$ is shared via a degree-$(\tau-1)$ polynomial $F_h(x)$, and the zero-share $z_h = \Psi(\alpha_h)$ is generated from a degree-$(\tau-1)$ polynomial $\Psi(x)$ with $\Psi(0) = 0$. The coalition $\mathcal{K}_{\mathrm{cor}}$ holds $\kappa \le \tau - 2$ share evaluations $\{F_h(\alpha_i)\}_{i \in \mathcal{K}_{\mathrm{cor}}}$, which provides at most $\tau - 2 < \tau$ interpolation points and leaves $F_h(0) = s_h$ information-theoretically undetermined. Crucially, even when combining its $\kappa \le \tau - 2$ zero-shares $\{\Psi(\alpha_i)\}_{i \in \mathcal{K}_{\mathrm{cor}}}$ with the public anchor $\Psi(0) = 0$, the coalition possesses at most $(\tau - 2) + 1 = \tau - 1 < \tau$ evaluation points on the degree-$(\tau-1)$ polynomial $\Psi(x)$. Because all constant evaluation points $\alpha_i = i \in [N]$ have invertible pairwise differences $(\alpha_i - \alpha_j) \in \mathcal{R}_q^{\times}$~\cite{mouchet2023threshold}, at least one degree of freedom of $\Psi(x)$ remains uniformly undetermined over $\mathcal{R}_q$, keeping every honest zero-share $z_h = \Psi(\alpha_h)$ hidden from $\mathcal{A}_{\mathrm{cli}}$. Furthermore, since $|\widehat{\mathcal{S}}^{(t)}| \ge \tau$ and $\kappa \le \tau - 2$, every valid round contains at least $|\mathcal{H}^{(t)}| \ge \tau - (\tau - 2) = 2$ honest surviving clients. When the coalition decrypts $C_j^{(t)}$ using $(S, \sigma_a)$ and subtracts its own known contributions $\sum_{i \in \widehat{\mathcal{S}}^{(t)} \cap \mathcal{K}_{\mathrm{cor}}} \mathrm{pt}_{i,j}^{(t)}$, it obtains only the sum of honest updates $\sum_{h \in \mathcal{H}^{(t)}} \mathrm{pt}_{h,j}^{(t)}$, which is a single linear equation in $|\mathcal{H}^{(t)}| \ge 2$ unknown honest plaintexts and cannot algebraically isolate any individual $\mathrm{pt}_{h,j}^{(t)}$.

#### V-B. Protocol Correctness and Security

**Lemma 1 (*Vote Tally Correctness and Bitmap Privacy*):**
*Assume $|\mathcal{S}^{(t)}| \ge \tau$, $\kappa \le \tau - 2$, $p \mid \tilde{p}$, $|\mathcal{S}^{(t)}| < p$, and $\|\tilde{p} E_0^{(t)} + \sum_{i \in \mathcal{S}^{(t)}} v_i^{(t)}(X)\|_\infty < q/2$. Then: (i) server aggregation in Eq.~(10) recovers the exact pack-wise vote tally $\nu_j^{(t)} = \sum_{i \in \mathcal{S}^{(t)}} v_{i,j}^{(t)}$; and (ii) neither the server $\mathcal{A}_{\mathrm{srv}}$ nor a coalition $\mathcal{A}_{\mathrm{cli}}$ of $\kappa \le \tau - 2$ colluding clients can algebraically recover any honest client's individual vote bitmap $\mathbf{v}_h^{(t)}$.*

*Proof:* (i) For $\hat{v}_i^{(t)} = [a_0^{(t)} \lambda_i^{(t)} z_i + \tilde{p} e_{i,0}^{(t)} + v_i^{(t)}(X)]_q$ with $|\mathcal{S}^{(t)}| \ge \tau > \deg(\Psi)$, Lagrange interpolation over $\mathcal{S}^{(t)}$ yields $\bigl[\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} z_i\bigr]_q = \Psi(0) = 0$. Summing $\hat{v}_i^{(t)}$ over $i \in \mathcal{S}^{(t)}$ leaves $[\tilde{p} E_0^{(t)} + \sum_{i \in \mathcal{S}^{(t)}} v_i^{(t)}(X)]_q$. Since $\|\tilde{p} E_0^{(t)} + \sum_{i \in \mathcal{S}^{(t)}} v_i^{(t)}(X)\|_\infty < q/2$, centered reduction modulo $q$ does not wrap around, and reduction modulo $p$ eliminates $\tilde{p} E_0^{(t)}$ and recovers $\nu_j^{(t)} \in [0, |\mathcal{S}^{(t)}|] \subset [0, p)$ exactly.
(ii) Against the server $\mathcal{A}_{\mathrm{srv}}$ (which lacks $\sigma_b$ and $z_h$), $a_0^{(t)} = \mathrm{HE.PRPG}(\sigma_b, t \parallel 0)$ is pseudorandom and $a_0^{(t)} \lambda_h^{(t)} z_h + \tilde{p} e_{h,0}^{(t)}$ masks $v_h^{(t)}(X)$ in $\mathcal{R}_q$. Against $\kappa \le \tau - 2$ colluding clients $\mathcal{A}_{\mathrm{cli}}$ (who know $\sigma_b$ and thus $a_0^{(t)}$), the coalition holds at most $\kappa \le \tau - 2$ shares of $\Psi(x)$ plus $\Psi(0) = 0$, giving at most $\tau - 1 < \tau$ points on the degree-$(\tau-1)$ polynomial $\Psi(x)$. Thus $z_h = \Psi(\alpha_h)$ remains unknown to $\mathcal{A}_{\mathrm{cli}}$ for every honest client $h \in \mathcal{H}^{(t)}$, preventing the coalition from computing $a_0^{(t)} \lambda_h^{(t)} z_h$ and stripping the mask from $\hat{v}_h^{(t)}$. Subtracting the corrupted clients' masked votes from $\sum_{i \in \mathcal{S}^{(t)}} \hat{v}_i^{(t)}$ reveals only the sum of honest vote bitmaps $\sum_{h \in \mathcal{S}^{(t)} \setminus \mathcal{K}_{\mathrm{cor}}} v_h^{(t)}(X)$ across at least two honest participants. $\blacksquare$

**Theorem 1 (*Dropout Compensation Correctness and Privacy*):**
*Let $\widehat{\mathcal{S}}^{(t)} \subseteq \mathcal{S}^{(t)}$ with $|\widehat{\mathcal{S}}^{(t)}| \ge \tau$ and $\kappa \le \tau - 2$. Under the constant evaluation points $\alpha_i = i \in [N]$ ($q_\ell > N$): (i) synchronous aggregation in Eq.~(13) and asynchronous compensated aggregation in Eq.~(15) restore the exact aggregate key contribution $a_j^{(t)} S$ and fixed-weight plaintext sum $\mathrm{pt}_j^{(t)} = \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \mathrm{pt}_{i,j}^{(t)}$; and (ii) the pure key-compensation ciphertext $\delta_{h,j}^{(t)}$ protects honest clients' secret shares against $\mathcal{A}_{\mathrm{srv}}$ and $\mathcal{A}_{\mathrm{cli}}$.*

*Proof:* (i) When $\widehat{\mathcal{S}}^{(t)} = \mathcal{S}^{(t)}$, Shamir interpolation over $|\mathcal{S}^{(t)}| \ge \tau$ gives $\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} s_{k,i} = s_k$ and $\sum_{i \in \mathcal{S}^{(t)}} \lambda_i^{(t)} z_i = 0$, so $\sum_{i \in \mathcal{S}^{(t)}} \tilde{s}_{i,j}^{(t)} = \sum_{i \in \mathcal{S}^{(t)}} s_i + \sum_{k \in \bar{\mathcal{S}}^{(t)}} s_k = S$. When upload-phase dropouts occur ($\mathcal{D}^{(t)} \neq \emptyset$), adding $\kappa_{i,j}^{(t)}$ in Eq.~(14) to $\tilde{s}_{i,j}^{(t)}$ cancels the stale $\lambda_i^{(t)}$ terms for each $i \in \widehat{\mathcal{S}}^{(t)}$, leaving $\tilde{s}_{i,j}^{(t)} + \kappa_{i,j}^{(t)} \equiv s_i + \widehat{\lambda}_i^{(t)} \sum_{k \notin \widehat{\mathcal{S}}^{(t)}} s_{k,i} + \widehat{\lambda}_i^{(t)} b_j^{(t)} z_i \pmod q$. Summing over $|\widehat{\mathcal{S}}^{(t)}| \ge \tau$ surviving clients restores $\sum_{k \notin \widehat{\mathcal{S}}^{(t)}} s_k$ and cancels $b_j^{(t)} z_i$, while the pure key-compensation ciphertext $\delta_{i,j}^{(t)} = [a_j^{(t)} \kappa_{i,j}^{(t)} + \tilde{p} \hat{e}_{i,j}^{(t)}]_q$ introduces zero plaintext distortion, preserving $\mathrm{pt}_j^{(t)} = \sum_{i \in \widehat{\mathcal{S}}^{(t)}} \mathrm{pt}_{i,j}^{(t)}$.
(ii) In $\delta_{h,j}^{(t)} = [a_j^{(t)} \kappa_{h,j}^{(t)} + \tilde{p} \hat{e}_{h,j}^{(t)}]_q$, the compensation key term $\kappa_{h,j}^{(t)}$ is masked by the pack-specific zero-share term $(\widehat{\lambda}_h^{(t)} - \lambda_h^{(t)}) b_j^{(t)} z_h$ and perturbed by fresh RLWE noise $\tilde{p} \hat{e}_{h,j}^{(t)}$ ($\hat{e}_{h,j}^{(t)} \leftarrow \chi_e$). Because $z_h$ cannot be interpolated by $\kappa \le \tau - 2$ colluding clients and $b_j^{(t)} = \mathrm{HE.PRPG}(\sigma_b, t \parallel j)$ refreshes the multiplicative mask on every pack and round, neither $\mathrm{ct}_{h,j}^{(t)}$, $\delta_{h,j}^{(t)}$, nor their sum exposes unmasked linear equations in the static shares $\{s_{k,h}\}$. $\blacksquare$

**Theorem 2 (*Prefetching Correctness and Privacy*):**
*Suppose all consensus pack ciphertexts over $\mathcal{H}_{i,j}$ are cached, $p \mid \tilde{p}$, and $\|\tilde{p} E_{\mathrm{pre},j} + \mathrm{pt}_{\mathrm{pre},j}\|_\infty < q/2$. Then: (i) one-step decryption in Eq.~(17) recovers the exact multi-round weighted update sum $\mathrm{pt}_{\mathrm{pre},j} = \sum_{r \in \mathcal{H}_{i,j}} \mathrm{pt}_j^{(r)}$; and (ii) forming $C_{\mathrm{pre},j}$ reveals no plaintext information to $\mathcal{A}_{\mathrm{srv}}$ and no additional single-client information beyond the per-round aggregates to $\mathcal{A}_{\mathrm{cli}}$.*

*Proof:* (i) For any cache index set $\mathcal{H}_{i,j}$, homomorphic addition over $\mathcal{R}_q$ in Eq.~(16) yields:
$$C_{\mathrm{pre},j} = \Bigl[A_{\mathrm{pre},j} S + \tilde{p} E_{\mathrm{pre},j} + \sum_{r \in \mathcal{H}_{i,j}} \mathrm{pt}_j^{(r)}\Bigr]_q, \quad (19)$$
where $A_{\mathrm{pre},j} = \bigl[\sum_{r \in \mathcal{H}_{i,j}} a_j^{(r)}\bigr]_q$. An authorized client holding $(S, \sigma_a)$ subtracts $A_{\mathrm{pre},j} S$, applies centered reduction modulo $q$, and reduces modulo $p$ to eliminate $\tilde{p} E_{\mathrm{pre},j}$, recovering $\mathrm{pt}_{\mathrm{pre},j} = \sum_{r \in \mathcal{H}_{i,j}} \mathrm{pt}_j^{(r)}$ in a single decryption step. Because each round's $\mathrm{pt}_j^{(r)} = \sum_{u \in \widehat{\mathcal{S}}^{(r)}} \mathrm{Ecd}(\omega_u^{(r)} \mathbf{x}_{u,j}^{(r)}, \Delta)$ already incorporates the fixed active-set weights $\omega_u^{(r)}$, decoding $\mathrm{Dcd}(\mathrm{pt}_{\mathrm{pre},j}, \Delta)$ directly yields the exact cumulative global update $\sum_{r \in \mathcal{H}_{i,j}} \tilde{\mathbf{g}}_j^{(r)}$ without any post-decryption rescaling.
(ii) Since $C_{\mathrm{pre},j}$ is a deterministic ring sum of the per-round aggregates $\{C_j^{(r)}\}_{r \in \mathcal{H}_{i,j}}$, it reveals no plaintext information to the server $\mathcal{A}_{\mathrm{srv}}$ (which lacks $S$ and $\sigma_a$), and discloses to authorized clients no information beyond the per-round aggregates $\{\mathrm{pt}_j^{(r)}\}$, within which individual honest updates remain protected by $|\mathcal{H}^{(r)}| \ge 2$. $\blacksquare$

---

### Section VI. Performance Evaluation & Section VII. Conclusion

#### VI-A. Experimental Tables (Tables II–VII) & Audit Summary

**Table II: Scalability Analysis Across Client Scales on CIFAR-10 ($T=50$)**

| $N$ | $K$ | AC (%) | TV (GB) | Base (GB) | TT (s) | Storage $\mathcal{O}(N)$ | Setup (s) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **50** | **25** | **82.77** | **13.71** | **52.15** | **962.5** | **3.33 MB** | **0.42** |
| 100 | 50 | 82.91 | 27.42 | 104.30 | 1894.0 | 6.44 MB | 1.65 |
| 500 | 250 | 83.08 | 137.10 | 521.50 | 9410.5 | 31.44 MB | 41.20 |
| 1000 | 500 | 83.15 | 274.20 | 1043.00 | 18790.0 | 62.69 MB | 164.80 |

**Table III: Overall Comparison of AC (%), TV (GB), and TT (s) Across Four Benchmark Datasets**

| Method | MNIST ($\theta=0.1, \zeta=0.1$) | FMNIST ($\theta=0.3, \zeta=0.1$) | CIFAR-10 ($\theta=0.7, \zeta=0.5$) | SVHN ($\theta=0.7, \zeta=0.5$) |
| :--- | :---: | :---: | :---: | :---: |
| **FedAvg+CKKS** | **99.23** / 8.56 / 315.0 | **91.46** / 7.78 / 285.4 | **84.41** / 52.15 / 1756.3 | **95.73** / 89.60 / 3141.6 |
| **FedPHE (Top-$\zeta$)** | 99.10 / 3.84 / 201.5 | 87.00 / 3.95 / 179.4 | 75.77 / 31.75 / 1221.5 | 94.44 / 54.38 / 2445.1 |
| **ESAFL** | 99.11 / 4.67 / 240.0 | 89.51 / 3.89 / 244.4 | 77.51 / 26.46 / 1402.6 | 95.54 / 45.14 / 2363.5 |
| **MASER** | 99.13 / 8.31 / 466.7 | 90.66 / 7.17 / 427.8 | 81.91 / 40.92 / 1927.9 | 95.63 / 71.02 / 3308.4 |
| **ECPFL-UN (Ours)** | 99.19 / 4.21 / 439.9 | 91.20 / 2.86 / 323.2 | 82.77 / 20.03 / 1564.9 | 95.11 / 34.89 / 986.5 |
| **ECPFL-TH-$\theta$ (Ours)** | 99.10 / 4.06 / 422.5 | 90.74 / 2.15 / 259.8 | 75.58 / **7.60** / **689.2** | 94.17 / **19.10** / **577.6** |
| **ECPFL-RK-$\theta$ (Ours)** | 99.15 / **0.80** / **129.9** | 90.14 / **1.19** / **95.8** | 79.24 / 18.66 / 1441.4 | 95.11 / 31.68 / 923.2 |

**Table V: Per-Round Cryptographic Complexity and Measured Latency of ECPFL by Entity**

| Entity | Cryptographic Operation | Complexity | Measured Time |
| :--- | :--- | :---: | :---: |
| **Active client** | Pack-level encryption | $|\mathcal{K}^{(t)}|$ Enc | $\le 0.69$ s |
| | One-step local decryption | $\le |\mathcal{K}^{(t)}|$ Dec | $\le 0.18$ s |
| | Masked vote generation | $J$ $\ell_2$-norms $+$ 1 Enc | $< 16$ ms |
| **Prefetch client** | Cross-round accumulation | $\le R|\mathcal{K}^{(t)}|$ Add | $\le 0.10$ s |
| **Server** | Homomorphic aggregation | $K|\mathcal{K}^{(t)}|$ Add | $\le 0.26$ s |
| **KGC / Comp.** | Online KGC computation | $0$ (Offline setup) | $0$ ms |
| | Dropout compensation ct. | $|\mathcal{K}^{(t)}|$ Enc | $\le 0.69$ s |

**Table VI: Component-Wise Ablation Study of the ESP Module on SVHN (ResNet-32, $\zeta=0.5, \theta=0.7$)**

| LS | RF | PRD | CRD | RK | AC (%) | UV (MB) | $\Delta$UV |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| -- | -- | -- | -- | -- | **95.73** | 45,429.7 | Baseline |
| $\checkmark$ | -- | -- | -- | -- | 95.07 | 41,553.9 | $-8.5\%$ |
| $\checkmark$ | $\checkmark$ | -- | -- | -- | 95.01 | 41,798.3 | $-8.0\%$ |
| $\checkmark$ | $\checkmark$ | $\checkmark$ | -- | -- | 94.89 | 42,409.5 | $-6.6\%$ |
| $\checkmark$ | $\checkmark$ | $\checkmark$ | $\checkmark$ | -- | 94.91 | 41,528.6 | $-8.6\%$ |
| $\checkmark$ | $\checkmark$ | $\checkmark$ | $\checkmark$ | $\checkmark$ | 94.90 | **31,869.6** | **$-29.8\%$** |

#### Section VII. Conclusion and Future Work
This paper proposes \textsc{ECPFL}, an efficient ciphertext prefetching FL framework that extends one-step aggregate decryption to partial participation and upload-phase client dropout scenarios without peer-to-peer client communication. The \textsc{ESP} protocol addresses the alignment and dropout challenges in encrypted sparsification by integrating a Shamir zero-sharing-based secure voting mechanism with a dropout-resilient pack-level sparse ciphertext upload and key-compensation mechanism, enabling aligned upstream compression and exact aggregate key-contribution restoration under fixed active-set aggregation weights. Building upon \textsc{ESP}, the \textsc{ECP} protocol allows intermittently participating clients with limited bandwidth to asynchronously download and accumulate sparse ciphertext updates during idle periods and recover multiple rounds of global updates through a single local decryption operation, shifting most downstream communication out of the synchronous training phase.

Although our incremental KGC initialization eliminates online KGC involvement and persistent share-matrix storage, its quadratic one-time setup communication and linear per-client share storage remain scalability limitations. Future work will explore fully decentralized distributed key generation (DKG) and committee-based secret sharing to eliminate the quadratic setup overhead, and will investigate adaptive pack-level voting based on gradient consensus and client availability.
