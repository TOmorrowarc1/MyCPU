from assassyn.frontend import Bits, Record

# 1. 基础物理常量
# 指令 Opcode (7-bit)
OP_R_TYPE   = Bits(7)(0b0110011) # ADD, SUB...
OP_I_TYPE   = Bits(7)(0b0010011) # ADDI...
OP_LOAD     = Bits(7)(0b0000011) # LB, LW...
OP_STORE    = Bits(7)(0b0100011) # SB, SW...
OP_BRANCH   = Bits(7)(0b1100011) # BEQ...
OP_JAL      = Bits(7)(0b1101111)
OP_JALR     = Bits(7)(0b1100111)
OP_LUI      = Bits(7)(0b0110111)
OP_AUIPC    = Bits(7)(0b0010111)
OP_SYSTEM   = Bits(7)(0b1110011) # ECALL, EBREAK

# 立即数类型 (用于生成器选择切片逻辑)
class ImmType:
    R = 0 # 无立即数
    I = 1
    S = 2
    B = 3
    U = 4
    J = 5

# 2. 执行阶段控制信号 (EX Control)
# ALU 功能码 (One-hot 映射, 假设 Bits(16))
# 顺序对应 alu_func[i]
class ALUOp:
    ADD  = 0
    SUB  = 1
    SLL  = 2
    SLT  = 3
    SLTU = 4
    XOR  = 5
    SRL  = 6
    SRA  = 7
    OR   = 8
    AND  = 9
    # 占位/直通/特殊用途
    NOP    = 15

class Rs1Sel:
    RS1        = 0
    EX_MEM_BYPASS = 1
    MEM_WB_BYPASS = 2

class Rs2Sel:
    RS2 = 0
    EX_MEM_BYPASS = 1
    MEM_WB_BYPASS = 2

# 操作数 1 选择 (One-hot, Bits(5))
# 对应: real_rs1, pc, 0
class Op1Sel:
    RS1  = 0
    PC   = 1
    ZERO = 2

# 操作数 2 选择 (One-hot, Bits(5))
# 对应: real_rs2, imm, 4
class Op2Sel:
    RS2  = 0
    IMM  = 1
    CONST_4 = 2
    EX_MEM_BYPASS = 3
    MEM_WB_BYPASS = 4

# 3. 访存与写回控制信号 (MEM/WB Control)

# 访存操作 (Bits(3))
class MemOp:
    NONE  = 0
    LOAD  = 1
    STORE = 2

# 访存宽度 (Bits(3))
class MemWidth:
    BYTE = 0
    HALF = 1
    WORD = 2

# 符号扩展 (Bits(1))
class MemSign:
    SIGNED   = 0
    UNSIGNED = 1

# 写回使能 (隐式：通过将 RD 设为 0 来禁用写回，这里仅作逻辑标记)
class WB:
    YES = 1
    NO  = 0

# Rs 使用标志 (用于判断是否使用 Rs 寄存器，防止虚假冒险)
class RsUse:
    NO  = 0  # 不使用
    YES = 1  # 使用

# 4. 控制信号结构定义

# 写回域 (WbCtrl)
# Record至少需要包含两个字段，因此 `rd_addr` 不定义为 `Record`
rd_addr    = Bits(5)       # 目标寄存器索引，如果是0拒绝写入。

# 访存域 (MemCtrl)
mem_ctrl_signals = Record(
    mem_opcode   = Bits(3), # 内存操作，独热码 (0:None, 1:Load, 2:Store)
    mem_width    = Bits(3), # 访问宽度，独热码 (0:Byte, 1:Half, 2:Word)
    mem_unsigned = Bits(1), # 是否无符号扩展 (LBU/LHU)
    rd_addr = Bits(5)       # 【嵌套】携带 WB 级信号
)

# 执行域 (ExCtrl)
ex_ctrl_signals = Record(
    alu_func = Bits(16),   # ALU 功能码 (独热码)
    rs1_sel  = Bits(3),    # rs1结果来源，独热码 (0:RS1, 1:EX_MEM_Fwd, 2: MEM_WB_Fwd)
    rs2_sel  = Bits(3),    # rs2结果来源，独热码 (0:RS1, 1:EX_MEM_Fwd, 2: MEM_WB_Fwd)
    op1_sel  = Bits(3),    # 操作数1来源，独热码 (0:RS1, 1:PC, 2: Constant_0)
    op2_sel  = Bits(3),    # 操作数2来源，独热码 (0:RS2, 1:imm, 2: Constant_4)
    is_branch = Bits(1),    # 是否跳转 (Branch 指令)
    is_jtype = Bits(1),     # 是否直接跳转 (JAL/JALR 指令)
    is_jalr  = Bits(1),     # 是否是 JALR 指令
    next_pc_addr = Bits(32),  # 预测结果：下一条指令的地址
    mem_ctrl = mem_ctrl_signals  # 【嵌套】携带 MEM 级信号
)