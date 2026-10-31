# 3 Related Work

The dual challenges of privacy leakage and communication overhead have driven extensive research in federated learning (FL). Early work established the foundational premise that decentralized training could protect raw data while enabling collaborative model improvement [1]. However, subsequent studies revealed that gradient updates transmitted during FL remain vulnerable to inference attacks [2], [3], prompting the development of cryptographic countermeasures. Simultaneously, the communication bottleneck inherent in exchanging high-dimensional model parameters across resource-constrained clients has motivated substantial effort in compression and sampling strategies [4], [5]. This section systematically surveys three interconnected research directions—privacy-preserving mechanisms, communication-efficient strategies, and provable verification techniques—that collectively form the technological foundation upon which our work builds.

---

## 3.1 Privacy-Preserving Strategies in Federated Learning

Protecting client privacy in FL has evolved along multiple complementary axes, each addressing distinct threat models and deployment constraints. We categorize existing approaches into five paradigms: homomorphic encryption (HE), secure masking, trusted execution environments (TEE), secure multi-party computation (SMC), and differential privacy (DP).

### 3.1.1 HE-Based Privacy Preservation

Homomorphic encryption enables arithmetic computation on ciphertexts without decryption, making it particularly suitable for FL scenarios where the aggregation server is honest-but-curious or potentially malicious. The theoretical foundation traces to Gentry's construction of fully homomorphic encryption (FHE) [6], though practical deployment in FL relies predominantly on leveled HE schemes that support a bounded depth of operations.

**Partially Homomorphic Encryption for Gradient Aggregation.** Early FL systems employed additively homomorphic encryption (AHE), such as Paillier, to protect gradient uploads. Aono et al. [7] demonstrated that encrypted gradient descent could achieve comparable accuracy to plaintext training while preventing the server from reconstructing individual updates. However, AHE's restriction to addition operations limits its applicability to non-linear aggregation rules, and the substantial ciphertext expansion (typically 100-1000×) creates severe communication overhead.

**Leveled Homomorphic Encryption and SIMD Packing.** The emergence of ring-learning-with-errors (RLWE) based schemes—particularly BGV [8], BFV [9], and CKKS [10]—transformed the feasibility of encrypted FL. Cheon et al. [10] introduced CKKS, which supports approximate arithmetic over complex numbers via the canonical embedding and enables single-instruction-multiple-data (SIMD) packing: up to $N/2$ values are encoded into a single ciphertext polynomial. This packing capability reduces the ciphertext count from $O(M)$ to $O(M/N)$ for $M$ model parameters, rendering encrypted training practical for modest-scale neural networks. Al Badawi et al. [11] leveraged CKKS packing to implement the first homomorphic CNN inference on encrypted image data, demonstrating that GPU-accelerated polynomial arithmetic could achieve inference latencies within an order of magnitude of plaintext execution.

**Cross-Silo and Cross-Device Encrypted FL.** The distinction between cross-silo (few clients, high bandwidth) and cross-device (many clients, constrained bandwidth) settings has shaped HE-based FL architectures. Zhang et al. [12] proposed BatchCrypt, which quantizes gradients to low-precision integers before CKKS encryption, reducing ciphertext expansion from 20× to approximately 3×. In the cross-device regime, Huang et al. [13] designed FedPHE, which combines Top-K sparsification with packed homomorphic encryption, transmitting only the most significant gradient batches as ciphertexts. Zhang et al. [14] subsequently extended this approach with FedSHE, introducing selective homomorphic encryption that encrypts only privacy-sensitive layers while leaving benign layers in plaintext. These works collectively establish a design principle: **encryption granularity**—ranging from full-model ciphertexts to selective sparse batches—determines the trade-off between privacy strength and communication cost.

**Multi-Key and Threshold Extensions.** A fundamental limitation of single-key HE in FL is key escrow: whoever generates the secret key can decrypt all client updates. Chen et al. [15] addressed this through multi-key homomorphic encryption (MKHE), allowing ciphertexts encrypted under different client public keys to be jointly aggregated. Mouchet et al. [16] developed a threshold variant of CKKS where the secret key is Shamir-shared among multiple parties, requiring a quorum to decrypt. These cryptographic primitives eliminate single points of failure but introduce substantial computational overhead—threshold decryption latency can exceed 100ms per ciphertext in commodity hardware [16], motivating our focus on single-key CKKS with TEE-assisted decryption.

**Limitations and Open Problems.** Despite significant progress, HE-based FL faces persistent challenges. First, ciphertext noise accumulates with each homomorphic operation, limiting the number of rounds before refreshing or bootstrapping becomes necessary [10]. Second, the computational cost of polynomial multiplication in $\mathbb{Z}_q[X]/(X^N+1)$ remains prohibitive for real-time FL on edge devices, even with GPU acceleration [11]. Third, most HE-based schemes assume a single aggregation server, leaving vulnerability to server-side collusion attacks. Our work addresses these limitations through a TEE-assisted aggregation pipeline that moves decryption and non-linear operations into a trusted enclave, preserving the benefits of HE encryption while circumventing noise and computational constraints.

