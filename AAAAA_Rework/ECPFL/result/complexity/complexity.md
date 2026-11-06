# ECPFL (V17) 计算复杂度基准

- 环维度 n=4096，logp=50，Δ=2^20，eta=4，τ=3，K=25，R=3
- 重复 1 次取 mean±std

| 组件 | 耗时 mean±std (ms) | 每客户端材料 (MB) |
|---|---|---|
| kgc/keygen_N50 | 666.19±0.00 | 3.5 |
| client/esp_vote | 5.94±0.00 | — |
| client/esp_enc_per_pack | 8.76±0.00 | — |
| client/esp_comp_per_pack | 10.57±0.00 | — |
| client/dec_one_shot | 3.92±0.00 | — |
| client/ecp_prefetch_R3 | 4.26±0.00 | — |
| server/esp_tally_K25 | 2.24±0.00 | — |
| server/esp_agg_sync_K25 | 1.18±0.00 | — |
| server/esp_agg_dropout_K25 | 2.25±0.00 | — |
