# RISC-V 五级流水线 Trap-Handler Assassyn 实现方案

## 1. 概述：Trap 的全生命周期与其他新增机制

Trap 机制的实现并不破坏原有的流水线结构，而是作为一套平行系统附着在流水线上。

### 1.1 异常携带 (Exception Propagation)
当 IF, ID, EX, MEM 任意阶段检测到异常（如非法指令、地址对齐错误）时，**不立即**暂停流水线。

*   **行为**:
    *   将该指令标记为“异常状态”（`Exception_Valid = 1`）。
    *   记录异常原因（`Cause`）和辅助信息（`Tval`）。
    *   禁止该指令在后续阶段产生副作用（如禁止 MEM 写 SRAM）。

### 1.2 中断受理 (Interrupt Handling)
CPU 仅在 **WB 阶段开始**时观察全局使能信号与 MIP 高位信号，若中断存在，当前周期 WB 指令非异常指令则触发中断，允许当前 WB 指令顺利退休，将 **MEM 阶段及之前**的指令冲刷成 NOP。

### 1.3 控制流与副作用管理
当 WB 决定触发 Trap（或执行 `mret`）时，系统执行统一的 **Flush + Redirect** 操作。

### 1.3.1 同步冲刷 (Synchronous)
放置全局寄存器 `flush_all_pc_reg` 并连接到各个流水线，从而在下一个时钟上升沿 Flush 流水线中所有指令，并利用内部值完成 PC 重定向。

### 1.3.2 组合逻辑门控 (Combinational Gating)**
直接连接到 MEM 阶段 SRAM 的写使能端，确保即使 Trap 决定发生在周期内部也能实时拦截正在进行的不可逆写入。
  > SRAM Flush 信号： `flush_all_signal` （来自 CSRs 总控单元）

## 2. 控制信号添加

为了实现上述机制，需要在标准五级流水线中添加以下信号和数据通路：

### 2.1 流水线寄存器扩展 (Pipeline Registers)
在级间控制信号寄存器中增加一组**异常向量**：
*   `Exception_Valid` (1 bit): 指示当前指令是否已触发异常。
*   `Exception_Code` (32 bits): 异常编码（对应 mcause）。
*   `Exception_Val` (32 bits): 附加信息（对应 mtval，如错误地址）。
*   `PC` (32 bits): 当前指令的 PC 值，供 Trap 处理时保存到 mepc。
*   `CSR_addr` (12 bits): 当前指令访问的 CSR 地址，供 WB 使用，为 `0x00` 时不写入。

在级间数据寄存器中增加第二个结果位：
*  `CSR_result_data` (32 bits): 在 EX 阶段计算出的 CSR 值，将写入对应 CSR。

### 2.2 全局控制信号 (Global Signals)
*   `flush_all_pc` (32 bit): 非 0 时触发全局冲刷并重定向 PC。
*   `flush_all_signal` (1 bit): 非 0 时禁止 MEM 阶段 SRAM 写入。

### 2.3 阶段特有信号与新增逻辑

#### **ID Stage**
*   `Current_Mode`: 检测 CSR 访问权限，若非法置起 `Exception_Valid`。
*   **ECALL/EBREAK**: 译码时直接置起 `Exception_Valid`。
*   `CSR_read_data`: 从 CSR Unit 读取出的数据，作为操作数进入 EX 阶段。
*   `CSR_sel`: Hazard 单元生成的 CSR RAW 冒险旁路选择信号。

#### **EX Stage**
*   **新增逻辑**:
    *   **CSR ALU**: 计算 CSRRW/RS/RC 的新值。
    *   **Forwarding**: 接收来自级间 CSR 寄存器的旁路数据。
    *   **Result Muxing**: 选择 ALU 结果或 `CSR_read_data` 作为最终写回数据。

#### **MEM Stage**
*   `Flush_Trap`: 来自 CSR 控制单元的冲刷信号，置高位时冲刷 SRAM 写使能寄存器并拉低当周期写使能信号。

#### **WB Stage (Controller)**
*   基本是控制信号以及与 CSRs Unit 的互动。

## 4. CSRs 逻辑

### 4.1 需实现 CSRs 及其读写行为
每一个 CSR 都有其独特的 **Fields** 定义，且每个 **Field** 遵循不同的读写规则。可以通过掩码与硬连线实现 **WPRI(Read-only)** 对应行为，通过逻辑电路实现 **WLRL** 与 **WARL** 对应行为。以下是需要实现的 CSRs 列表以及其读写电路：

* **Current_Mode**: 当前权限，Manual 中没有定义但是其依旧需要维护。
    *   Bits(2)，合法值为 `00`: U-mode 与 `11`: M-mode
    *   合法值电路映射：截取最低位并扩展到 2 位。
* **misa** (`0x301`): 只读，硬连线为 `0x40000100` (RV32I)。
* **mstatus** (`0x300`): 当前处理器状态。
    *   MPP (Bits[11:12]): WARL，合法值为 `00` (U-mode) 或 `11` (M-mode)，电路同`Current_Mode` 设计。
    *   MPIE (Bit[7]): WARL。
    *   MIE (Bit[3]): WARL。
    *   其余位均为 WPRI: 硬连线为0，写入时掩码为 `0x00001888`。
* **mie** (`0x304`): Machine Interrupt Enable。
    *   MEIE (Bit[11]): WARL。
    *   MTIE (Bit[7]): WARL。
    *   MSIE (Bit[3]): WARL。
    *   写入时使用掩码 `0x00000888`。
