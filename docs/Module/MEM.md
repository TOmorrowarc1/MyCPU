# RV32I MEM (MemoryAccess) 模块设计文档

> **依赖**：Assassyn Framework, `control_signals.py`

## 1. 模块概述
该模块存在两部分：作为流水线的访存响应阶段的 **MemoryAccess** 与作为冯诺依曼架构内存，仲裁并受理 IF 与 MEM L/S请求的 **SingleMemory**。

### 1.1 MemoryAccess 模块功能
由于针对 **SingleMemory** 的读/写请求已在 EX 阶段发出，MEM 阶段的职责如下：
1.  **数据接收**：从 **SingleMemory** 寄存器端口读取原始数据。
2.  **数据整形**：根据地址低位和指令类型（LB/LH/LW/LBU/LHU），对数据进行移位、截断和符号扩展。
3.  **路由选择**：在“加工后的内存数据”和“EX 阶段传来的 ALU 结果”之间进行选择。
4.  **分发**：将最终结果同时发送给 **WB 模块** 和 **Bypass 网络**。
  
### 1.2 SingleMemory 模块功能
该模块模拟一个简单的单端口 SRAM，支持字节寻址的读写操作。其职责如下：
1. **请求仲裁**：接受来自 IF 或 EX 的读/写请求将结果分别返回至 ID 与 MEM，优先处理 EX 的请求，对于未完成的请求返回 Bits(32)(0)。
2. **数据存储与读取**：SRAM 自带读写细度为 WORD，因此虽然按字节读可以依靠稍后裁剪完成，但是按字节写需要先读取原值，再移位剪切拼接，最后写入新值。因此读使用一个周期，写需要两个周期。

## 2. MemoryAccess 模块接口定义

### 2.1 端口定义 (`__init__`)

接收来自 EX 阶段的控制信号包以及两条数据通道。

``` python
class MemoryAccess(Module):
    def __init__(self):
        super().__init__(
            ports={
                # 1. 控制通道：包含 mem_op, mem_width, mem_unsigned, wb_ctrl
                'ctrl': Port(mem_ctrl_signals),

                # 2. 统一数据通道：
                # - Load/Store 指令：SRAM 地址 (用于切割数据)
                # - ALU 指令：计算结果
                # - JAL/JALR 指令：PC+4 (由 EX 级 Mux 进来)
                'alu_result': Port(Bits(32)) 
            }
        )
        self.name = 'MEMAccess'
```

### 2.2 构建函数 (`build`)

参数如下：

```python
@module.combinational
def build(self, 
          wb_module: Module,      # 下一级流水线 (writeback.py)
          sram_dout: Array,       # SRAM 的输出端口 (Ref)
          mem_bypass_reg: Array   # 全局 Bypass 寄存器 (数据)
          ):
    # 实现见下文
    pass
```

内部实现：

#### 2.2.1 获取输入与拆包

```python
    # 弹出所有输入端口
    ctrl, alu_result = self.pop_all_ports(False)
    
    # 提取需要的控制信号
    mem_opcode = ctrl.mem_opcode
    mem_width = ctrl.mem_width
    mem_unsigned = ctrl.mem_unsigned
```

#### 2.2.2 SRAM 数据加工 (Data Aligner)

需要根据地址的低 2 位 (`alu_result[1:0]`) 从 32 位字中切出正确的字节。