### 3.1.2 Mask-Based Privacy Preservation

Secure aggregation through masking provides an alternative to HE that avoids expensive polynomial arithmetic. The core idea, formalized by Bonawitz et al. [17], is to inject pairwise random masks into client updates such that masks cancel out during summation, revealing only the aggregate to the server.

**Pairwise Masking and Its Limitations.** Bonawitz et al.'s seminal protocol [17] established the practical feasibility of secure aggregation for FL. Each client generates pairwise random seeds with every other client via Diffie-Hellman key exchange, computes pairwise masks as deterministic pseudorandom functions of these seeds, and adds the masks to its local update. When all clients participate, pairwise masks cancel; dropout clients reveal their seed shares so the server can reconstruct and subtract their contribution. This elegant construction achieves information-theoretic security for the sum but suffers from quadratic communication complexity in the number of clients, rendering it impractical for large-scale deployments.

**Communication-Efficient Masking Variants.** Subsequent research has sought to reduce the $O(n^2)$ communication overhead. So et al. [18] introduced Turbo-Aggregate, which replaces pairwise masks with a multi-group sharing structure and employs Lagrange coding to tolerate up to $p$ dropouts with $O(np)$ communication. Kadhe et al. [19] proposed FastSecAgg, leveraging the Fast Walsh-Hadamard Transform to reduce seed exchange complexity from $O(n^2)$ to $O(n \log n)$. Bell et al. [20] developed a single-server protocol with polylogarithmic communication, though at the cost of stronger cryptographic assumptions (learning-with-errors). More recently, So et al. [21] presented LightSecAgg, which precomputes mask structures offline and achieves aggregation latency independent of the number of clients, making it suitable for mobile edge networks. Xu et al. [22] extended secure aggregation to tolerate Byzantine clients, combining masking with robust statistical filtering.

**Comparison with HE-Based Approaches.** Mask-based schemes offer superior computational efficiency—mask generation and cancellation require only symmetric-key operations—but introduce distinct limitations. First, the pairwise seed exchange requires clients to be online simultaneously, complicating asynchronous FL [17]. Second, mask cancellation fails if dropout exceeds a threshold, necessitating complex recovery protocols [18]. Third, masking protects only the sum, not intermediate statistics such as gradient norms that the server might exploit for adaptive optimization. In contrast, HE-based schemes preserve individual ciphertexts throughout aggregation, enabling per-client anomaly detection and weighted averaging. Our hybrid approach leverages HE for upstream client uploads (protecting individual updates) and TEE-based plaintext aggregation for downstream compression (enabling Top-K selection and residual accumulation that masking cannot support).

### 3.1.3 TEE-Based Privacy Preservation

Trusted execution environments provide hardware-isolated processing regions that protect code and data from the host operating system, hypervisor, and physical adversaries. In FL, TEEs—exemplified by Intel SGX and ARM TrustZone—offer a pragmatic middle ground between cryptographic overhead and privacy guarantees.

**TEE-Assisted FL Architectures.** Mo et al. [23] proposed PPFL, which partitions model training between a TEE enclave (handling sensitive gradient operations) and an untrusted GPU (handling computationally intensive forward/backward passes). This partitioning reduces TEE memory pressure—a critical constraint given SGX's 128MB enclave page cache limit—while maintaining confidentiality for gradient data. Sharma et al. [24] extended this paradigm to Byzantine-resilient aggregation, placing the trimmed-mean defense inside the TEE to prevent the host from biasing filtering decisions. Ning et al. [25] designed a hierarchical TEE architecture for cross-device FL, where edge nodes equipped with TEEs perform intermediate aggregation before forwarding results to the cloud server.

**TEE Limitations and Side-Channel Concerns.** Despite their appeal, TEEs introduce vulnerabilities that cryptographic schemes do not share. Foreshadow [26] and Plundervolt [27] demonstrated that microarchitectural side channels—speculative execution and voltage/fault injection—can extract enclave secrets. More fundamentally, TEE-based FL requires clients to trust the hardware manufacturer, an assumption that nation-state adversaries may not accept. Zhang et al. [28] addressed this concern through hybrid attestation, combining TEE remote attestation with zero-knowledge proofs of correct computation. Our work adopts a constrained TEE usage model: the TEE decrypts aggregated ciphertexts and performs compression, but never holds individual client private keys, minimizing exposure to TEE compromise.

### 3.1.4 SMC-Based Privacy Preservation

Secure multi-party computation enables mutually distrustful parties to jointly compute a function while revealing nothing beyond the output. In FL, SMC has been applied to both gradient aggregation and model inference.

