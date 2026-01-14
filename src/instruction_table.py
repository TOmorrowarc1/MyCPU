from .control_signals import *

# RV32I 指令真值表
# 表格列定义:
# Key, Opcode, Funct3, Bit30 | ImmType, ALU_Func, Op1, Op2, Mem_Op, Width, Mem_Sign, csr_op_sel, alu_result_sel, csr_alu_op, branch_type, csr_we, is_MRET

rv32i_table = [

    # --- R-Type ---
    ('add', OP_R_TYPE, 0x0, 0, ImmType.R, ALUOp.ADD, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('sub', OP_R_TYPE, 0x0, 1, ImmType.R, ALUOp.SUB, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('sll', OP_R_TYPE, 0x1, 0, ImmType.R, ALUOp.SLL, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('slt', OP_R_TYPE, 0x2, 0, ImmType.R, ALUOp.SLT, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('sltu', OP_R_TYPE, 0x3, 0, ImmType.R, ALUOp.SLTU, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('xor', OP_R_TYPE, 0x4, 0, ImmType.R, ALUOp.XOR, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('srl', OP_R_TYPE, 0x5, 0, ImmType.R, ALUOp.SRL, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('sra', OP_R_TYPE, 0x5, 1, ImmType.R, ALUOp.SRA, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('or', OP_R_TYPE, 0x6, 0, ImmType.R, ALUOp.OR, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('and', OP_R_TYPE, 0x7, 0, ImmType.R, ALUOp.AND, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),

    # --- I-Type (ALU) ---
    ('addi', OP_I_TYPE, 0x0, None, ImmType.I, ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('slti', OP_I_TYPE, 0x2, None, ImmType.I, ALUOp.SLT, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('sltiu', OP_I_TYPE, 0x3, None, ImmType.I, ALUOp.SLTU, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('xori', OP_I_TYPE, 0x4, None, ImmType.I, ALUOp.XOR, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('ori', OP_I_TYPE, 0x6, None, ImmType.I, ALUOp.OR, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('andi', OP_I_TYPE, 0x7, None, ImmType.I, ALUOp.AND, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    # Shift Imm (Bit30 distinguishes Logic/Arith shift)
    ('slli', OP_I_TYPE, 0x1, None, ImmType.I, ALUOp.SLL, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('srli', OP_I_TYPE, 0x5, 0, ImmType.I, ALUOp.SRL, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('srai', OP_I_TYPE, 0x5, 1, ImmType.I, ALUOp.SRA, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),

    # --- I-type (Load) ---
    # ALU 计算地址 (RS1 + Imm)，Mem 读取
    ('lb', OP_LOAD, 0x0, None, ImmType.I, ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, MemOp.LOAD,
     MemWidth.BYTE, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('lh', OP_LOAD, 0x1, None, ImmType.I, ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, MemOp.LOAD,
     MemWidth.HALF, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('lw', OP_LOAD, 0x2, None, ImmType.I, ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, MemOp.LOAD,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('lbu', OP_LOAD, 0x4, None, ImmType.I, ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, MemOp.LOAD,
     MemWidth.BYTE, MemSign.UNSIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('lhu', OP_LOAD, 0x5, None, ImmType.I, ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, MemOp.LOAD,
     MemWidth.HALF, MemSign.UNSIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),

    # --- S-type (Store) ---
    # ALU 计算地址 (RS1 + Imm)，Mem 写入
    ('sb', OP_STORE, 0x0, None, ImmType.S, ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, MemOp.STORE,
     MemWidth.BYTE, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('sh', OP_STORE, 0x1, None, ImmType.S, ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, MemOp.STORE,
     MemWidth.HALF, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('sw', OP_STORE, 0x2, None, ImmType.S, ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, MemOp.STORE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),

    # --- Branch ---
    # ALU 做比较 (Sub/Cmp)，PC Adder 算目标 (PC+Imm)，不写回
    ('beq', OP_BRANCH, 0x0, None, ImmType.B, ALUOp.SUB, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.BEQ, CSRWe.DISABLE, is_MRET.NO),
    ('bne', OP_BRANCH, 0x1, None, ImmType.B, ALUOp.SUB, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.BNE, CSRWe.DISABLE, is_MRET.NO),
    ('blt', OP_BRANCH, 0x4, None, ImmType.B, ALUOp.SLT, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.BLT, CSRWe.DISABLE, is_MRET.NO),
    ('bge', OP_BRANCH, 0x5, None, ImmType.B, ALUOp.SLT, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.BGE, CSRWe.DISABLE, is_MRET.NO),
    ('bltu', OP_BRANCH, 0x6, None, ImmType.B, ALUOp.SLTU, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.BLTU, CSRWe.DISABLE, is_MRET.NO),
    ('bgeu', OP_BRANCH, 0x7, None, ImmType.B, ALUOp.SLTU, Op1Sel.RS1, Op2Sel.RS2, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.BGEU, CSRWe.DISABLE, is_MRET.NO),

    # --- JAL ---
    # ALU: PC + 4 (Link Data -> WB)
    # Tgt: PC + Imm (Jump Target -> IF)
    ('jal', OP_JAL, None, None, ImmType.J, ALUOp.ADD, Op1Sel.PC, Op2Sel.CONST_4, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.JAL, CSRWe.DISABLE, is_MRET.NO),

    # --- JALR ---
    # ALU: PC + 4 (Link Data -> WB)
    # Tgt: RS1 + Imm (Jump Target -> IF)
    ('jalr', OP_JALR, 0x0, None, ImmType.I, ALUOp.ADD, Op1Sel.PC, Op2Sel.CONST_4, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.JALR, CSRWe.DISABLE, is_MRET.NO),

    # --- U-Type ---
    # LUI:   ALU 算 0 + Imm
    ('lui', OP_LUI, None, None, ImmType.U, ALUOp.ADD, Op1Sel.ZERO, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    # AUIPC: ALU 算 PC + Imm
    ('auipc', OP_AUIPC, None, None, ImmType.U, ALUOp.ADD, Op1Sel.PC, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),

    # --- Environment (ECALL/EBREAK) ---
    ('ecall', OP_SYSTEM, 0x0, 0, ImmType.I, ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),
    ('ebreak', OP_SYSTEM, 0x0, 0, ImmType.I, ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.NO),

    # --- Zicsr 扩展指令 (CSR 指令) ---
    # 寄存器操作指令 (Register-Register Operations)
    # csrrw: CSR_RW 操作，使用 rs1 作为操作数
    ('csrrw', OP_SYSTEM, 0x1, None, ImmType.I, ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.CSR, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.ENABLE, is_MRET.NO),
    # csrrs: CSR_RS 操作，使用 rs1 作为操作数
    ('csrrs', OP_SYSTEM, 0x2, None, ImmType.I, ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.CSR, CSRALUOp.CSR_RS, BranchType.NO_BRANCH, CSRWe.ENABLE, is_MRET.NO),
    # csrrc: CSR_RC 操作，使用 rs1 作为操作数
    ('csrrc', OP_SYSTEM, 0x3, None, ImmType.I, ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.CSR, CSRALUOp.CSR_RC, BranchType.NO_BRANCH, CSRWe.ENABLE, is_MRET.NO),

    # 立即数操作指令 (Immediate-Register Operations)
    # csrrwi: CSR_RW 操作，使用立即数 (zimm) 作为操作数
    ('csrrwi', OP_SYSTEM, 0x5, None, ImmType.I, ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.IMM, ALUResultSel.CSR, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.ENABLE, is_MRET.NO),
    # csrrsi: CSR_RS 操作，使用立即数 (zimm) 作为操作数
    ('csrrsi', OP_SYSTEM, 0x6, None, ImmType.I, ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.IMM, ALUResultSel.CSR, CSRALUOp.CSR_RS, BranchType.NO_BRANCH, CSRWe.ENABLE, is_MRET.NO),
    # csrrci: CSR_RC 操作，使用立即数 (zimm) 作为操作数
    ('csrrci', OP_SYSTEM, 0x7, None, ImmType.I, ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.IMM, ALUResultSel.CSR, CSRALUOp.CSR_RC, BranchType.NO_BRANCH, CSRWe.ENABLE, is_MRET.NO),

    # --- MRET 指令 ---
    # mret: M-mode 返回指令
    ('mret', OP_SYSTEM, 0x0, 0, ImmType.I, ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, MemOp.NONE,
     MemWidth.WORD, MemSign.SIGNED, CSROpSel.RS1, ALUResultSel.ALU, CSRALUOp.CSR_RW, BranchType.NO_BRANCH, CSRWe.DISABLE, is_MRET.YES),
]
