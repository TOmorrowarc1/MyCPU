# DataHazardUnit 模块设计方案

## 1. 模块概述

**DataHazardUnit** 是一个 **纯组合逻辑 (`Downstream`)** 模块。

*   **职责**：
    1.  **前瞻控制 (Forwarding Logic)**：检测 RAW 冒险，生成多路选择信号，控制 EX 阶段 ALU 的操作数来源。
    2.  **阻塞控制 (Stall Logic)**：检测 Load-Use 冒险，生成流水线停顿（Stall）和气泡（Flush）信号。
*   **特性**：无内部状态（Stateless）。它依赖流水线各级“回传”的实时控制信号包作为真值来源。

## 2. 接口定义

### 2.1 输入接口 (Inputs)

HazardUnit 需要两类信息：**“当前想要什么”** (ID级) 和 **“前面正在产出什么”** (EX/MEM/WB级)。

```python
class DataHazardUnit(Downstream):
    @downstream.combinational
    def build(self,
        # --- 1. 来自 ID 级 (当前指令需求) ---
        rs1_idx: Bits(5),    # 源寄存器 1 索引 (Bits 5)
        rs2_idx: Bits(5),    # 源寄存器 2 索引 (Bits 5)
        rs1_used: Bits(1),   # 是否需要读取 rs1 (Bits 1) - 避免 LUI 等指令的虚假冒险
        rs2_used: Bits(1),   # 是否需要读取 rs2 (Bits 1)

        # --- 2. 来自流水线各级 (实时状态回传) ---
        # 这些是各级 Module build() 的返回值 (Record 类型)
        ex_rd:Bits(5),     # EX 级控制包
        ex_is_load:Bits(1),  # EX 级是否为 Load 指令
        mem_rd:Bits(5),      # MEM 级目标寄存器索引
        mem_ctrl: Value,     # MEM 级控制包 (mem_ctrl_t)
    ):
    pass
```

### 2.2 输出接口 (Outputs)

输出分为两类：给 EX 级的数据选择信号，和给 IF/ID 级的流控信号。

*   **Forwarding Selectors** (3-bit):
    *   `fwd_op1`: 操作数 1 选择码
    *   `fwd_op2`: 操作数 2 选择码
    *   *编码定义*: `001`: RegFile, `010`: EX_Bypass, `100`: MEM_Bypass

*   **Pipeline Controls** (1-bit):
    *   `stall_if`: 冻结 Fetcher。

---

你的分析逻辑非常严密，特别是关于 **Load-Use Stall** 的判断条件，完全正确。

你提到的关于 **EX 阶段** 和 **MEM 阶段** 结果获取的时间差问题（即“EX 阶段的指令在下一拍会进入 MEM，所以要从 MEM Bypass 取”），是设计 **ID 级预判型 Forwarding** 最烧脑的地方。

为了确保逻辑万无一失，我们需要建立一个严格的 **“时空映射表”**。

## 3. DataHazardUnit 内部实现

### 1. 时空映射：ID 站在“现在”预测“未来”

假设当前是 **Cycle T**。
*   **ID 级**：指令 `Inst_Current`。
*   **EX 级**：指令 `Inst_N-1`。
*   **MEM 级**：指令 `Inst_N-2`。
*   **WB 级**：指令 `Inst_N-3`。

当 `Inst_Current` 到达 EX 级时（**Cycle T+1**）：
*   `Inst_N-1` 将到达 MEM 级 -> 它的结果在 `mem_forward_data` (来自 MEM 模块输出)。
*   `Inst_N-2` 将到达 WB 级 -> 它的结果在 `wb_forward_data` (来自 WB 模块输出)。
*   `Inst_N-3` 将退休 -> 它的结果已写入 Register File。

### 2. DataHazardUnit 逻辑真值表

基于上述映射，`DataHazardUnit` 的决策逻辑如下：

#### 2.1 检测 Load-Use (必须 Stall)
这是唯一需要暂停的情况。
*   **条件**：`id_rs1 == ex_rd` **且** `ex_is_load`。
*   **原因**：`Inst_N-1` 是 Load。在 Cycle T+1，它在 MEM 级刚开始读 SRAM，数据还没出来。EX 级的 `mem_forward_data` 线拿不到数据。
*   **动作**：`Stall = 1`。