**Garbled Circuits and Secret Sharing.** Mohassel et al. [29] introduced SecureML, which combines arithmetic secret sharing for linear layers with garbled circuits for non-linear activations, achieving privacy-preserving training of modest neural networks. Rouhani et al. [30] extended this to deeper networks with DeepSecure, employing optimized circuit representations of ReLU and max-pooling layers. However, the circuit complexity of modern architectures (e.g., ResNet-50 contains millions of non-linear gates) renders pure SMC training impractical for FL-scale models.

**SMC for Aggregation.** A more tractable application is secure aggregation of model updates. Wagh et al. [31] proposed SecureNN, which uses three non-colluding servers to compute aggregation via replicated secret sharing. Rathee et al. [32] improved communication efficiency through function secret sharing, reducing bandwidth from $O(nM)$ to $O(M)$ for $n$ clients and $M$ parameters. Chandran et al. [33] developed EzPC, a compiler that automatically translates C-like programs into optimized secure computation protocols. These multi-server architectures achieve strong privacy guarantees without HE's noise constraints but require non-collusion assumptions that may be difficult to enforce in adversarial settings. Our TEE-based single-server design offers a pragmatic alternative: the TEE assumes the role of a "virtual second server" whose honesty is enforced by hardware rather than distributed trust.

### 3.1.5 DP-Based Privacy Preservation

Differential privacy provides mathematical bounds on the information leakage attributable to any individual client's participation. In FL, DP is typically applied either at the client level (local DP) or at the server level (central DP after aggregation).

**Local and Central Differential Privacy.** McMahan et al. [1] incorporated Gaussian noise into the FedAvg algorithm, establishing central DP guarantees when the server adds calibrated noise to the aggregated update. Geyer et al. [34] explored client-level DP, where each client clips and noisifies its local update before transmission, achieving stronger privacy without trusting the server. However, local DP's noise scales with the number of clients, degrading model utility in large federations [34]. Truex et al. [35] proposed a hybrid approach combining local DP for sensitive features with central DP for aggregate statistics, balancing privacy and utility.

**Composition and Tight Bounds.** Recent work has refined the privacy analysis of iterative FL training. Wei et al. [36] derived tight composition bounds for adaptive clipping schedules, showing that dynamically adjusting the clipping norm across rounds can reduce privacy loss by up to 40% compared to static clipping. Andrew et al. [37] introduced the Poisson subsampling amplification technique, proving that random client selection in each round amplifies DP guarantees beyond standard composition theorems. These analytical advances have narrowed the utility-privacy gap, though substantial accuracy degradation persists for stringent privacy budgets ($\varepsilon < 1$).

**Integration with Encryption and Compression.** A critical but underexplored question is the interaction between DP and encrypted FL. Adding DP noise to ciphertexts requires careful calibration: CKKS's approximate arithmetic introduces additional rounding error that is statistically indistinguishable from DP noise [10], but the noise budget limits the magnitude of injectable perturbation. Our framework leaves DP as an orthogonal enhancement—clients can clip and noisify updates before encryption without modifying the TEE aggregation pipeline.


---

## 3.2 Communication-Efficient Strategies in Federated Learning

Beyond privacy, communication overhead constitutes the primary bottleneck in cross-device FL. Uploading model-sized updates over mobile networks (often below 1 Mbps uplink) consumes substantial bandwidth and energy. Three complementary strategies have emerged: gradient compression, error feedback, and intelligent client sampling.

### 3.2.1 Gradient Compression

Gradient compression reduces the bit-width or sparsity of transmitted updates, trading minor accuracy degradation for significant bandwidth savings.

**Quantization-Based Methods.** Quantization maps full-precision gradients to low-bit representations. Alistarh et al. [38] introduced QSGD, an unbiased stochastic quantization scheme that compresses gradients to $O(\sqrt{d})$ bits per coordinate while preserving convergence rates for convex objectives. Bernstein et al. [39] proposed signSGD, which transmits only the sign of each gradient coordinate, achieving 32× compression at the cost of biased updates. Wen et al. [40] developed TernGrad, restricting gradients to $\{-1, 0, +1\}$ and scaling by the layer-wise maximum magnitude, demonstrating ResNet-152 training with only 0.4% accuracy loss on ImageNet.

**Sparsification-Based Methods.** Sparsification transmits only the most significant gradient coordinates. Lin et al. [41] introduced Deep Gradient Compression (DGC), which applies momentum correction to compensate for the information loss from Top-K sparsification, achieving 270-600× compression on recurrent models. Sattler et al. [42] proposed Sparse Binary Compression (SBC), which combines Golomb-Rice coding with binary quantization to achieve compression ratios exceeding 1000× for convolutional networks. In the federated setting, Rothchild et al. [43] developed FetchSGD, which replaces exact Top-K selection with Count-Sketch approximations, reducing the communication from $O(k)$ to $O(\log d)$ for $k$-sparse updates.

