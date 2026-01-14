# RISC-V Trap-Handler 实现机制

## 1. RISC-V Privileged ISA 抽象：有限状态机

相比于 RISC-V Unprivileged（非特权）部分仅关注通用计算的简洁性，Privileged ISA提供的抽象更为复杂且具备层次感。Privileged ISA 可以被视为一个巨大的、通过硬件实现的**有限状态机 (Finite State Machine, FSM)**，由以下四个元素定义：

*   **权限 (Privilege)**:
    RISC-V ISA 采用分层级的权限保护模型，旨在隔离系统资源与应用程序。权限由高向低分为 **M (Machine)**、**S (Supervisor)**、**U (User)** 等多个等级。
    *   不同的权限等级面对的“硬件抽象”不同：高权限模式（如 M-Mode）拥有对底层硬件的完全控制权，能够访问所有控制状态寄存器 (CSRs) 并执行特权指令；而低权限模式（如 U-Mode）的视图被限制，无法感知或操作涉及系统控制的 CSRs，从而保证了系统的安全性与稳定性。

*   **状态 (State)**:
    在 Unprivileged ISA 提供的通用寄存器（如 x0-x31）与 PC 之外，Privileged ISA 引入了一组 **控制与状态寄存器 (CSRs)** 来定义处理器的全系统状态。
    *   系统的状态不仅由 CSR 中的数值决定，还包括 CSR 内部特定 **Field (字段)** 的值，以及值映射到的语义（e.g. `mstatus` 中的 `MIE` 位代表全局中断开关，`misa` 寄存器中的特定位组合代表了 CPU 支持的指令集扩展能力）。

*   **事件 (Event)**:
    事件是驱动状态机发生迁移的触发器，主要包括 **异常 (Exception)**、**中断 (Interrupt)** 或特殊指令（如 `ecall`），外在表现为**控制权的移交**。本项目语境下 Event 基本等同于 Trap，分为水平 Trap 与垂直 Trap，由提权与否区分。

    > *   **异常 (Exception)**: 是**同步 (Synchronous)** 事件，由当前执行的指令直接产生（例如：非法指令、地址对齐错误、缺页异常）。异常通常意味着当前指令执行失败或需要软件介入。
    > *   **中断 (Interrupt)**: 是**异步 (Asynchronous)** 事件，通常由处理器外部设备（如定时器、磁盘控制器、键盘）产生，与当前执行的指令流无关。

*   **协议 (Protocol)**:
    这是定义状态机行为的规则集合，包含两部分：
    1.  **静态规则**: CSRs 及其 Fields 固有的读写行为（如 Fields 的 WARL、WLRL、WPRI 属性）。
    2.  **动态逻辑**: 当“事件”发生时，硬件自动执行的一系列状态迁移操作（如 Trap Entry：保存 PC 到 `mepc`、更新 `mcause`、关闭中断、跳转至 `mtvec` 等）。

> **Why so complicated?**
> 之所以 Privileged ISA 的抽象复杂度显著提升，是因为硬件的角色发生了本质转变：
> 从 Unprivileged 阶段单纯执行逻辑运算的 **“计算机器” (Turing Complete Machine)**，进化为系统错误的 **“发现者”** 与突发状况的 **“第一处理人” (First Handler)**。
> 这种转变要求硬件必须向软件暴露丰富的内部信息并与操作系统软件进行精密的互动。因此，硬件抽象必须从单纯的数据流处理延拓到包含权限管理、上下文切换与异常报告的复杂形态。

## 2. 项目概述

本项目旨在实现一个支持 RISC-V Privileged ISA 中 **M-mode 子集** 的 CPU 模拟器，核心目标是完整复现 **Trap-Handler (异常处理)** 机制。

> **关于 Trap-Handler:**
> **Trap-Handler** 用于处理CPU运行过程中遇到的错误或中断，处理过程分为两个部分：
> 1.  **硬件机制 (Mechanism)**: 当 Trap 发生时，CPU 硬件自动暂停当前程序，保存现场（PC 与 状态），并强制跳转到预设的入口地址（Trap Vector）。这是本项目模拟的重点。
> 2.  **软件策略 (Policy)**: 位于入口地址的一段特权级代码（通常由 OS 或固件编写）。它负责分析硬件报告的信息（读取 `mcause`, `mtval`），执行相应的补救措施（如杀死进程、调度任务、模拟指令），最后通过 `mret` 指令指示硬件恢复现场并返回。

