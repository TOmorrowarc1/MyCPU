from assassyn.frontend import Bits, Record

# 1. 基础物理常量
# 指令 Opcode (7-bit)
OP_R_TYPE = Bits(7)(0b0110011)  # ADD, SUB...
OP_I_TYPE = Bits(7)(0b0010011)  # ADDI...
OP_LOAD = Bits(7)(0b0000011)  # LB, LW...
OP_STORE = Bits(7)(0b0100011)  # SB, SW...
OP_BRANCH = Bits(7)(0b1100011)  # BEQ...
OP_JAL = Bits(7)(0b1101111)
OP_JALR = Bits(7)(0b1100111)
OP_LUI = Bits(7)(0b0110111)
OP_AUIPC = Bits(7)(0b0010111)
OP_SYSTEM = Bits(7)(0b1110011)  # ECALL, EBREAK, Ziscr


# 立即数类型 (用于生成器选择切片逻辑)
class ImmType:
    R = Bits(7)(0b0000001)  # 无立即数
    I = Bits(7)(0b0000010)
    S = Bits(7)(0b0000100)
    B = Bits(7)(0b0001000)
    U = Bits(7)(0b0010000)
    J = Bits(7)(0b0100000)
    Z = Bits(7)(0b1000000)  # 用于 CSR 指令的 zimm


# 2. 执行阶段控制信号 (EX Control)
# ALU 功能码 (One-hot 映射, 假设 Bits(16))
# 顺序对应 alu_func[i]
class ALUOp:
    ADD = Bits(16)(0b0000000000000001)
    SUB = Bits(16)(0b0000000000000010)
    SLL = Bits(16)(0b0000000000000100)
    SLT = Bits(16)(0b0000000000001000)
    SLTU = Bits(16)(0b0000000000010000)
    XOR = Bits(16)(0b0000000000100000)
    SRL = Bits(16)(0b0000000001000000)
    SRA = Bits(16)(0b0000000010000000)
    OR = Bits(16)(0b0000000100000000)
    AND = Bits(16)(0b0000001000000000)
    SYS = Bits(16)(0b0000010000000000)
    # 占位/直通/特殊用途
    NOP = Bits(16)(0b1000000000000000)


class BranchType:
    NO_BRANCH = Bits(16)(0b0000000000000001)
    BEQ = Bits(16)(0b0000000000000010)
    BNE = Bits(16)(0b0000000000000100)
    BLT = Bits(16)(0b0000000000001000)
    BGE = Bits(16)(0b0000000000010000)
    BLTU = Bits(16)(0b0000000000100000)
    BGEU = Bits(16)(0b0000000001000000)
    JAL = Bits(16)(0b0000000010000000)
    JALR = Bits(16)(0b0000000100000000)


class Rs1Sel:
    RS1 = Bits(4)(0b0001)
    EX_BYPASS = Bits(4)(0b0010)
    MEM_BYPASS = Bits(4)(0b0100)
    WB_BYPASS = Bits(4)(0b1000)


class Rs2Sel:
    RS2 = Bits(4)(0b0001)
    EX_BYPASS = Bits(4)(0b0010)
    MEM_BYPASS = Bits(4)(0b0100)
    WB_BYPASS = Bits(4)(0b1000)


# 操作数 1 选择 (One-hot, Bits(3))
# 对应: real_rs1, pc, 0
class Op1Sel:
    RS1 = Bits(3)(0b001)
    PC = Bits(3)(0b010)
    ZERO = Bits(3)(0b100)


# 操作数 2 选择 (One-hot, Bits(3))
# 对应: real_rs2, imm, 4
class Op2Sel:
    RS2 = Bits(3)(0b001)
    IMM = Bits(3)(0b010)
    CONST_4 = Bits(3)(0b100)


# 3. 访存阶段控制信号(MEM Control)
# 访存操作 (One-hot, Bits(3))
class MemOp:
    NONE = Bits(3)(0b001)
    LOAD = Bits(3)(0b010)
    STORE = Bits(3)(0b100)