#### 2.2 检测 Forwarding (生成 Mux 选择码)
如果没有 Stall，我们生成发给 EX 的选择码 `fwd_op1_sel`。

1.  **优先级 1 (最近)**：`id_rs1 == ex_rd` (且不是 Load)
    *   **预测**：在 T+1 时，数据在 MEM 级。
    *   **动作**：`Sel = 010` (选择 `mem_forward_data`，即 MEM->EX 旁路)。

2.  **优先级 2 (次近)**：`id_rs1 == mem_rd`
    *   **预测**：在 T+1 时，数据在 WB 级。
    *   **动作**：`Sel = 100` (选择 `wb_forward_data`，即 WB->EX 旁路)。

### 4. 完整的 DataHazardUnit 实现代码

```python
class DataHazardUnit(Downstream):
    @downstream.combinational
    def build(self,
              # Inputs (Current Instruction Needs)
              rs1_idx: Value, rs2_idx: Value,
              rs1_used: Value, rs2_used: Value,
              
              # Inputs (Pipeline Status from Return Values)
              ex_rd: Value,
              ex_ctrl_is_load: Value,
              mem_rd: Value,
            ):
        
        # --- 1. 解包状态 ---
        ex_rd  = ex_ctrl.mem_ctrl.wb_ctrl.rd_addr
        ex_we  = ex_ctrl.mem_ctrl.wb_ctrl.rf_wen
        ex_load= ex_ctrl.mem_ctrl.is_load
        
        mem_rd = mem_ctrl.wb_ctrl.rd_addr
        mem_we = mem_ctrl.wb_ctrl.rf_wen
        
        wb_rd  = wb_ctrl.rd_addr
        wb_we  = wb_ctrl.rf_wen # 或 rd!=0

        # --- 2. 辅助函数：针对一个操作数的检测 ---
        def check_hazard(src_idx, src_used):
            # 默认：无冲突，用寄存器值 (00)
            # 这里的编码对应 EX 阶段 Mux 的端口：
            # 00: Packet Data
            # 01: Unused
            # 10: MEM_Fwd (来自上条指令)
            # 11: WB_Fwd (来自上上条指令)
            
            fwd_sel = Bits(2)(0)
            stall   = Bits(1)(0)
            use_wb  = Bits(1)(0) # ID 级修补信号
            
            with Condition(src_used & (src_idx != 0)):
                # 检查 EX 冲突 (优先级最高)
                with Condition(ex_we & (ex_rd == src_idx)):
                    if ex_load:
                        stall = Bits(1)(1) # Load-Use -> Stall
                    else:
                        fwd_sel = Bits(2)(0b10) # ALU -> Forward from MEM (Next Cycle)
                
                # 检查 MEM 冲突 (优先级次之)
                with Condition(mem_we & (mem_rd == src_idx)):
                    # 如果 EX 没冲突，才看 MEM
                    with Condition(~(ex_we & (ex_rd == src_idx))):
                        fwd_sel = Bits(2)(0b11) # Forward from WB (Next Cycle)
                
                # 检查 WB 冲突 (优先级最低，ID 级修补)
                with Condition(wb_we & (wb_rd == src_idx)):
                    # 如果 EX 和 MEM 都没冲突
                    with Condition(~(ex_we & (ex_rd == src_idx)) & ~(mem_we & (mem_rd == src_idx))):
                        use_wb = Bits(1)(1) # 告诉 Decoder 用 WB 数据修补
            
            return stall, fwd_sel, use_wb

        # --- 3. 执行检测 ---
        stall_1, sel_1, fix_1 = check_hazard(rs1_idx, rs1_used)
        stall_2, sel_2, fix_2 = check_hazard(rs2_idx, rs2_used)
        
        # --- 4. 汇总输出 ---
        global_stall = stall_1 | stall_2
        
        return global_stall, sel_1, sel_2, fix_1, fix_2
```