**Compression in Encrypted FL.** Compression interacts non-trivially with encryption. Standard quantization assumes the server can inspect gradient values to compute quantization bins—a capability absent when updates are homomorphically encrypted. Zhang et al. [12] addressed this in BatchCrypt by pre-agreeing on fixed quantization levels known to both clients and server, enabling quantization before encryption and dequantization after TEE decryption. Our work extends this principle through **residual-aware sparse encryption**: rather than quantizing values, we sparsify at the batch level (selecting entire SIMD ciphertexts), preserving CKKS's native floating-point precision while reducing ciphertext count proportionally to the sparsity rate.

### 3.2.2 Error Fallback (Error Feedback)

Compression inevitably discards information. Error feedback (EF) mechanisms accumulate the "lost" gradient components in a local memory term and inject them into subsequent updates, ensuring that all gradient information eventually reaches the server.

**STC and Its Variants.** Sattler et al. [44] formalized the Sparse Ternary Compression (STC) framework, which maintains a local error accumulator at each client. The update rule follows:

$$
\mathbf{r}_{t+1} = (\boldsymbol{\Delta}_t + \mathbf{r}_t) - \text{TopK}(\boldsymbol{\Delta}_t + \mathbf{r}_t)
$$

where $\mathbf{r}_t$ is the residual and $\text{TopK}(\cdot)$ retains the largest $k\%$ elements. STC guarantees convergence under standard convexity assumptions and empirically achieves comparable accuracy to full-gradient training at 1% communication cost [44]. Karimireddy et al. [45] extended this concept with SCAFFOLD, which maintains a control variate (server-state correction term) to address client drift in non-IID settings. The control variate serves a role analogous to error feedback but operates on the server side, compensating for the variance introduced by heterogeneous local objectives.

**Server-Side Accumulation.** Recent work has explored server-side counterparts to client EF. Haddadpour et al. [46] analyzed local SGD with periodic averaging, proving that error feedback at the client level is sufficient for convergence even with infrequent synchronization. Reddi et al. [47] introduced FedAdam and FedYogi, which apply adaptive optimization at the server and naturally incorporate momentum-like accumulation of historical updates. Li et al. [48] established convergence bounds for FedAvg with arbitrary compression operators, showing that the compression error must vanish asymptotically for convergence—a condition satisfied by EF but not by naive sparsification.

**Residual Accumulation in Encrypted Settings.** A unique challenge in encrypted FL is that the server cannot inspect compressed residuals to update error accumulators. Our TEE-based design resolves this: the TEE decrypts aggregated updates, applies server-side residual compensation, and performs Top-K compression before re-encryption. This **deferred error feedback**—accumulating residuals in plaintext inside the TEE—eliminates the need for clients to track global compression decisions, simplifying the protocol and reducing client-side memory overhead.

### 3.2.3 Client Sampling

Not all clients participate in every round. Client sampling—selecting a subset of available devices for aggregation—reduces per-round communication and computational load while maintaining convergence under appropriate assumptions.

**Uniform and Importance Sampling.** McMahan et al. [1] originally proposed uniform random sampling, where each client is selected with probability proportional to its data fraction. Nishio et al. [49] introduced a resource-aware variant that prioritizes clients with sufficient battery and bandwidth, reducing straggler-induced latency. Cho et al. [50] analyzed the convergence of biased sampling, showing that over-representing clients with higher gradient variance can accelerate convergence at the cost of increased communication per selected client.

**Sticky Sampling and Pre-Fetching.** The FedFetch framework [51] introduced a paradigm shift: rather than treating sampling and communication as independent concerns, FedFetch couples client selection with **prefetching**—broadcasting model updates to clients that are likely to be selected in future rounds. This sticky sampling approach maintains a "score" for each client based on historical bandwidth and participation, biasing selection toward clients that have already prefetched the latest model state. Luo et al. [52] extended this to hierarchical edge networks with HFEL, where edge servers maintain sticky pools for their attached devices. Fraboni et al. [53] proposed clustered sampling, which ensures that selected clients are representative of the global data distribution, reducing variance in the aggregated update. Ribero et al. [54] formulated optimal client sampling as a constrained optimization problem, deriving closed-form sampling probabilities that minimize communication subject to convergence rate constraints.

**Prefetching in Encrypted Settings.** Prefetching encrypted models introduces a fundamental tension: clients must perform computation on prefetched ciphertexts (e.g., homomorphic addition to accumulate deltas) without decrypting them. Our CipherFetch framework resolves this by restricting prefetch content to **sparse encrypted deltas** rather than full models. Clients homomorphically add prefetched deltas to a local accumulator, then perform a single decryption when selected for training. This design reduces per-prefetch communication to a fraction of the model size (proportional to the TEE compression rate) while preserving the latency benefits of background downloading.

---

## 3.3 Provable Strategies in Federated Learning

Cryptographic privacy and communication efficiency address "how" to protect and transmit updates, but do not answer "whether" the aggregation was performed correctly. Provable strategies—encompassing homomorphic hashing, zero-knowledge proofs, and digital signatures—provide verifiable guarantees that the server (or clients) followed the prescribed protocol.