# 访存宽度 (One-hot, Bits(3))
class MemWidth:
    BYTE = Bits(3)(0b001)
    HALF = Bits(3)(0b010)
    WORD = Bits(3)(0b100)


# 符号扩展 (Bits(1))
class MemSign:
    SIGNED = Bits(1)(0b0)
    UNSIGNED = Bits(1)(0b1)

# 4. 写回阶段控制信号(WB Control)
class WB:
    ENABLE = Bits(1)(0b1)
    DISABLE = Bits(1)(0b0)

# Privileged 指令相关控制信号
# Exception_Code 常量(Bits(32))
EXC_INST_ADDR_MISALIGNED = Bits(32)(0x00000000)
EXC_ILLEGAL_INST = Bits(32)(0x00000002)
EXC_EBREAK = Bits(32)(0x00000003)
EXC_LOAD_ADDR_MISALIGNED = Bits(32)(0x00000004)
EXC_STORE_ADDR_MISALIGNED = Bits(32)(0x00000006)
EXC_ECALL_UMODE = Bits(32)(0x00000008)
EXC_ECALL_MMODE = Bits(32)(0x0000000B)

# Interrupt_Code 常量(Bits(32))
INT_MSI = Bits(32)(0x00000003)  # Machine Software Interrupt (Bit 3)
INT_MTI = Bits(32)(0x00000007)  # Machine Timer Interrupt (Bit 7)
INT_MEI = Bits(32)(0x0000000B)  # Machine External Interrupt (Bit 11)

# CSR ALU 操作选择 (One-hot, Bits(3))
class CSRALUOp:
    CSR_RW = Bits(3)(0b001)  # 读写: rs1
    CSR_RS = Bits(3)(0b010)  # 读置位: rd | rs1
    CSR_RC = Bits(3)(0b100)  # 读清除: rd & (~rs1)
    
# CSR 操作数来源 (Bits(1))
class CSROpSel:
    RS1 = Bits(1)(0b0)  # 来自 rs1
    IMM = Bits(1)(0b1)  # 来自 指令立即数 (zimm)
        
# CSR 读取结果来源选择 (One-hot, Bits(4))
class CSRReadSel:
    CSR = Bits(4)(0b0001)          # 来自 CSR 读取结果
    CSR_EX_BYPASS = Bits(4)(0b0010)  # 来自 EX 阶段 CSR 结果旁路
    CSR_MEM_BYPASS = Bits(4)(0b0100) # 来自 MEM 阶段 CSR 结果旁路
    CSR_WB_BYPASS = Bits(4)(0b1000)  # 来自 WB 阶段 CSR 结果旁路
   
# CSR 读使能 (Bits(1))
class CSRRe:
    ENABLE = Bits(1)(0b1)
    DISABLE = Bits(1)(0b0)
    
# CSR 写使能 (Bits(1))
class CSRWe:
    ENABLE = Bits(1)(0b1)
    DISABLE = Bits(1)(0b0)
    
    
# 4. 控制信号结构定义
# 写回域 (WB Ctrl)
wb_ctrl_signals = Record(
    # Unprivileged ISA
    rd_addr=Bits(5),  # 目标寄存器索引，如果是0拒绝写入。
    halt_if=Bits(1),  # 是否触发仿真终止 (sb x0, (-1)x0)
    # Privileged ISA
    is_MRET=Bits(1),  # 是否为 MRET 指令
    Exception_Valid=Bits(1),  # 异常代码有效标志
    Exception_Code=Bits(32),  # 异常代码 (值见上方定义)
    Exception_Val=Bits(32),  # 异常相关值 (如：faulting address)
    PC=Bits(32),  # 当前指令的 PC (用于异常处理)
    csr_waddr=Bits(12),  # CSR 寄存器地址 (12-bit)
)

