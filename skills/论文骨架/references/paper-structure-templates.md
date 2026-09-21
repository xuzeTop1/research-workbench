# 论文结构模板参考

## 中文理工科期刊（系统设计与实现类）

典型适用：计算机应用研究、计算机系统应用、电化教育研究、现代教育技术

```
题目（中文）
作者（单位/城市/邮编）
摘要（200-300字）：背景→问题→方法→结果→结论
关键词（5-7个，分号分隔）

0 引言 [~800字]
  领域背景 → 具体问题 → 现有不足 → 本文方案 → 贡献列表

1 相关工作 [~1200字]
  1.1 子方向A [~400字]
  1.2 子方向B [~400字]
  1.3 子方向C [~400字]

2 需求分析与总体设计 [~1500字]
  2.1 设计目标（功能+非功能需求）
  2.2 总体架构（图）
  2.3 数据模型

3 关键技术与实现 [~3000字] ← 核心章，占最大篇幅
  3.1 技术A（设计决策+实现细节+公式）
  3.2 技术B
  3.3 技术C
  3.4 安全设计

4 子系统设计与实现 [~1500字]（如有移动端/前端）
  4.1 ...
  4.2 ...

5 同步/通信协议 [~2000字]（如为卖点）
  5.1 安全握手
  5.2 消息格式
  5.3 一致性保障

6 实验与评测 [~2500字]
  6.1 环境与硬件规格
  6.2 测试套件与覆盖规模
  6.3 关键指标评测（多子节）
  6.4 端到端性能
  6.5 案例
  6.6 已知局限

7 总结与展望 [~500字]
  工作总结 → 不足声明 → 未来方向

参考文献 [15-30条]
```

---

## 英文CS会议/期刊（评测+方法类）

典型适用：AIED, EDM, ACL workshop, IEEE TLT, arXiv preprint → 投稿

```
Title
Authors (Affiliations)
Abstract (150-250 words)
Keywords

1. Introduction [~1.5 pages]
   Context → Problem → Gaps in prior work → Our approach → Contributions (numbered) → Paper structure

2. Related Work [~1.5 pages]
   2.1 Sub-direction A
   2.2 Sub-direction B
   2.3 Sub-direction C
   2.4 Positioning: "Unlike X, our work..."

3. Problem Formulation [~1 page]
   Formal definition → Notation table → Assumptions

4. Method / System Design [~3 pages] ← CORE
   4.1 Architecture overview (Figure)
   4.2 Component A (Algorithm + equation)
   4.3 Component B
   4.4 Component C
   4.5 Design rationale / Trade-offs

5. Experimental Setup [~1.5 pages]
   5.1 Dataset
   5.2 Baselines
   5.3 Metrics
   5.4 Evaluation protocol (annotation, statistical method)

6. Results and Analysis [~2.5 pages]
   6.1 Main experiment (Table)
   6.2 Ablation study
   6.3 Statistical significance
   6.4 Qualitative analysis / Case studies
   6.5 Latency / Resource overhead

7. Discussion and Limitations [~1 page]
   7.1 Implications
   7.2 Scope boundaries
   7.3 Threats to validity

8. Conclusion [~0.5 page]
   Summary → Specific future work

References [25-50 entries]
```

---

## 各节字数分配参考

| 节 | 占比范围 | 说明 |
|----|---------|------|
| 摘要 | 5% | 独立成篇，不看全文也能理解 |
| 引言 | 10-12% | 问题+贡献，不展开技术细节 |
| 相关工作 | 12-15% | 按子方向组织，不做流水账 |
| 方法/设计 | 30-35% | 最重，每个设计决策含WHY |
| 实验 | 20-25% | 设置+结果+分析三合一 |
| 讨论/局限 | 5-8% | 诚实但不自我否定 |
| 结论 | 3-5% | 不重复引言，给限定性总结 |