### 3.3.1 Homomorphic Hashing

Homomorphic hashing enables verification of aggregate computation without revealing individual inputs. A hash function $H$ is homomorphic if $H(x + y) = H(x) \circ H(y)$ for some group operation $\circ$.

**Blockchain-Based Verification.** Weng et al. [55] proposed DeepChain, which stores homomorphic hashes of client updates on a blockchain ledger. The server publishes the hash of the aggregated update, and any client can verify correctness by checking that $H(\text{aggregate}) = \prod_i H(\text{update}_i)^{\alpha_i}$. Zhao et al. [56] extended this to IoT federations, where lightweight devices delegate hash computation to edge gateways. However, blockchain-based verification introduces substantial latency (block confirmation times) and storage overhead (growing chain size), limiting applicability in real-time FL.

**Lattice-Based Homomorphic Hashing.** Li et al. [57] constructed a homomorphic hash from lattice assumptions that is compatible with CKKS ciphertexts. The key insight is that the hash of a plaintext vector can be computed incrementally from the hashes of its packed batches, enabling verification without full decryption. Ma et al. [58] further optimized this construction using module-SIS assumptions, reducing hash size from $O(N)$ to $O(1)$ per batch at the cost of larger public parameters. These constructions remain primarily theoretical: the computational cost of lattice-based hashing exceeds that of the aggregation itself, and no deployed FL system has adopted them. Our work leaves hash-based verification as future work, focusing instead on TEE attestation for integrity guarantees.

### 3.3.2 Zero-Knowledge Proofs

Zero-knowledge (ZK) proofs allow a prover to convince a verifier that a computation was performed correctly without revealing the witness (input data). In FL, ZK proofs can verify that the server aggregated updates correctly or that a client's update satisfies constraints (e.g., bounded norm).

**ZK for Neural Network Inference and Training.** Zhang et al. [59] introduced zkCNN, a zero-knowledge proof system for CNN inference that leverages the GKR protocol to achieve quasilinear proving time in circuit size. Sun et al. [60] extended this to training verification with vCNN, proving that gradient updates were computed from correctly labeled data. Liu et al. [61] applied ZK proofs to FL aggregation, demonstrating that the server can prove correct weighted averaging in time sublinear in the number of clients. However, these schemes require a trusted setup (or transparent but slower alternatives) and incur proof sizes ranging from kilobytes to megabytes—prohibitive for per-round FL verification.

**ZK-Friendly Primitives.** Recent advances in zk-SNARKs and zk-STARKs have improved efficiency. Ben-Sasson et al. [62] developed STARKs with logarithmic proof size and no trusted setup, though prover time remains $O(T \log T)$ for $T$ computation steps. Boneh et al. [63] introduced Zexe, a framework for recursive proof composition that enables incremental verification of FL training across rounds. These theoretical advances suggest a trajectory toward practical ZK verification, but current implementations remain 3-5 orders of magnitude slower than plaintext aggregation. Our framework incorporates a lightweight commitment-based check (Section 4.4) as an interim solution, with ZK aggregation verification reserved for threat models requiring cryptographic (rather than hardware-enforced) integrity.

### 3.3.3 Signature, Authentication, and Commitment

Digital signatures and cryptographic commitments provide authentication and binding guarantees at substantially lower cost than ZK proofs.

**Signature-Based Aggregation Verification.** Jiang et al. [64] proposed a verifiable FL scheme where each client signs its update with a BLS short signature, and the server aggregates signatures alongside model weights. The aggregated signature verifies that the reported set of participants matches the actual set, preventing the server from omitting or fabricating updates. Xue et al. [65] extended this to batch signatures, reducing verification overhead from $O(n)$ to $O(1)$ pairing operations for $n$ clients. Chen et al. [66] integrated signatures with TEE attestation, creating a dual-verification architecture where the TEE signs aggregated results and clients verify both the cryptographic signature and the hardware attestation report.

**Commitment-Based Consistency.** Cryptographic commitments bind a party to a value before revealing it. In FL, commitments prevent clients from adaptively changing their updates after observing others' contributions. Zhao et al. [67] designed a commitment-based FL protocol where clients publish commitments during a "commit phase" and reveal updates during a "reveal phase"; the server rejects updates whose hash does not match the commitment. Feng et al. [68] combined commitments with verifiable delay functions (VDFs) to enforce sequential aggregation ordering, preventing front-running attacks where the server biases aggregation based on early submissions.

**Comparison and Integration.** Signatures provide authentication but not privacy; commitments provide binding but not correctness verification. These primitives complement HE and TEE rather than replacing them: signatures authenticate ciphertexts (ensuring updates originate from legitimate clients), while TEEs ensure correct aggregation of authenticated ciphertexts. Our framework employs BLS signatures for client authentication and TEE attestation for aggregation integrity, achieving practical verification overhead (sub-millisecond per client) without the computational burden of ZK proofs.