---

## 3. CSR 架构概述

### 3.1 CSR 寻址与访问控制 (Addressing and Access Control)

CSR (Control and Status Register) 是 Privileged ISA 的核心存储单元，用于记录 CPU 的配置、状态以及 Trap 发生时的上下文信息。

*   **地址空间**: CSR 拥有独立的 **12位** 地址空间（$0x000$ ~ $0xFFF$），理论上支持 4096 个寄存器，但在实际架构中只有一小部分被定义和实现。
*   **地址即属性 (Address as Attribute)**: CSR 的地址并非随机分配，其二进制编码的特定位段直接定义了该寄存器的访问权限，所有读写指令需进行以下检查：
    1.  **读写属性 (R/W Attribute)**: 由最高两位 **[11:10]** 决定。
        *   `00` / `01` / `10`: **Read/Write (RW)**。允许读写。
        *   `11`: **Read-Only (RO)**。只读。任何试图写入的操作都应被视为非法。
    2.  **特权等级 (Privilege Level)**: 由次高两位 **[9:8]** 决定。
        *   `00`: User (U-Mode)
        *   `01`: Supervisor (S-Mode)
        *   `10`: Hypervisor (H-Mode)
        *   `11`: Machine (M-Mode)
        *   **规则**: 仅当 `Current_Privilege_Mode >= CSR_Privilege_Level` 时，才允许访问。

*   **异常处理**: 任何违反上述规则的访问（即：访问未实现的 CSR、当前权限不足、或向只读 CSR 写入）均会立即触发 **Illegal Instruction Exception (Code 2)**。（具体的各类 Trap 原因及编码将在 `mcause` 寄存器的说明中详细展开）。

### 3.2 Field 概念与行为规范

为了提高硬件的灵活性与兼容性，一个 CSR 内部通常被细分为多个 Field（域）。每个 Field 根据其功能定义遵循不同的读写规则，包含以下三种规则：

### 1. WPRI (Writes Preserve Values, Reads Ignore Values) / Read-Only
*   **定义**:
    *   **WPRI**: 为未来标准扩展预留的保留位。软件不应假设其值，硬件通常将其硬连线为 0。
    *   **Read-Only**: 架构定义为固定值（e.g. `misa` 中的某些特性位）或由硬件状态驱动（e.g. `mip` 中的外设中断位）。
*   **读写逻辑**:
    *   **读**: WPRI 在未实现时始终返回全零, read-only返回根据硬件状态变化的值。
    *   **写**: **忽略写入操作**，不应抛出异常。

### 2. WLRL (Write/Read Only Legal Values)
*   **合法值**: 该 Field 只有一部分取值在架构上是合法的（e.g. 某些状态枚举）。
*   **读写逻辑**:
    *   **读**: 始终返回合法值。
    *   **写**:
        *   如果写入值在合法集合内：正常更新。
        *   如果写入值**不合法**：硬件必须**根据CSR当前值与写入值**将其映射到一个确定的合法值（e.g. 保持原值，或截断到最近的合法值，或直接置 0）。
        *   写入非法值**可以但不必要**触发异常（一般不触发而直接修正）。

### 3. WARL (Write Any Values, Reads Legal Values)
*   **读写逻辑**:
    *   **读**: 始终返回当前实际生效的合法值。
    *   **写**: 可以写入任何值，合法值直接写入，不合法值由hart状态与写入值映射到合法值，不报错。
  
---

## 4. Trap-Handler 核心 M-mode CSRs

构建 Trap-Handler 机制只需要关注 M-Mode 的部分核心寄存器。

### 4.1 misa (Machine ISA Register)

*   **地址**: `0x301`
*   **用途**: 标识 CPU 支持的 ISA 宽度与扩展指令集。

#### 4.1.1 字段定义

*   **`MXL` (Bits 31:30)**: **M**achine **X**LEN。指示寄存器宽度。
    *   `01`: 32-bit (RV32)
    *   `10`: 64-bit (RV64)
*   **`Extensions` (Bits 25:0)**: 每一位对应一个字母 (A-Z)，`0`/`1` 表示对应扩展 未/已 实现。
    *   Bit 0 (A), Bit 8 (I), Bit 12 (M), etc.
