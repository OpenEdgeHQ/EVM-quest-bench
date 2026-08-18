<p align="right"><a href="README.md">English</a> · <b>中文</b></p>

# EVM-QuestBench

**EVM-QuestBench：面向自然语言交易代码生成的执行地基评测基准**

EVM-QuestBench 评测模型能否把自然语言区块链意图转化为可执行的交易代码，并在 EVM 上产生正确的状态变化。题库包含 **62 道 Atomic 原子题** 和 **45 道 Composite 组合题**，模型生成的动作会在 BSC Anvil fork 上真实执行，再由 validator 检查 receipt、calldata 和链上状态，而不是比较代码字符串。

## 论文信息

- ACL 2026 主会 Long Paper，Volume 1
- 作者：Pei Yang*、Wanyi Chen*、Ke Wang、Lynn Ai、Eric Yang、Tianyu Shi†（*同等贡献，†通讯作者）
- 单位：Gradient、Soochow University
- [项目主页](https://openedgehq.github.io/EVM-quest-bench/)
- [ACL Anthology](https://aclanthology.org/2026.acl-long.1642/)
- [arXiv](https://arxiv.org/abs/2601.06565)
- [Hugging Face 数据集与在线预览](https://huggingface.co/datasets/berryccc1/EVM-QuestBench)

## Hugging Face 数据集

```python
from datasets import load_dataset

dataset = load_dataset("berryccc1/EVM-QuestBench")
print(dataset["atomic"][0])
```

默认包含 `atomic`（62 条）和 `composite`（45 条）两个 split。

## 快速开始

```bash
pip install -r requirements.txt
cd bsc_quest_bench/skill_runner && bun install && cd ../..
python run_quest_bench.py --model MODEL --type atomic
python run_quest_bench.py --model MODEL --type composite
```

其余题型、环境、验证器与开发说明请参见 [英文 README](README.md)。

## 引用

```bibtex
@inproceedings{yang-etal-2026-evm-questbench,
  title = {EVM-QuestBench: An Execution-Grounded Benchmark for Natural-Language Transaction Code Generation},
  author = {Yang, Pei and Chen, Wanyi and Wang, Ke and Ai, Lynn and Yang, Eric and Shi, Tianyu},
  booktitle = {Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics},
  year = {2026},
  pages = {35513--35529},
  publisher = {Association for Computational Linguistics},
  url = {https://aclanthology.org/2026.acl-long.1642/}
}
```