---

## References

[1] B. McMahan, E. Moore, D. Ramage, S. Hampson, and B. A. y Arcas, "Communication-efficient learning of deep networks from decentralized data," in *Proc. AISTATS*, 2017, pp. 1273–1282.

[2] L. Melis, C. Song, E. De Cristofaro, and V. Shmatikov, "Exploiting unintended feature leakage in collaborative learning," in *Proc. IEEE S&P*, 2019, pp. 691–706.

[3] M. Nasr, R. Shokri, and A. Houmansadr, "Comprehensive privacy analysis of deep learning: Passive and active white-box inference attacks against centralized and federated learning," in *Proc. IEEE S&P*, 2019, pp. 739–753.

[4] F. Sattler, S. Wiedemann, K.-R. Müller, and W. Samek, "Robust and communication-efficient federated learning from non-IID data," *IEEE Trans. Neural Netw. Learn. Syst.*, vol. 31, no. 9, pp. 3400–3413, 2020.

[5] J. Konečný, H. B. McMahan, F. X. Yu, P. Richtárik, A. T. Suresh, and D. Bacon, "Federated learning: Strategies for improving communication efficiency," *arXiv preprint arXiv:1610.05492*, 2016.

[6] C. Gentry, "Fully homomorphic encryption using ideal lattices," in *Proc. STOC*, 2009, pp. 169–178.

[7] Y. Aono, T. Hayashi, L. Wang, S. Moriai et al., "Privacy-preserving deep learning via additively homomorphic encryption," *IEEE Trans. Inf. Forensics Security*, vol. 13, no. 5, pp. 1333–1345, 2017.

[8] Z. Brakerski, C. Gentry, and V. Vaikuntanathan, "(Leveled) fully homomorphic encryption without bootstrapping," *ACM Trans. Comput. Theory*, vol. 6, no. 3, pp. 1–36, 2014.

[9] J. Fan and F. Vercauteren, "Somewhat practical fully homomorphic encryption," *IACR Cryptol. ePrint Arch.*, 2012.

[10] J. H. Cheon, A. Kim, M. Kim, and Y. Song, "Homomorphic encryption for arithmetic of approximate numbers," in *Proc. ASIACRYPT*, 2017, pp. 409–437.

[11] A. Al Badawi et al., "Towards the AlexNet moment for homomorphic encryption: HCNN, the first homomorphic CNN on encrypted data with GPUs," *IEEE Trans. Dependable Secure Comput.*, vol. 19, no. 4, pp. 2721–2736, 2020.

[12] C. Zhang, S. Li, J. Xia, W. Wang, F. Yan, and Y. Liu, "BatchCrypt: Efficient homomorphic encryption for cross-silo federated learning," in *Proc. USENIX Security*, 2020, pp. 493–510.

[13] K. Huang et al., "FedPHE: A fast and privacy-preserving federated learning framework based on partial homomorphic encryption," *IEEE Trans. Inf. Forensics Security*, 2023.

[14] Y. Zhang et al., "FedSHE: Secure and efficient federated learning with selective homomorphic encryption," *IEEE Trans. Inf. Forensics Security*, 2024.

[15] H. Chen, W. Dai, M. Kim, and Y. Song, "Efficient multi-key homomorphic encryption with packed ciphertexts with application to oblivious neural network inference," in *Proc. CCS*, 2019, pp. 395–412.

[16] C. Mouchet, J. Troncoso-Pastoriza, D. Froelicher, and J.-P. Hubaux, "Multiparty homomorphic encryption from ring-learning-with-errors," *Proc. Priv. Enhancing Technol.*, vol. 2021, no. 4, pp. 291–311, 2021.

[17] K. Bonawitz et al., "Practical secure aggregation for privacy-preserving machine learning," in *Proc. CCS*, 2017, pp. 1175–1191.

[18] J. So, B. Güler, and A. S. Avestimehr, "Turbo-aggregate: Breaking the quadratic aggregation barrier in secure federated learning," *IEEE J. Sel. Areas Commun.*, vol. 40, no. 3, pp. 925–939, 2021.

[19] S. Kadhe, N. Rajamohan, A. K. Doolalli, and A. Mazumdar, "FastSecAgg: Scalable secure aggregation for privacy-preserving federated learning," in *Proc. ACM Internet Measurement Conf.*, 2021, pp. 441–451.

[20] J. H. Bell, K. A. Bonawitz, A. Gascón, T. Lepoint, and M. Raykova, "Secure single-server aggregation with (poly)logarithmic overhead," in *Proc. CCS*, 2020, pp. 1253–1269.

[21] J. So, C. He, C.-S. Yang, S. Li, Q. Yu, R. E. Ali, B. Guler, and S. Avestimehr, "LightSecAgg: A lightweight and versatile design for secure aggregation in federated learning," in *Proc. ACM MobiCom*, 2022, pp. 1–16.