```python
    # 1. 读取 SRAM 原始数据 (32-bit)
    raw_mem = sram_dout[0].bitcast(Bits(32))
    
    # 2. 二分选择半字 (16-bit Candidates)
    # 根据 alu_result[1:1] (地址第1位) 选择高16位还是低16位
    # 0 -> 低16位 [15:0]
    # 1 -> 高16位 [31:16]
    half_selected = alu_result[1:1].select(raw_mem[16:32], raw_mem[0:16])

    # 3. 二分选择字节 (8-bit Candidates)
    # 在刚才选出的半字基础上，根据 alu_result[0:0] (地址第0位) 选择高8位还是低8位
    # 0 -> 低8位
    # 1 -> 高8位
    byte_selected = alu_result[0:0].select(half_selected[8:16], half_selected[0:8])

    # 此时我们有了三个维度的候选者：
    # A. byte_selected: 无论地址是多少，这里都是你要的那个字节 (8-bit)
    # B. half_selected: 无论地址是多少，这里都是你要的那个半字 (16-bit)
    # C. raw_mem:       原始字 (32-bit)

    # 4. 统一处理符号位
    # 技巧：无论是有符号还是无符号，先算出 "填充位 (Padding Bit)" 是 0 还是 1
    
    # 对于 Byte：如果是无符号，填充0；否则填充最高位(第7位)
    pad_bit_8 = mem_unsigned.select(Bits(1)(0), byte_selected[7:7])
    # 生成 24 位的填充掩码 (全0 或 全1)
    padding_8 = pad_bit_8.select(Bits(24)(0xffffff), Bits(24)(0))
    # 拼接
    byte_extended = concat(padding_8, byte_selected)

    # 对于 Half：如果是无符号，填充0；否则填充最高位(第15位)
    pad_bit_16 = mem_unsigned.select(Bits(1)(0), half_selected[15:15])
    # 生成 16 位的填充掩码
    padding_16 = pad_bit_16.select(Bits(16)(0xffff), Bits(16)(0))
    # 拼接
    half_extended = concat(padding_16, half_selected)

    # 5. 根据位宽指令选择最终结果
    # 使用 mem_width 作为选择信号 (独热码)
    processed_mem_result = mem_width.select1hot(
        byte_extended,  # 对应 is_byte 
        half_extended,  # 对应 is_half
        raw_mem         # 对应 is_word
    )
```

#### 2.2.3 最终数据选择 (Final Mux)

决定传递给 WB 的数据来自内存读取抑或 ALU 计算。

```python
    # 如果是 Load 指令，用加工后的内存数据
    # 否则 (ALU运算/JAL/LUI)，用 EX 传下来的 alu_result
    is_load = ctrl.mem_opcode == MemOpcode.LOAD
    is_store = ctrl.mem_opcode == MemOpcode.STORE
    final_data = is_load.select(processed_mem_result, alu_result)
```

#### 2.2.4 输出驱动 (Output Driver)

同时将结果存入旁路寄存器和级间寄存器。

```python
    # 1. 驱动全局 Bypass 寄存器 (Side Channel)
    # 这使得下下条指令能在当前周期看到结果
    # 注意：如果当前是气泡 (rd=0)，写入 0 也是安全的
    mem_bypass_reg[0] = final_data

    # 2. 驱动下一级 WB
    # 剥离外层 mem_ctrl，只传 wb_ctrl
    wb_call = wb_module.async_called(
        ctrl = ctrl.rd_addr,
        wdata = final_data
    )
    
    # 设置 FIFO 深度为 1 (刚性流水线特征)
    wb_call.bind.set_fifo_depth(ctrl=1, wdata=1)

    # 3. 状态暴露
    # 将关键控制信息返回，供 HazardUnit 使用
    return ctrl, is_store
```

## 3. SingleMemory 模块接口定义

### 3.1 端口定义 (`__init__`)

SingleMemory 需要同时接收来自 **IF** 和 **EX** 的信号。

```python
class SingleMemory(DownStream):
    def __init__(self):
        super().__init__()
        self.name = 'SingleMEM'
```

### 3.2 构建函数 (`build`)

该部件通过 IPO 抽象可得逻辑如下：

输出为 SRAM 的读使能，地址，写使能，写数据和 status regs ——状态指示寄存器 Bits(1), 地址寄存器 Bits(32), 长度独热码寄存器 Bits(3), wdata 寄存器 Bits(32)。

输入为 EX 的 L/S 请求信号各 Bits(1), 地址 Bits(32), 长度 Bits(3), wdata Bits(32) 与 IF 的地址 Bits(32)，来自上一周期的 status regs 与 SRAM 输出。

设状态指示寄存器 0 为无写请求；1为将处理读取后的拼接与写入。

读使能：~ status

写使能：status