* **mip** (`0x344`): Machine Interrupt Pending。
    *   MEIP (Bit[11]): 只读，来自外部中断线。
    *   MTIP (Bit[7]): 只读，来自定时器中断线。
    *   MSIP (Bit[3]): WARL，可由 CSR 指令写入 (软件中断)。
    *   写入时掩码为 `0x00000008`。
* **mtvec** (`0x305`): Trap 向量基地址与模式，控制 Trap Entry 时 PC 跳转位置。
    *   Base (Bits[2:31]): WARL，需保证 4 字节对齐 (实现 trival)。
    *   Mode (Bits[0:1]): WARL，合法值为 `0` (Direct) 或 `1` (Vectored)。
    *   写入时使用掩码 `0xFFFFFFFD` 即可。
* **mepc** (`0x341`): 可读写，Trap 发生时保存 PC。
    *   最低 2 位强制为0，使用掩码`0xFFFFFFFC`。
* **mcause** (`0x342`): 可读写，Trap 发生时保存原因。
    *   Interrupt (Bit[31]): 标记是否为中断，1 为中断，0 为异常。
    *   Code (Bits[0:30]): Trap 原因代码。
    *   写入时使用掩码 `0xFFFFFFFF`。
* **mtval** (`0x343`): 可读写，Trap 发生时保存附加信息 (如错误地址)。
    *   写入时使用掩码 `0xFFFFFFFF`。
* **mtscratch** (`0x340`): 可读写，任意用途寄存器。 

* **mvendorid** (`0xF11`), **marchid** (`0xF12`), **mimpid** (`0xF13`), **mhartid** (`0xF14`), **mconfigptr** (`0xF15`), **medeleg** (`0x302`), **mideleg** (`0x303`), **mcounteren** (`0x306`), **mstatush** (`0x310`), **medelegh**(`0x312`), **mtinst**(`0x34A`), **mtval2**(`0x34B`): 只读，返回 0。

> **注**: 所有未列出的 CSR 视为不存在，访问时直接报错。
> **注**: 使用 `0x00` 作为 CSR 写入地址表示不进行任何写入操作。

### 4.2 CSRs 总体封装
将 CSR 作为一个整体抽象成如下接口，处理与流水线的交互、Trap 逻辑和原子性更新。

#### 4.2.1 读写控制逻辑
*   **读取 (ID Stage)**: 组合逻辑。
    *   根据 `Read_Addr Bits(12)` 多路选择输出 `CSR_read_data Bits(32)`。
    >   所有引发 `illegal instruction` 的指令均在 ID 阶段被筛出并消除一切会导致错误的副作用。

*   **指令写入 (WB Stage)**:
    *   接收合法的 `csr_waddr Bits(12)`、`csr_wdata Bits(32)`。

#### 4.2.2 Trap 状态机逻辑 (WB Stage Triggered)
当收到来自 WB 阶段的 `Exception_Vaild Bits(1)` 信号时，或没有收到该信号但是中断受理逻辑通过，则状态机在一瞬间完成以下并行操作（优先级高于指令写入）：
1.  `mepc` $\leftarrow$ `Trap_PC` (当前 PC 或 Next PC)
2.  `mcause` $\leftarrow$ 来自 WB 的 `Exception_Code` 或来自内部的中断代码。
3.  `mtval` $\leftarrow$ `Exception_Val`
4.  `mstatus.MPIE` $\leftarrow$ `mstatus.MIE`
5.  `mstatus.MPP` $\leftarrow$ `Current_Mode`
6.  `mstatus.MIE` $\leftarrow$ `0`
7.  `Current_Mode` $\leftarrow$ `M-Mode (11)`
> 注：如果在 M-Mode 下发生 Trap，则终止模拟并报错（二重 Trap）。

当收到 `Trap_Return_Signal (mret)` 时：
1.  `mstatus.MIE` $\leftarrow$ `mstatus.MPIE`
2.  `Current_Mode` $\leftarrow$ `mstatus.MPP`
3.  `mstatus.MPIE` $\leftarrow$ `1`
4.  `mstatus.MPP` $\leftarrow$ `U-Mode (00)`

#### 4.2.3 CSRs I/O 接口总结

* 输出
| 端口名 | 描述 |
| :----- |:---|
| `current_mode`  | 全局 2 位寄存器 Current_Mode 本身，ID 阶段用于权限检查 |
| `CSR_read_data` | Bits(32) 供 DecoderImpl 使用|
| `flush_all_pc`  | 全局 32 位寄存器，非 0 时冲刷整条流水线并使 PC 取对应值 |
| `flush_all_signal` | Bits(1) 供 MEM 使用，非 0 时冲刷内部写入 |

* 输入
| 端口名        | 描述                                     |
| :------------ | :-------------------------------------- |
| `csr_raddr`         | Bits(12) 来自 ID 阶段的读地址             |
| `csr_waddr`         | Bits(12) 来自 WB 阶段的写地址             |
| `csr_wdata`         | Bits(32) 来自 WB 阶段的写数据             |
| `csr_we`            | Bits(1)  来自 WB 阶段的写使能             |
| `Exception_Vaild`   | Bits(1)  来自 WB 阶段，指令携带的控制信号  |
| `Exception_Code`    | Bits(32) 来自 WB 阶段，异常代码           |
| `Exception_Val`     | Bits(32) 来自 WB 阶段，异常附加信息       |
| `WB_PC`             | Bits(32) 来自 WB 阶段，该阶段指令 PC      |
| `MEM_PC`            | Bits(32) 来自 MEM 阶段，该阶段指令 PC     |