*   **保留位**: Bits 29:26 应恒为 `0`。
*   **访问属性**: 规范定义为 **WARL**，但若模拟器不支持动态切换指令集，应实现为 **Read-Only**。

### 4.2 mstatus (Machine Status Register)

*   **地址**: `0x300`
*   **用途**: CPU 的总控制台，追踪并控制全局运行状态（**中断使能**与**特权级**）。

#### 4.2.1 核心字段定义

| 字段名 | 位域 (RV32) | 名称 | 描述 |
| :--- | :--- | :--- | :--- |
| **MIE** | Bit 3 | Machine Interrupt Enable | 全局中断开关。<br>`1`: 允许中断; `0`: 禁止中断。 |
| **MPIE** | Bit 7 | Machine Previous IE | **中断使能备份**。<br>Trap 发生时，硬件自动将旧的 MIE 值备份至此。 |
| **MPP** | Bits 12:11 | Machine Previous Privilege | **特权级备份**。<br>Trap 发生时，硬件自动将之前的特权模式备份至此。<br>*(注: 若仅支持 U/M 模式，合法值仅为 `00` 和 `11`)*。 |

*   所有Field访问属性都是 **WARL**。

#### 4.2.2 状态迁移协议

本协议定义了硬件如何利用上述字段处理中断判定、Trap 进入与 Trap 返回。

**A. 中断受理逻辑**

硬件在 **每条指令执行结束后**，根据以下公式检查是否响应中断：

```text
中断有效 = (Pending & Enable) && Global_Enable
```

其中 `Pending` 来自 `mip`，`Enable` 来自 `mie`。而 **`Global_Enable`** 的判定取决于当前特权级：

1.  **Current Mode = M-Mode**:
    *   取决于 `mstatus.MIE`。
    *   *含义*: M-Mode 可以选择屏蔽发往自己的中断。
2.  **Current Mode = U-Mode**:
    *   **始终为 True** (无视 `mstatus.MIE`)。
    *   *含义*: 低权限无法屏蔽发往高权限的中断。`MIE` 仅在 CPU 处于 M-Mode 时才生效。

**B. 进入 Trap**

当硬件决定受理一个 Trap（异常或中断）时，状态机原子性地执行以下更新：

1.  **备份特权级**: `mstatus.MPP = Current_Mode`
    > **注**: 如果 CPU 原本就在 M-Mode 运行（例如正在处理中断）时发生了**异常**（如非法地址），此时 `Current_Mode` 为 M，因此 `MPP` 会被置为 `11`。
    > **注**: CPU在未实现特定 Privileged 扩展时无法处理**二重 Trap** ，直接上传 `critical error` 到平台即可（即崩溃）。 
2.  **备份中断使能**: `mstatus.MPIE = mstatus.MIE`
3.  **关中断**: `mstatus.MIE = 0`
    *   除非 Handler 拉高 `mstatus.MIE`，否则中断导致二重 Trap 的情况不会出现。
4.  **提权**: `Current_Mode = Machine (11)`

**C. 退出 Trap**

当执行 `mret` 指令从 M-mode 返回时，硬件执行逆操作：

1.  **恢复特权级**: `Current_Mode = mstatus.MPP`
2.  **恢复中断使能**: `mstatus.MIE = mstatus.MPIE`
3.  **重置备份**:
    *   `mstatus.MPIE = 1`
    *   `mstatus.MPP = U_Mode` (设为支持的最低权限)

### 4.3 mip & mie (Interrupt Control Registers)

*   **`mie` (Machine Interrupt Enable)**: 特定中断受理使能。
    *   **地址**: `0x304`
    *   **属性**: **WARL**。软件完全控制，决定想要监听哪些中断。
*   **`mip` (Machine Interrupt Pending)**: 待处理中断。
    *   **地址**: `0x344`
    *   **属性**: 大部分位是 **Read-Only** 的硬件映射，仅个别位（MSIP）支持**WARL**。

#### 4.3.1 关键字段定义

`mip` 和 `mie` 共享相同的位布局，一一对应：

