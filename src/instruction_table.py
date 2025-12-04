from control_signals import *

# RV32I 指令真值表
# 表格列定义:
# Key, Opcode, Funct3, Bit30, ImmType | ALU_Func, Rs1_use, Rs2_use, Op1, Op2, Mem_Op, Width, Sign, WB, Branch, Jump, Jalr

rv32i_table = [
    
    # --- R-Type ---
    ('add',    OP_R_TYPE, 0x0,  0,    ImmType.R, ALUOp.ADD, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('sub',    OP_R_TYPE, 0x0,  1,    ImmType.R, ALUOp.SUB, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('sll',    OP_R_TYPE, 0x1,  0,    ImmType.R, ALUOp.SLL, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('slt',    OP_R_TYPE, 0x2,  0,    ImmType.R, ALUOp.SLT, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('sltu',   OP_R_TYPE, 0x3,  0,    ImmType.R, ALUOp.SLTU, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('xor',    OP_R_TYPE, 0x4,  0,    ImmType.R, ALUOp.XOR, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('srl',    OP_R_TYPE, 0x5,  0,    ImmType.R, ALUOp.SRL, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('sra',    OP_R_TYPE, 0x5,  1,    ImmType.R, ALUOp.SRA, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('or',     OP_R_TYPE, 0x6,  0,    ImmType.R, ALUOp.OR,  RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('and',    OP_R_TYPE, 0x7,  0,    ImmType.R, ALUOp.AND, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),

    # --- I-Type (ALU) ---
    ('addi',   OP_I_TYPE, 0x0,  None, ImmType.I, ALUOp.ADD, RsUse.YES, RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('slti',   OP_I_TYPE, 0x2,  None, ImmType.I, ALUOp.SLT, RsUse.YES, RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('sltiu',  OP_I_TYPE, 0x3,  None, ImmType.I, ALUOp.SLTU, RsUse.YES, RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('xori',   OP_I_TYPE, 0x4,  None, ImmType.I, ALUOp.XOR, RsUse.YES, RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('ori',    OP_I_TYPE, 0x6,  None, ImmType.I, ALUOp.OR,  RsUse.YES, RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('andi',   OP_I_TYPE, 0x7,  None, ImmType.I, ALUOp.AND, RsUse.YES, RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    # Shift Imm (Bit30 distinguishes Logic/Arith shift)
    ('slli',   OP_I_TYPE, 0x1,  0,    ImmType.I, ALUOp.SLL, RsUse.YES, RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('srli',   OP_I_TYPE, 0x5,  0,    ImmType.I, ALUOp.SRL, RsUse.YES, RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),
    ('srai',   OP_I_TYPE, 0x5,  1,    ImmType.I, ALUOp.SRA, RsUse.YES, RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,  0, 0, WB.YES, 0, 0, 0),

    # --- I-type (Load) ---
    # ALU 计算地址 (RS1 + Imm)，Mem 读取
    ('lb',     OP_LOAD,   0x0,  None, ImmType.I, ALUOp.ADD, RsUse.YES, RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.LOAD,  MemWidth.BYTE, MemSign.SIGNED,   WB.YES, 0, 0, 0),
    ('lh',     OP_LOAD,   0x1,  None, ImmType.I, ALUOp.ADD, RsUse.YES, RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.LOAD,  MemWidth.HALF, MemSign.SIGNED,   WB.YES, 0, 0, 0),
    ('lw',     OP_LOAD,   0x2,  None, ImmType.I, ALUOp.ADD, RsUse.YES, RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.LOAD,  MemWidth.WORD, MemSign.SIGNED,   WB.YES, 0, 0, 0),
    ('lbu',    OP_LOAD,   0x4,  None, ImmType.I, ALUOp.ADD, RsUse.YES, RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.LOAD,  MemWidth.BYTE, MemSign.UNSIGNED, WB.YES, 0, 0, 0),
    ('lhu',    OP_LOAD,   0x5,  None, ImmType.I, ALUOp.ADD, RsUse.YES, RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.LOAD,  MemWidth.HALF, MemSign.UNSIGNED, WB.YES, 0, 0, 0),

    # --- S-type (Store) ---
    # ALU 计算地址 (RS1 + Imm)，Mem 写入
    ('sb',     OP_STORE,  0x0,  None, ImmType.S, ALUOp.ADD, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.IMM, MemOp.STORE, MemWidth.BYTE, 0, WB.NO,  0, 0, 0),
    ('sh',     OP_STORE,  0x1,  None, ImmType.S, ALUOp.ADD, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.IMM, MemOp.STORE, MemWidth.HALF, 0, WB.NO,  0, 0, 0),
    ('sw',     OP_STORE,  0x2,  None, ImmType.S, ALUOp.ADD, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.IMM, MemOp.STORE, MemWidth.WORD, 0, WB.NO,  0, 0, 0),

    # --- Branch ---
    # ALU 做比较 (Sub/Cmp)，PC Adder 算目标 (PC+Imm)，不写回
    ('beq',    OP_BRANCH, 0x0,  None, ImmType.B, ALUOp.SUB, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE, 0, 0, WB.NO, 1, 0, 0),
    ('bne',    OP_BRANCH, 0x1,  None, ImmType.B, ALUOp.SUB, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE, 0, 0, WB.NO, 1, 0, 0),
    ('blt',    OP_BRANCH, 0x4,  None, ImmType.B, ALUOp.SLT, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE, 0, 0, WB.NO, 1, 0, 0),
    ('bge',    OP_BRANCH, 0x5,  None, ImmType.B, ALUOp.SLT, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE, 0, 0, WB.NO, 1, 0, 0),
    ('bltu',   OP_BRANCH, 0x6,  None, ImmType.B, ALUOp.SLTU, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE, 0, 0, WB.NO, 1, 0, 0),
    ('bgeu',   OP_BRANCH, 0x7,  None, ImmType.B, ALUOp.SLTU, RsUse.YES, RsUse.YES, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE, 0, 0, WB.NO, 1, 0, 0),

    # --- JAL ---
    # ALU: PC + 4 (Link Data -> WB)
    # Tgt: PC + Imm (Jump Target -> IF)
    ('jal',    OP_JAL,    None, None, ImmType.J, ALUOp.ADD, RsUse.NO,  RsUse.NO,  Op1Sel.PC,  Op2Sel.CONST_4, MemOp.NONE, 0, 0, WB.YES, 1, 1, 0),

    # --- JALR ---
    # ALU: PC + 4 (Link Data -> WB)
    # Tgt: RS1 + Imm (Jump Target -> IF)
    ('jalr',   OP_JALR,   0x0,  None, ImmType.I, ALUOp.ADD, RsUse.YES, RsUse.NO,  Op1Sel.PC,  Op2Sel.CONST_4, MemOp.NONE, 0, 0, WB.YES, 1, 1, 1),

    # --- U-Type ---
    # LUI:   ALU 算 0 + Imm
    ('lui',    OP_LUI,    None, None, ImmType.U, ALUOp.ADD, RsUse.NO,  RsUse.NO,  Op1Sel.ZERO, Op2Sel.IMM, MemOp.NONE, 0, 0, WB.YES, 0, 0, 0),
    # AUIPC: ALU 算 PC + Imm
    ('auipc',  OP_AUIPC,  None, None, ImmType.U, ALUOp.ADD, RsUse.NO,  RsUse.NO,  Op1Sel.PC,  Op2Sel.IMM, MemOp.NONE, 0, 0, WB.YES, 0, 0, 0),

    # --- Environment (ECALL/EBREAK) ---
    # 作为特殊 I-Type 处理，但这里只给基本信号，具体逻辑由 Decoder/Execution 中的 finish() 逻辑拦截，直接停止模拟。
    ('ecall',  OP_SYSTEM, 0x0,  None, ImmType.I, ALUOp.NOP, RsUse.NO,  RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE, 0, 0, WB.NO, 0, 0, 0),
    ('ebreak', OP_SYSTEM, 0x0,  None, ImmType.I, ALUOp.NOP, RsUse.NO,  RsUse.NO,  Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE, 0, 0, WB.NO, 0, 0, 0),
]