地址：状态指示寄存器为 0 且 EX L/S 请求存在为 1 时取 EX 地址；状态指示寄存器为 0 且 EX L/S 请求全部为 0 时取 IF 地址；状态指示寄存器为 1 时取保存的地址寄存器中值。

写数据：状态指示寄存器为 1 时取移位拼接结果；其他情况取全 0。

状态指示寄存器：上一周期为 0 且 EX S 请求存在时置 1；其他情况置 0。

地址寄存器：上一周期为 0 且 EX S 请求存在时取 EX 地址；其他情况取全 0。

长度独热码寄存器：上一周期为 0 且 EX S 请求存在时取 EX 长度；其他情况取全 0。

写数据寄存器：上一周期为 0 且 EX S 请求存在时取 EX 写数据；其他情况取全 0。

```python
@downstream.combinational
def build(
    self, 
    # --- 来自 IF 阶段的接口 ---
    if_addr: Value,      # 取指地址 (PC)

    # --- 来自 EX 阶段的接口 (优先) ---
    mem_addr: Value,   # 访存地址 (ALU Result)
    re: Value,           # 读使能 (Load)
    we: Value,           # 写使能 (Store)
    wdata: Value,       # 写数据 (Store Value)
    width: Value,       # 访存宽度 (Byte/Half/Word)     
    sram: SRAM,         # 物理 SRAM 资源引用
    ):

    # 0. 使用 optional 弹出端口
    if_addr_val=if_addr.optional(Bits(16)(0))
    mem_addr_val=mem_addr.optional(Bits(16)(0))
    re_val=re.optional(Bits(1)(0))
    we_val=we.optional(Bits(1)(0))
    wdata_val=wdata.optional(Bits(32)(0))
    width_val=width.optional(Bits(3)(1))

    # 1. 定义状态寄存器
    # 0: IDLE/READ Phase; 1: WRITE Phase
    store_state = RegArray(Bits(1), 1, initializer=[0])
    # 定义锁存器，用于跨周期传递 Store 信息)
    store_addr = RegArray(Bits(32), 1)
    store_data = RegArray(Bits(32), 1)
    store_width = RegArray(Bits(3), 1)

    # 2. 状态迁移逻辑
    # store_state 更新
    store_reg_refresh = we_val & ~store_state[0]
    store_state[0] <= store_reg_refresh.select(Bits(1)(1), Bits(1)(0))
    # 地址寄存器更新
    store_addr[0] <= store_reg_refresh.select(mem_addr_val, Bits(32)(0))
    # 长度独热码寄存器更新
    store_width[0] <= store_reg_refresh.select(width_val, Bits(3)(1))
    # 写数据寄存器更新
    store_data[0] <= store_reg_refresh.select(wdata_val, Bits(32)(0))

    # 3. SRAM 输入计算
    # 读使能/写使能确定
    SRAM_we = store_state[0]
    SRAM_re = ~store_state[0]
    # 地址计算与仲裁
    final_mem_addr = state[0].select(store_addr[0], mem_addr_val)
    ex_request = we_val | re_val | store_state[0]
    SRAM_addr = ex_request.select(final_mem_addr, if_addr_val)

    # 写数据计算
    final_wdata = state[0].select(store_data[0], Bits(32)(0))
    final_width = store_width[0]
    # 计算位偏移 (addr[1:0] * 8)   
    shamt = final_mem_addr[1:0].concat(Bits(3)(0))
    # 生成基础掩码 (000000FF, 0000FFFF, FFFFFFFF)
    raw_mask = mem_wid.select1hot(
        Bits(32)(0xFFFFFFFF), # Word
        Bits(32)(0x0000FFFF), # Half
        Bits(32)(0x000000FF), # Byte
    )    
    # 移位到目标位置
    shifted_mask = raw_mask << shamt
    shifted_data = final_wdata << shamt
    # 利用掩码进行拼接，得到结果
    SRAM_wdata = (sram.dout[0] & (~shifted_mask)) | (shifted_data & shifted_mask)

    # 4. 驱动 SRAM 端口
    sram.build(
        addr=SRAM_addr[0:15],
        re=SRAM_re,
        we=SRAM_we,
        wdata=SRAM_wdata,
    )
```