# 访存域 (MEM Ctrl)
mem_ctrl_signals = Record(
    mem_opcode=Bits(3),  # 内存操作，独热码 (0:None, 1:Load, 2:Store)
    mem_width=Bits(3),  # 访问宽度，独热码 (0:Byte, 1:Half, 2:Word)
    mem_unsigned=Bits(1),  # 是否无符号扩展 (LBU/LHU)
    wb_ctrl=wb_ctrl_signals,  # 【嵌套】携带 WB 级信号
)

# 执行域 (EX Ctrl)
ex_ctrl_signals = Record(
    # ALU 功能码，使用 Bits(16) 静态定义 (ADD:Bits(16)(0b0000000000000001), SUB:Bits(16)(0b0000000000000010), ...)
    alu_func=Bits(16),
    # rs1结果来源，使用 Bits(4) 静态定义 (RS1:Bits(4)(0b0001), EX_BYPASS:Bits(4)(0b0010), MEM_BYPASS:Bits(4)(0b0100), WB_BYPASS: Bits(4)(0b1000))
    rs1_sel=Bits(4),
    # rs2结果来源，使用 Bits(4) 静态定义 (RS2:Bits(4)(0b0001), EX_BYPASS:Bits(4)(0b0010), MEM_BYPASS:Bits(4)(0b0100), WB_BYPASS:Bits(4)(0b1000))
    rs2_sel=Bits(4),
    # CSR 结果来源，使用 Bits(4) 静态定义 (CSR:Bits(4)(0b0001), CSR_EX_BYPASS:Bits(4)(0b0010), CSR_MEM_BYPASS:Bits(4)(0b0100), CSR_WB_BYPASS:Bits(4)(0b1000))
    csr_sel=Bits(4),
    # 操作数1来源，使用 Bits(3) 静态定义 (RS1:Bits(3)(0b001), PC:Bits(3)(0b010), ZERO:Bits(3)(0b100))
    op1_sel=Bits(3),
    # 操作数2来源，使用 Bits(3) 静态定义 (RS2:Bits(3)(0b001), IMM:Bits(3)(0b010), CONST_4:Bits(3)(0b100))
    op2_sel=Bits(3),
    # CSR 操作数来源，使用 Bits(1) 静态定义 (RS1:Bits(1)(0b0), IMM:Bits(1)(0b1))
    csr_op_sel=Bits(1),
    csr_alu_func=Bits(3),  # CSR ALU 操作选择，使用 Bits(3) 静态定义 (CSR_RW:Bits(3)(0b001), CSR_RS:Bits(3)(0b010), CSR_RC:Bits(3)(0b100))  
    branch_type=Bits(16),  # Branch 指令功能码，使用 Bits(16) 静态定义
    next_pc_addr=Bits(32),  # 预测结果：下一条指令的地址
    mem_ctrl=mem_ctrl_signals,  # 【嵌套】携带 MEM 级信号
)

pre_decode_t = Record(
    # 原始控制信号
    alu_func=Bits(16),
    alu_result_sel=Bits(1),
    csr_alu_op=Bits(3),
    op1_sel=Bits(3),
    op2_sel=Bits(3),
    branch_type=Bits(16),  # Branch 指令功能码
    next_pc_addr=Bits(32),  # IF 预测结果
    # 嵌套的后续阶段控制
    mem_ctrl=mem_ctrl_signals,
    # 原始数据需求
    rs1_data=Bits(32),
    rs2_data=Bits(32),
    csr_data=Bits(32),
    imm=Bits(32),
)

id_ctrl_signals = Record(
    # 预解码信号
    PC=Bits(32),  # 当前指令的 PC
    Exception_Valid=Bits(1),  # 异常代码有效标志
    Exception_Code=Bits(32),  # 异常代码 (值见上方定义)
    Exception_Val=Bits(32),  # 异常相关值 (如：faulting address)
    stall_if = Bits(1), # 是否暂停取指
)