| 位域 | 名称 | 描述 | 读写行为 (`mip`) |
| :--- | :--- | :--- | :--- |
| **MEI(P/E)** (Bit 11) | Machine **External** Interrupt | 外部中断（键盘、网络）。来自 PLIC/CLINT。 | **只读** (反映外部连线电平) |
| **MTI(P/E)** (Bit 7) | Machine **Timer** Interrupt | 时钟中断。来自 Timer 模块。 | **只读** (反映时钟比较结果) |
| **MSI(P/E)** (Bit 3) | Machine **Software** Interrupt | 软件中断 | **读写** (软件可置1来触发中断) |

> 此处中断的 Bit 位置等于 mcause 值中的中断 ID。

#### 4.3.2 状态迁移协议

**A. 信号产生**
*   **硬件行为**: 当外设（e.g. Timer）满足条件时，硬件将 `mip` 对应的位置 1。
*   **软件行为**: 软件可以写入 `mip.MSIP` = 1 来手动触发软件中断。

**B. 中断受理判定**
详情见 `mstatus` 部分。多个中断同时受理时有如下优先级：MEI，MSI，MTI。

**C. 信号清除：软件的责任**
Handler 在处理完中断后，执行 `mret` 之前必须清除中断源，否则返回后会立即再次触发导致死循环。

*   **对于 Software Interrupt (MSIP)**:
    *   软件 **直接写入** `mip` 寄存器，将 Bit 3 清零 (`csrrc mip, mask`)。
*   **对于 Timer/External Interrupt (MTIP/MEIP)**:
    *   **不能**通过软件写 `mip` 清除，而必须**与外设交互**。（e.g. 软件写入时钟比较器设置下一个闹钟时间，外设硬件检测到条件不再满足将 `mip.MTIP` 信号线拉低）。

### 4.5 mtvec (Machine Trap-Vector Base-Address Register)

*   **地址**: `0x305`
*   **用途**: 指定 Trap 发生时 PC 跳转的目标地址（即 Trap Handler 的入口）。
   
#### 4.5.1 字段定义

| 位域 | 名称 | 描述 |
| :--- | :--- | :--- |
| **Base** (Bits 31:2) | Trap Vector Base Address | **基址**。存储 Handler 的高 30 位地址。<br>**约束**: 必须保证重组后的完整地址是 4 字节对齐的。 |
| **Mode** (Bits 1:0) | Vector Mode | **跳转模式**。决定如何计算最终 PC。 |

*   两个字段皆 **WARL**。

#### 4.5.2 模式与状态迁移逻辑

| Value | Name | Description |
| :---: | :--- | :--- |
| **0** | **Direct** | 所有的 Trap（异常 + 中断）都跳转到 `Base` 地址。 |
| **1** | **Vectored** | **异常 (Exceptions)**: 依然跳转到 `Base`。<br>**中断 (Interrupts)**: 跳转到 `Base + 4 * Cause` （Cause来自mcause寄存器）。 |

### 4.6 mcause (Machine Cause Register)

*   **地址**: `0x342`
*   **用途**: 报告 Trap 发生的具体原因。
*   **Fields (read-only 硬件决定)**:
    *   **Interrupt (Bit 31)**: `1` 表示中断（异步）；`0` 表示异常（同步）。
    *   **Exception Code (Bits 30:0)**: 表示具体的错误类型。

#### 标准异常列表与信号发生源 (Standard Exceptions Table)

下表列出了 M-Mode 必须处理的标准异常。**“信号发生源”** 指示了该异常通常在流水线的哪个阶段被检测到（这也决定了同一条指令导致异常处理的优先级）。当流水线多个阶段中多条指令报错时，从进入流水线时间早者开始处理。

| Code | 异常名称 | 描述 | 流水线阶段 |
| :---: | :--- | :--- | :--- |
| **0** | Instruction Address Misaligned | PC[1:0] != Bits(2)(0) | IF |
| **2** | Illegal Instruction | 指令非法（无法解读，权限不足，CSR非法等） | ID |
| **3** | Breakpoint | 执行 `ebreak` 指令 | EX |
| **4** | Load Address Misaligned | 读取数据的地址未对齐 | EX |
| **6** | Store/AMO Address Misaligned | 写入数据的地址未对齐 | EX |
| **8** | Environment Call from U-mode | U-mode 执行 `ecall` | EX |
| **11** | Environment Call from M-mode | M-mode 执行 `ecall` | EX |

