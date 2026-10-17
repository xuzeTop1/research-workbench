# 引用格式体系速查

## GB/T 7714-2015（中国大陆期刊）

### 著录格式

**期刊文章 [J]**
```
[序号] 主要责任者. 题名[J]. 刊名, 年, 卷(期): 起止页码. DOI.
```
示例（虚构，仅演示格式）：
```
[2] Smith A, Jones B, Wang C, et al. Title of the referenced article[J]. Journal Name, 2023, 45(3): 102274.
```

**会议论文 [C]**
```
[序号] 责任者. 题名[C]//论文集名. 出版地: 出版者, 年: 页码.
```
示例（虚构）：
```
[5] Doe J, Roe R, Roe P, et al. Paper title in proceedings[C]//Proc. of Conference (Conf 2025). Lecture Notes in Computer Science, vol 15877. Cham: Springer, 2025: 251-266.
```

**预印本 [PP/OL]**
```
[序号] 责任者. 题名[PP/OL]. arXiv(年-月). URL. DOI:xxx.
```
示例（虚构）：
```
[4] Author A, Author B, Author C, Author D. Paper title here[PP/OL]. arXiv(2025-02). https://arxiv.org/abs/2502.xxxxx. DOI:10.48550/arXiv.2502.xxxxx.
```

**中文期刊（示例）**
```
[9] 张三, 李四, 王五, 等. 某领域综述主题[J]. 期刊名, 2025, 34(6): 1-11.
```

### 关键规则
- 作者 ≤ 3 人全部列出；> 3 人列前 3 + "et al." / "等"
- 英文作者：姓在前名缩写在后（Kasneci E）
- 卷号不缩写，期号用括号
- 文献类型标志码紧跟题名：`[J]` `[C]` `[M]` `[D]` `[PP/OL]` `[EB/OL]` `[R]` `[S]` `[N]`

---

## IEEE（国际 CS/工程期刊会议）

### 著录格式

**期刊**
```
[#] A. A. Author, B. B. Author, and C. C. Author, "Title of paper," *Abbrev. J. Title*, vol. X, no. X, pp. xxx–xxx, Mon. Year, doi: xx.xxxx/xxxxx.
```

**会议**
```
[#] A. A. Author, "Title of paper," in *Proc. Conf. Abbrev.*, City, Year, pp. xxx–xxx.
```

**预印本**
```
[#] A. Author, "Title of paper," arXiv:xxxx.xxxxx, Year.
```

**书籍**
```
[#] A. A. Author, *Title of Book*, xth ed. City: Publisher, Year.
```

### 关键规则
- 名缩写在姓前（A. A. Author）
- 标题用双引号（文章），斜体（期刊/书名）
- 月份缩写（Jan., Feb., Mar., ..., Dec.）
- 超过 6 位作者用 "et al."
- DOI 推荐但非必须

---

## Vancouver / NLM（ICMJE 推荐；多数生物医学期刊）

**期刊**
```
[#] Author AA, Author BB, Author CC. Title of article. Abbrev Journal Title. Year;Vol(Issue):pages. doi:xx.xxxx/xxxxx
```

### 关键规则
- 作者：姓 + 名首字母，无句点；作者数上限按期刊规定（常见：前 6 位后加 "et al."）——以期刊 Instructions for Authors 为准
- 刊名用 NLM 缩写（NLM Catalog 可查），无斜体
- 按正文首次出现顺序编号；正文用方括号、圆括号或上标数字，按期刊要求

## AMA（JAMA 等期刊）

```
1. Author AA, Author BB, Author CC. Title of article. *Abbrev Journal Title*. Year;Vol(Issue):pages. doi:xx.xxxx/xxxxx
```
- 正文引用为上标数字；作者多时的截断规则以 AMA Manual 与期刊要求为准（常见：超过 6 位列前 3 位 + et al.）

## ACM Reference Format（ACM 期刊/会议）

```
[#] Firstname Lastname, Firstname Lastname, and Firstname Lastname. Year. Title of the paper. In Proceedings of
the Conference Name (Conf 'YY). ACM, City, Country, pages. https://doi.org/xx.xxxx/xxxxx
```
- 以 ACM 官方模板生成的参考文献为准（acmart + BibTeX）；人工核对作者全名、年份位置与 DOI

## APA 7th（社会科学）

```
Author, A. A., Author, B. B., & Author, C. C. (Year). Title of article. *Journal Name, Vol*(Issue), pages. https://doi.org/xx.xxxx/xxxxx
```

> 以上均为格式骨架示例，具体细则（作者截断、缩写、标点）以目标期刊的 Instructions for Authors 为准。

---

## 正文引用标注

| 格式体系 | 文中引用方式 |
|---------|-------------|
| GB/T 7714 | `[1]` 或 `[1-3]` 或 `[1,2,5]` |
| IEEE | `[1]` 或 `[1]–[3]` 或 `[1], [2], [5]` |
| APA | (Author, Year) 或 Author (Year) |
| Vancouver / AMA | `[1]`、`(1)` 或上标 ¹，按期刊要求 |

### 标注位置规则

- 句末标点前：`...已被广泛采用[3]。` ✓
- 不跨句引用：`[1]提出了一种方法[2]。` ✗ → 拆成两句各标各的
- 连续引用同一来源多次：不重复标，用"该工作进一步..."替代