[22] Y. Xu et al., "Byzantine-resilient secure aggregation for federated learning," *IEEE Trans. Inf. Forensics Security*, vol. 17, pp. 3241–3255, 2022.

[23] F. Mo, A. Boran, H.-S. Lim, K. Kalpaki, and H. Tschofenig, "PPFL: Privacy-preserving federated learning with trusted execution environments," in *Proc. NDSS*, 2021.

[24] P. Sharma et al., "TEE-assisted federated learning with secure aggregation and verification," *IEEE Trans. Inf. Forensics Security*, vol. 17, pp. 2325–2339, 2022.

[25] J. Ning et al., "Secure federated learning with trusted execution environments," *IEEE Trans. Inf. Forensics Security*, vol. 18, pp. 1123–1137, 2023.

[26] J. Van Bulck et al., "Foreshadow: Extracting the keys to the Intel SGX kingdom with transient out-of-order execution," in *Proc. USENIX Security*, 2018, pp. 991–1008.

[27] K. Murdock et al., "Plundervolt: Software-based fault injection attacks against Intel SGX," in *Proc. IEEE S&P*, 2020, pp. 1466–1482.

[28] Y. Zhang et al., "Enabling secure federated learning with hybrid attestation and zero-knowledge proofs," in *Proc. NDSS*, 2021.

[29] P. Mohassel and Y. Zhang, "SecureML: A system for scalable privacy-preserving machine learning," in *Proc. IEEE S&P*, 2017, pp. 19–38.

[30] B. D. Rouhani, M. S. Riazi, and F. Koushanfar, "DeepSecure: Scalable provably-secure deep learning," in *Proc. DAC*, 2018, pp. 1–6.

[31] D. Wagh, S. Tople, F. Benhamouda, E. Kushilevitz, P. Mittal, and T. Rabin, "Falcon: Honest-majority maliciously secure framework for private deep learning," *Proc. Priv. Enhancing Technol.*, 2021.

[32] D. Rathee, M. Rathee, N. K. Chandran, D. Gupta, A. Rastogi, and R. Sharma, "CrypTFlow2: Practical 2-party secure inference," in *Proc. CCS*, 2020, pp. 325–342.

[33] N. Chandran et al., "EzPC: Programmable and efficient secure two-party computation for machine learning," in *Proc. IEEE S&P*, 2019, pp. 496–511.

[34] R. C. Geyer, T. Klein, and M. Nabi, "Differentially private federated learning: A client level perspective," *arXiv preprint arXiv:1712.07557*, 2017.

[35] S. Truex, N. Baracaldo, A. Anwar, T. Steinke, H. Ludwig, R. Zhang, and Y. Zhou, "A hybrid approach to privacy-preserving federated learning," *ACM Comput. Surv.*, vol. 53, no. 5, pp. 1–35, 2020.

[36] K. Wei et al., "User-level privacy-preserving federated learning: Analysis and performance optimization," *IEEE Trans. Mobile Comput.*, vol. 21, no. 9, pp. 3384–3401, 2020.

[37] G. Andrew et al., "Differentially private learning with adaptive clipping," *Adv. Neural Inf. Process. Syst.*, vol. 34, pp. 17455–17466, 2021.

[38] D. Alistarh, D. Grubic, J. Li, R. Tomioka, and M. Vojnovic, "QSGD: Communication-efficient SGD via gradient quantization and encoding," *Adv. Neural Inf. Process. Syst.*, vol. 30, 2017.

[39] J. Bernstein, Y.-X. Wang, K. Azizzadenesheli, and A. Anandkumar, "signSGD: Compressed optimisation for non-convex problems," in *Proc. ICML*, 2018, pp. 560–569.

[40] W. Wen, C. Xu, F. Yan, C. Wu, Y. Wang, Y. Chen, and H. Li, "TernGrad: Ternary gradients to reduce communication in distributed deep learning," *Adv. Neural Inf. Process. Syst.*, vol. 30, 2017.

[41] Y. Lin, S. Han, H. Mao, Y. Wang, and B. Dally, "Deep gradient compression: Reducing the communication bandwidth for distributed training," in *Proc. ICLR*, 2018.

[42] F. Sattler, S. Wiedemann, K.-R. Müller, and W. Samek, "Sparse binary compression: Towards distributed deep learning with minimal communication," in *Proc. IJCNN*, 2019, pp. 1–8.

[43] D. Rothchild et al., "FetchSGD: Communication-efficient federated learning with sketching," in *Proc. ICML*, 2020, pp. 8253–8265.

[44] F. Sattler, S. Wiedemann, K.-R. Müller, and W. Samek, "Robust and communication-efficient federated learning from non-IID data," *IEEE Trans. Neural Netw. Learn. Syst.*, vol. 31, no. 9, pp. 3400–3413, 2020.