> **注**: Code 1, 5, 7涉及内存读写权限，目前无需关注；Code 12, 13, 15 对应缺页异常 (Page Fault)，仅在实现 S-Mode 及虚拟内存后出现。

### 4.7 mepc (Machine Exception Program Counter)

*   **地址**: `0x341`
*   **用途**: 记录 Trap 发生时的 PC 值，作为 `mret` 返回的目标地址。
*   **访问属性**: **WARL**。

#### 状态转移协议

硬件根据 Trap 的类型（中断位是否为 1）决定写入什么值：

1.  **对于异常 (Exception)**: `mcause.Interrupt = 0`
    *   **写入值**: `mepc = Current_PC` (即导致报错的那条指令的地址)。
    *   **目的**: 异常通常意味着“指令执行失败”。处理完异常后（e.g. 修复了缺页）通常希望**重新执行**该指令。如果要跳过该指令需要软件修改 `mepc += 4`。

2.  **对于中断 (Interrupt)**: `mcause.Interrupt = 1`
    *   **写入值**: `mepc = Next_PC` (即 `Current_PC + 4` 或跳转目标)。
    *   **目的**: 中断发生时，当前指令已经成功**退休 (Retired)**。处理完中断后通常希望继续执行程序流中的**下一条**指令。

### 4.8 mtval (Machine Trap Value)

*   **地址**: `0x343`
*   **用途**: 提供除错误码 (`mcause`) 之外的辅助证据，帮助软件快速定位问题。
*   **访问属性**: **WARL**。

#### 状态转移协议

如果 Trap 发生，`mtval` **可以**被硬件自动填充为以下值（其余情况通常置 0）：

| Exception Code | `mtval` 写入内容 | 意义 |
| :---: | :--- | :--- |
| **0, 4, 6** | **Bad Address** | 导致错误的目标虚拟地址 |
| **1, 5, 7** | **Bad Address** | 导致错误的目标虚拟地址 |
| **2** | **Instruction Bits** | 非法指令机器码 |
| **3, 8, 11** | 0 | 不需要额外数据 |
| **Interrupts** | 0 | 中断通常不需要额外数据 |

### 4.9 mscratch (Machine Scratch Register)

*   **地址**: `0x340`
*   **用途**: **M-Mode 专用的临时寄存器**。（e.g. 在 Trap Handler 的最开始交换栈指针）与其他 CSR（如 `mstatus`, `mip`）不同，`mscratch` **没有任何硬件副作用**：其不控制任何逻辑，不产生任何信号。

### 所有未提及的 M-mode CSRs 与 Fields 全部设置为 read-only 0 即可。 

---

## 5. 指令集

### 5.1 Zicsr 扩展 (Control and Status Register Instructions)

Zicsr 扩展提供了 6 条基本指令，用于在 **通用寄存器 (GPR)** 和 **控制状态寄存器 (CSR)** 之间进行数据交换，可以在 U-mode 下使用。

#### 5.1.1 指令格式 (Instruction Format)

所有 Zicsr 指令均属于 **I-Type** 格式。

| Bits[31:20] | Bits[19:15] | Bits[14:12] | Bits[11:7] | Bits[6:0] |
| :---: | :---: | :---: | :---: | :---: |
| **csr addr** | **rs1** / **uimm** | **funct3** | **rd** | **opcode** |
| CSR 地址 | 源操作数 / 立即数 | 操作类型 | 目的寄存器 | `1110011` (SYSTEM) |

#### 5.1.2 寄存器操作指令 (Register-Register Operations)

##### A. CSRRW (Atomic Read/Write CSR)
*   **汇编**: `csrrw rd, csr, rs1`
*   **Funct3**: `001`
*   **行为**: 读取 CSR 旧值并写入 `rd`；将 `rs1` 的值写入 CSR。如果 `rd == x0`，则**不进行读取**（不产生读取的副作用）。这通常用于单纯的“写 CSR”。

##### B. CSRRS (Atomic Read and Set Bit)
*   **汇编**: `csrrs rd, csr, rs1`
*   **Funct3**: `010`
*   **行为**: 读取 CSR 旧值并写入 `rd`；将 `New_Val = Old_Val | rs1` 写入 CSR；如果 `rs1 == x0`，则**不进行 CSR 写入**也**不考虑写入 CSR 导致的异常**。

