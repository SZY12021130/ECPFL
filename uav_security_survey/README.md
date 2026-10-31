# 无人机安全 CCF-A 文献研究机会综述

## 交付文件

- `survey_single.tex`：单一 LaTeX 源文件（UTF-8，使用 ctex + XeLaTeX 编译）。
- `survey_single.pdf`：编译生成的 25 页 PDF 综述。
- `refs.bib`：独立的 BibTeX 参考文献文件，包含 27 条来自 DBLP 的 2024–2026 CCF-A 无人机安全相关论文。
- `papers_ccfa.json`：DBLP 检索结果元数据（27 条论文的标题、作者、venue、年份、DOI、DBLP key 等）。
- `summary.txt`：检索统计摘要。

## 内容概要

本报告系统检索 DBLP 2024–2026 年 CCF-A 期刊/会议中面向 UAV/Drone 安全、隐私与密码学的研究，通过主题聚类提炼出 35 个可在典型实验环境（NVIDIA RTX 3050 + Intel i7，必要时租用云 GPU）中验证的研究贡献点。每个贡献点包含：

- 聚类的真实论文名称
- 现状分析
- 具体实验方向
- 经典/同态密码学结合点

涵盖方向包括：轻量认证、组密钥管理、物理层安全、同态联邦学习、安全多方计算、零知识匿名、区块链审计、GPS 反欺骗、OTA 安全、可信执行、后量子密码、边缘安全卸载、视觉隐私、搜索加密、差分隐私、可验证计算、安全路由、AI 模型安全、数字孪生安全等。

## 编译方式

```bash
cd uav_security_survey
xelatex survey_single.tex
bibtex survey_single
xelatex survey_single.tex
xelatex survey_single.tex
```

## 说明

由于 2024–2026 年 CCF-A 会议/期刊中直接以 UAV/Drone 安全为主题的论文数量有限，本报告在真实检索结果的基础上，围绕每篇论文提炼出多个可延伸的实验方向。所有列出的论文均可在 DBLP 中检索到，对应 BibTeX 已存放于 `refs.bib`。
