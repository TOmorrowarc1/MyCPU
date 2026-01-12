# HazardUnit 模块设计方案

## 1. 模块概述

**HazardUnit** 是一个 **纯组合逻辑 (`Downstream`)** 模块。

*   **职责**：
    1.  **前瞻控制 (Forwarding Logic)**：检测 RAW 冒险，生成多路选择信号，控制 EX 阶段 ALU 的操作数来源。
    2.  **阻塞控制 (Stall Logic)**：在 IF 与 MEM 共同使用一个只有一个接口，不支持 READ & WRITE by HALF 的 SRAM 的情况下，所有 EX 阶段的读取与写入，MEM 阶段的写入都需**生成流水线停顿（Stall）信号**。
    >   逻辑如下：一切数据与指令的同时操作都构成**结构冒险**，仲裁时**先受理前者**。由于读取需要一个周期完成，写入需先读取再剪辑拼接最后写入共两个周期完成，因此 EX 阶段读取和 EX & MEM 阶段写入都需要 stall。
*   **特性**：无内部状态（Stateless）。它依赖流水线各级“回传”的实时控制信号包作为真值来源。

## 2. 接口定义

### 2.1 输入接口 (Inputs)

HazardUnit 需要三类信息：**当前指令需求** (Id)，**先前指令结果**(EX/MEM/WB)和**先前指令类型**(EX/MEM)。

```python
class HazardUnit(Downstream):
    @downstream.combinational
    def build(self,
        # --- 1. 来自 ID 级 (当前指令需求) ---
        rs1_idx: Bits(5),    # 源寄存器 1 索引 (Bits 5)
        rs2_idx: Bits(5),    # 源寄存器 2 索引 (Bits 5)

        # --- 2. 来自流水线各级 (实时状态回传) ---
        # 各级 Module build() 的返回值
        ex_rd:Bits(5),     # EX 级目标寄存器索引
        ex_is_load:Bits(1),  # EX 级是否为 Load 指令
        ex_is_store:Bits(1), # EX 级是否为 Store 指令
        mem_is_store:Bits(1), # MEM 级是否为 Store 指令
        mem_rd:Bits(5),      # MEM 级目标寄存器索引
        wb_rd:Bits(5),    # WB 级目标寄存器索引
    ):
    pass
```

### 2.2 输出接口 (Outputs)

输出分为两类：给 EX 级的数据选择信号，和给 IF/ID 级的流控信号。

*   **Forwarding Selectors** (4-bit):
    *   `rs1_op1`: 操作数 1 选择码
    *   `rs2_op2`: 操作数 2 选择码
    *   *编码定义*: 见`control_signals.py`

*   **Pipeline Controls** (1-bit):
    *   `stall_if`: 冻结 Fetcher 与 Decoder。

## 3. HazardUnit 内部实现

### 3.1 时空映射：ID 站在“现在”预测“未来”

假设当前是 **Cycle T**。
*   **ID 级**：指令 `Inst_Current`。
*   **EX 级**：指令 `Inst_N-1`。
*   **MEM 级**：指令 `Inst_N-2`。
*   **WB 级**：指令 `Inst_N-3`。

当 `Inst_Current` 到达 EX 级时（**Cycle T+1**）：
*   `Inst_N-1` 将到达 MEM 级 -> 要从 `ex_bypass_reg` 读取其结果。
*   `Inst_N-2` 将到达 WB 级 -> 要从 `mem_bypass_reg` 读取其结果。
*   `Inst_N-3` 将退休 -> 要从 `wb_bypass_reg` 读取其结果。

### 3.2 build() 逻辑

基于上述映射，`HazardUnit` 的决策逻辑如下：

#### 3.2.1 检测 Load/Store 并生成 Stall 信号
*   **条件**：`ex_is_load == 1 || ex_is_store == 1 || mem_is_store == 1`。
*   **原因**：结构 Hazard（数据 Hazard 在 Stall 的场景下完全被覆盖）。
*   **动作**：`stall_if = 1`。

#### 3.2.2 检测 Forwarding 并生成 Mux 选择码
生成选择码 `rs1_sel` 与 `rs2_sel`。以`rs1_sel` 为例，生成逻辑如下：

1.  **优先级 1**：`rs1_idx == ex_rd`
    *   **动作**：`rs1_sel = Bits(4)(0010)`

2.  **优先级 2**：`rs1_idx == mem_rd`
    *   **动作**：`rs1_sel = Bits(4)(0100)`

3.  **优先级 3**：`rs1_idx == wb_rd`
    *   **动作**：`rs1_sel = Bits(4)(1000)`

如果都没有匹配，则 `rs1_sel = Bits(4)(0001)`。