##### C. CSRRC (Atomic Read and Clear Bit)
*   **汇编**: `csrrc rd, csr, rs1`
*   **Funct3**: `011`
*   **行为**: 读取 CSR 旧值并写入 `rd`；将 `New_Val = Old_Val & (~rs1)` 写入 CSR；如果 `rs1 == x0`，不进行写入，同上。

#### 5.1.3 立即数操作指令 (Immediate-Register Operations)

这三条指令使用指令编码中的 **5位无符号立即数 (uimm)** 来更新 CSR，通常用于操作只需修改低几位的CSR。

##### D. CSRRWI (Atomic Read/Write Immediate)
*   **汇编**: `csrrwi rd, csr, uimm`
*   **Funct3**: `101`
*   **行为**: 读取 CSR 旧值并写入 `rd`；将 `uimm` (零扩展到 XLEN 位) 写入 CSR；如果 `rd == x0`，则不进行读取。

##### E. CSRRSI (Atomic Read and Set Immediate)
*   **汇编**: `csrrsi rd, csr, uimm`
*   **Funct3**: `110`
*   **行为**: 读取 CSR 旧值并写入 `rd`；将 `New_Val = Old_Val | uimm` 写入CSR；如果 `uimm == 0`，则不进行写入。

##### F. CSRRCI (Atomic Read and Clear Immediate)
*   **汇编**: `csrrci rd, csr, uimm`
*   **Funct3**: `111`
*   **行为**: 读取 CSR 旧值并写入 `rd`；将 `New_Val = Old_Val & (~uimm)` 写入 CSR；如果 `uimm == 0`，则不进行写入。

### 5.2 ECALL & EBREAK

两条指令在执行期间**主动触发异常**，将控制权移交给 M-Mode Handler。它们属于基础指令集 (RV32I)，**所有权限模式 (U/M)**均可执行。

#### 5.2.1 ECALL (Environment Call)
*   **汇编**: `ecall`
*   **编码**: `0x00000073` (funct12=0, rd=0, rs1=0, opcode=SYSTEM)
*   **行为**: 指令执行立即终止；硬件触发异常，根据 `mtvec` 跳转； 需注意 `mcause` 的值取决于执行指令时的**权限等级**。

#### 5.2.2 EBREAK (Environment Break)
*   **汇编**: `ebreak`
*   **编码**: `0x00100073` (funct12=1, rd=0, rs1=0, opcode=SYSTEM)
*   **行为**: 指令执行立即终止；硬件触发异常，跳转；`mcause` 固定为**3**。

### 5.3 M-Mode 专用指令

#### 5.3.1 MRET
*   **汇编**: `mret`
*   **编码**: `0x30200073` (funct12=0x302, rd=0, rs1=0, opcode=SYSTEM)
*   **用途**: **从 Trap 中返回**。将控制权从 M-Mode Handler 移交回 `mepc` 指向的地址，并恢复之前的特权级和中断状态（详情见mstatus部分）。

#### 5.3.2 WFI
*   **汇编**: `wfi`
*   **编码**: `0x10500073` (funct12=0x105, SYSTEM)
*   **行为**: 可以视作 `NOP` 。

---

## 6. 总结：Trap 处理工作流 (Workflow of the Trap-Handler Sys)

### 6.1 背景状态

在 Trap 发生前，CPU 应处于以下稳定状态：

1.  **静态配置**: `misa` 已被硬连线，标识了 CPU 能力。
2.  **动态配置** (由 Bootloader/OS 完成):
    *   `mtvec`: 已指向正确的 Handler 入口，且 Mode 字段合法。
    *   `mie`: 软件已根据需要开启了特定中断的掩码（如开启时钟中断）。
    *   `mstatus`:
        *   `MIE=1` (全局中断开启)。
        *   `MPP=U`，`MPIE=1` 。
3.  **运行状态**:
    *   `mip`: 初始为 0（无中断挂起）。
    *   `Current_Mode`: **U-Mode**。

### 6.2 事件发生与受理

事件分为同步的异常与异步的中断，其生成与受理逻辑不同。