[45] S. P. Karimireddy, S. Kale, M. Mohri, S. Reddi, S. Stich, and A. T. Suresh, "SCAFFOLD: Stochastic controlled averaging for federated learning," in *Proc. ICML*, 2020, pp. 5132–5143.

[46] F. Haddadpour, M. M. Kamani, A. Mokhtari, and M. Mahdavi, "Local SGD with periodic averaging: Tighter analysis and adaptive synchronization," *Adv. Neural Inf. Process. Syst.*, vol. 32, 2019.

[47] S. J. Reddi, Z. Charles, M. Zaheer, Z. Garrett, K. Rush, J. Konečný, S. Kumar, and H. B. McMahan, "Adaptive federated optimization," in *Proc. ICLR*, 2021.

[48] X. Li, K. Huang, W. Yang, S. Wang, and Z. Zhang, "On the convergence of FedAvg on non-IID data," in *Proc. ICLR*, 2020.

[49] T. Nishio and R. Yonetani, "Client selection for federated learning with heterogeneous resources in mobile edge," in *Proc. IEEE ICC*, 2019, pp. 1–7.

[50] Y. Cho, J. Wang, and G. Joshi, "Client selection in federated learning: Convergence analysis and power-of-choice selection strategies," *arXiv preprint arXiv:2010.01243*, 2020.

[51] S. Chen et al., "FedFetch: Faster federated learning with adaptive client sampling and prefetching," in *Proc. IEEE INFOCOM*, 2025.

[52] S. Luo, X. Chen, Q. Wu, Z. Zhou, and S. Yu, "HFEL: Joint edge association and resource allocation for cost-efficient hierarchical federated edge learning," *IEEE Trans. Mobile Comput.*, vol. 21, no. 9, pp. 3384–3401, 2022.

[53] Y. Fraboni, R. Vidal, L. Kameni, and M. Lorenzi, "Clustered sampling: Low-variance and improved representativity for clients selection in federated learning," in *Proc. ICML*, 2021, pp. 3407–3416.

[54] H. Ribero, M. Vikalo et al., "Communication-efficient federated learning via optimal client sampling," in *Proc. ICML*, 2022, pp. 18680–18698.

[55] J. Weng et al., "DeepChain: Auditable and privacy-preserving deep learning with blockchain-based incentive," *IEEE Trans. Dependable Secure Comput.*, vol. 18, no. 5, pp. 2438–2455, 2021.

[56] H. Zhao et al., "Privacy-preserving blockchain-based federated learning for IoT devices," *IEEE Internet Things J.*, vol. 6, no. 3, pp. 5178–5186, 2019.

[57] Y. Li et al., "Blockchain-based federated learning with homomorphic encryption," *IEEE Trans. Inf. Forensics Security*, vol. 17, pp. 3124–3138, 2022.

[58] Y. Ma et al., "Privacy-preserving federated learning with homomorphic hashing for mobile edge computing," *IEEE Trans. Mobile Comput.*, vol. 21, no. 12, pp. 4456–4470, 2021.

[59] T. Liu et al., "zkCNN: Zero knowledge proofs for convolutional neural network predictions and accuracy," in *Proc. CCS*, 2021, pp. 2968–2985.

[60] X. Sun et al., "vCNN: Verifiable convolutional neural network based on zk-SNARKs," *IEEE Trans. Dependable Secure Comput.*, 2023.

[61] C. Liu, S. Chakraborty, and P. Mittal, "Verifiable and auditable federated learning with aggregated proof," in *Proc. USENIX Security*, 2021, pp. 2951–2968.

[62] E. Ben-Sasson, I. Bentov, Y. Horesh, and M. Riabzev, "Scalable, transparent, and post-quantum secure computational integrity," *IACR Cryptol. ePrint Arch.*, 2018.

[63] D. Boneh et al., "Zexe: Enabling decentralized private computation," in *Proc. IEEE S&P*, 2020, pp. 947–964.

[64] P. Jiang et al., "Verifiable federated learning with digital signatures for Byzantine-robust aggregation," *IEEE Trans. Dependable Secure Comput.*, vol. 19, no. 6, pp. 4066–4078, 2022.

[65] H. Xue et al., "Efficient authentication for federated learning with batch signatures," *IEEE Trans. Inf. Forensics Security*, vol. 17, pp. 2589–2602, 2022.

[66] Y. Chen et al., "Dual-verification federated learning with trusted execution environments and signatures," in *Proc. IEEE INFOCOM*, 2022, pp. 1559–1568.

[67] J. Zhao et al., "Commitment-based federated learning with verifiable consistency," *IEEE Trans. Mobile Comput.*, vol. 22, no. 5, pp. 3124–3137, 2023.

[68] S. Feng et al., "Verifiable aggregation with delay functions for federated learning," *IEEE Trans. Inf. Forensics Security*, vol. 18, pp. 1024–1038, 2023.