#### 6.2.1 异常 (Exceptions) - 同步
*   **触发时机**: 在指令执行的各个流水线阶段（IF, ID, EX, MEM）产生，但是 CPU 会暂停流水线直到**之前的所有指令**都退休后再处理该异常，否则 handle 过程可能受到旧指令影响。
*   **受理条件**: 总是受理。

#### 6.2.2 中断 (Interrupts) - 异步
*   **触发时机**: 外部信号随时可能拉高 `mip` 的对应位，但 CPU 仅在 **指令退休边界**进行采样和响应。
*   **受理条件**: mip 置位，mie 允许，符合 mstatus 提出的受理条件。

### 6.3 状态迁移

当 Trap 确定受理（使能信号拉高）时，在**同一个时钟周期内**，硬件**原子且并行**地执行以下状态更新：

1.  **更新 `mepc` (保存PC)**:
    *   **Exception**: 写入 **当前指令 PC**。
    *   **Interrupt**: 写入 **下一条指令 PC**。
2.  **更新 `mcause` (记录原因)**:
    *   Bit 31 = `1` (Interrupt) / `0` (Exception)。
    *   Bits 30:0 = Trap ID。
3.  **更新 `mtval` (补充信息)**:
    *   根据约定写入出错的内存地址（访存/对齐异常）或指令编码（非法指令）等。其他情况置 0。
4.  **更新 `mstatus`(状态保存)**:
    *   `MPIE` $\leftarrow$ `MIE` 
    *   `MPP` $\leftarrow$ `Current_Mode` 
    *   `MIE` $\leftarrow$ `0` （**关中断**，进入临界区）
5.  **提权**:
    *   `Current_Mode` $\leftarrow$ `Machine (M-Mode)`
6.  **跳转**:
    *   `PC` $\leftarrow$ `mtvec` （根据 Mode 计算目标地址）

> 实现时除了CSR需要更新，整个流水线也需要 Flush 成空流水线（引发 Trap 的指令总是在 WB 阶段，因此只需向除 WB 尾部级间寄存器外所有级间寄存器注入气泡即可）

### 6.4 软件接管阶段

一旦硬件完成了 Trap Entry 的状态迁移并跳转至 `mtvec`，硬件的特殊职责暂时结束，退化为标准的指令执行机器。此时由软件（Trap Handler）接管控制权。

1.  **硬件职责**:
    *   提供当前的 PC (指向 Handler 入口)。
    *   提供 CSRs 的静态值 (`mcause` 告知原因, `mtval` 提供补充信息, `mscratch` 辅助上下文保存)。
    *   除非发生新的异常或不可屏蔽事件，硬件不再自动操作 CSR。

2.  **二重 Trap 风险**:
    *   由于 M-Mode 只有一套 CSR 用于保存现场，若 Handler 代码执行过程中再次触发 Trap 则 **`mepc` 和 `mstatus` 将被新 Trap 覆盖**，无法处理因此 CPU 崩溃。

### 6.5 Trap 返回

`mret` 是 Trap 流程的终点，它是一条**改变控制流**和**特权状态**的指令。

#### 6.5.1 执行时机
为了遵循精确异常模型，`mret` 的状态更新必须发生在 **WB** 阶段，必须确保 `mret` 之前的所有指令都已安全退休，且 `mret` 自身没有触发异常。

#### 6.5.2 状态迁移逻辑
在 mret 成功 Retire 后，硬件执行 Trap Entry 的逆过程：

1.  **恢复 PC (Control Flow)**: `PC = mepc`；触发 **Pipeline Flush**，清除流水线中所有指令，下一周期从 `mepc` 处重新开始取指。
2.  **恢复特权级 (Privilege Mode)**: `Current_Mode = mstatus.MPP`。
3.  **恢复中断使能 (Interrupt Enable)**: `mstatus.MIE = mstatus.MPIE`。
4.  **重置备份字段 (Reset Fields)**: `mstatus.MPIE = 1`； `mstatus.MPP = U`。

#### 6.5.3 下一个周期
*   **状态**: CPU 处于 `mstatus.MPP` 指定的权限级。
*   **取指**: 从 `mepc` 指向的地址开始 Fetch。
*   **中断检查**: `mstatus.MIE` 已恢复，若 `mip` 中仍有挂起信号且满足条件，可能会在第一条用户指令执行完后再次触发 Trap。
*   **总之，与事件发生前状态保持一致。**
