from .control_signals import *


# 辅助函数：将BitPattern字符串转换为 (Value, Mask) 元组
# 一条指令 Bits(32)(x) 是合法的某类指令当且仅当 (x & Mask == Value)
def BP(pattern_str):
    # 输入: 由'0''1''?' 构成的字符串 e.g. "0000000??????????000?????0110011"
    # 输出: (Value, Mask) 的 Bits(32) 元组
    clean_str = pattern_str.replace("_", "")
    assert len(clean_str) == 32, f"Pattern length error: {pattern_str}"
    val = 0
    mask = 0
    for i, char in enumerate(reversed(clean_str)):
        if char == "0":
            # Value bit is 0, Mask bit is 1
            mask |= 1 << i
        elif char == "1":
            # Value bit is 1, Mask bit is 1
            val |= 1 << i
            mask |= 1 << i
        elif char == "?":
            # Value bit is 0, Mask bit is 0 (Don't Care)
            pass
        else:
            raise ValueError(f"Invalid char '{char}' in pattern")
    return Bits(32)(val), Bits(32)(mask)


# RV32I 指令真值表
# 表格列定义:
# Key, BP, ImmType, ALU_Func, Op1, Op2, Mem_Op, Width, Mem_Sign, branch_type, csr_op_sel, csr_alu_op, csr_re, csr_we

rv32i_table = [
    # --- R-Type ---
    (
        "add",
        BP("0000000_?????_?????_000_?????_0110011"),
        ImmType.R,
        (ALUOp.ADD, Op1Sel.RS1, Op2Sel.RS2, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "sub",
        BP("0100000_?????_?????_000_?????_0110011"),
        ImmType.R,
        (ALUOp.SUB, Op1Sel.RS1, Op2Sel.RS2, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "sll",
        BP("0000000_?????_?????_001_?????_0110011"),
        ImmType.R,
        (ALUOp.SLL, Op1Sel.RS1, Op2Sel.RS2, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "slt",
        BP("0000000_?????_?????_010_?????_0110011"),
        ImmType.R,
        (ALUOp.SLT, Op1Sel.RS1, Op2Sel.RS2, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "sltu",
        BP("0000000_?????_?????_011_?????_0110011"),
        ImmType.R,
        (ALUOp.SLTU, Op1Sel.RS1, Op2Sel.RS2, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "xor",
        BP("0000000_?????_?????_100_?????_0110011"),
        ImmType.R,
        (ALUOp.XOR, Op1Sel.RS1, Op2Sel.RS2, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "srl",
        BP("0000000_?????_?????_101_?????_0110011"),
        ImmType.R,
        (ALUOp.SRL, Op1Sel.RS1, Op2Sel.RS2, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "sra",
        BP("0100000_?????_?????_101_?????_0110011"),
        ImmType.R,
        (ALUOp.SRA, Op1Sel.RS1, Op2Sel.RS2, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "or",
        BP("0000000_?????_?????_110_?????_0110011"),
        ImmType.R,
        (ALUOp.OR, Op1Sel.RS1, Op2Sel.RS2, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "and",
        BP("0000000_?????_?????_111_?????_0110011"),
        ImmType.R,
        (ALUOp.AND, Op1Sel.RS1, Op2Sel.RS2, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    # --- I-Type (ALU) ---
    (
        "addi",
        BP("????????????_?????_000_?????_0010011"),
        ImmType.I,
        (ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "slti",
        BP("????????????_?????_010_?????_0010011"),
        ImmType.I,
        (ALUOp.SLT, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "sltiu",
        BP("????????????_?????_011_?????_0010011"),
        ImmType.I,
        (ALUOp.SLTU, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "xori",
        BP("????????????_?????_100_?????_0010011"),
        ImmType.I,
        (ALUOp.XOR, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "ori",
        BP("????????????_?????_110_?????_0010011"),
        ImmType.I,
        (ALUOp.OR, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "andi",
        BP("????????????_?????_111_?????_0010011"),
        ImmType.I,
        (ALUOp.AND, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    # Shift Imm (Bit30 distinguishes Logic/Arith shift)
    (
        "slli",
        BP("0000000?????_?????_001_?????_0010011"),
        ImmType.I,
        (ALUOp.SLL, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "srli",
        BP("0000000?????_?????_101_?????_0010011"),
        ImmType.I,
        (ALUOp.SRL, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "srai",
        BP("0100000?????_?????_101_?????_0010011"),
        ImmType.I,
        (ALUOp.SRA, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    # --- I-type (Load) ---
    # ALU 计算地址 (RS1 + Imm)，Mem 读取
    (
        "lb",
        BP("????????????_?????_000_?????_0000011"),
        ImmType.I,
        (ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.LOAD, MemWidth.BYTE, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "lh",
        BP("????????????_?????_001_?????_0000011"),
        ImmType.I,
        (ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.LOAD, MemWidth.HALF, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "lw",
        BP("????????????_?????_010_?????_0000011"),
        ImmType.I,
        (ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.LOAD, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "lbu",
        BP("????????????_?????_100_?????_0000011"),
        ImmType.I,
        (ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.LOAD, MemWidth.BYTE, MemSign.UNSIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "lhu",
        BP("????????????_?????_101_?????_0000011"),
        ImmType.I,
        (ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.LOAD, MemWidth.HALF, MemSign.UNSIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    # --- S-type (Store) ---
    # ALU 计算地址 (RS1 + Imm)，Mem 写入
    (
        "sb",
        BP("???????_?????_?????_000_?????_0100011"),
        ImmType.S,
        (ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.STORE, MemWidth.BYTE, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "sh",
        BP("???????_?????_?????_001_?????_0100011"),
        ImmType.S,
        (ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.STORE, MemWidth.HALF, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "sw",
        BP("???????_?????_?????_010_?????_0100011"),
        ImmType.S,
        (ALUOp.ADD, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.STORE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    # --- Branch ---
    # ALU 做比较 (Sub/Cmp)，PC Adder 算目标 (PC+Imm)，不写回
    (
        "beq",
        BP("????????????_?????_000_?????_1100011"),
        ImmType.B,
        (ALUOp.SUB, Op1Sel.RS1, Op2Sel.RS2, BranchType.BEQ),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "bne",
        BP("????????????_?????_001_?????_1100011"),
        ImmType.B,
        (ALUOp.SUB, Op1Sel.RS1, Op2Sel.RS2, BranchType.BNE),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "blt",
        BP("????????????_?????_100_?????_1100011"),
        ImmType.B,
        (ALUOp.SLT, Op1Sel.RS1, Op2Sel.RS2, BranchType.BLT),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "bge",
        BP("????????????_?????_101_?????_1100011"),
        ImmType.B,
        (ALUOp.SLT, Op1Sel.RS1, Op2Sel.RS2, BranchType.BGE),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "bltu",
        BP("????????????_?????_110_?????_1100011"),
        ImmType.B,
        (ALUOp.SLTU, Op1Sel.RS1, Op2Sel.RS2, BranchType.BLTU),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "bgeu",
        BP("????????????_?????_111_?????_1100011"),
        ImmType.B,
        (ALUOp.SLTU, Op1Sel.RS1, Op2Sel.RS2, BranchType.BGEU),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    # --- JAL ---
    # ALU: PC + 4 (Link Data -> WB)
    # Tgt: PC + Imm (Jump Target -> IF)
    (
        "jal",
        BP("?????????????????????????_1101111"),
        ImmType.J,
        (ALUOp.ADD, Op1Sel.PC, Op2Sel.CONST_4, BranchType.JAL),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    # --- JALR ---
    # ALU: PC + 4 (Link Data -> WB)
    # Tgt: RS1 + Imm (Jump Target -> IF)
    (
        "jalr",
        BP("????????????_?????_000_?????_1100111"),
        ImmType.I,
        (ALUOp.ADD, Op1Sel.PC, Op2Sel.CONST_4, BranchType.JALR),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    # --- U-Type ---
    # LUI:   ALU 算 0 + Imm
    (
        "lui",
        BP("?????????????????????????_0110111"),
        ImmType.U,
        (ALUOp.ADD, Op1Sel.ZERO, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    # AUIPC: ALU 算 PC + Imm
    (
        "auipc",
        BP("?????????????????????????_0010111"),
        ImmType.U,
        (ALUOp.ADD, Op1Sel.PC, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    # --- Environment (ECALL/EBREAK) ---
    (
        "ecall",
        BP("000000000000_00000_000_00000_1110011"),
        ImmType.I,
        (ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    (
        "ebreak",
        BP("000000000001_00000_000_00000_1110011"),
        ImmType.I,
        (ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
    # --- Zicsr 扩展指令 (CSR 指令) ---
    # 寄存器操作指令 (Register-Register Operations)
    # csrrw: CSR_RW 操作，使用 rs1 作为操作数
    (
        "csrrw",
        BP("????????????_?????_001_?????_1110011"),
        ImmType.Z,
        (ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.ENABLE, CSRWe.ENABLE),
    ),
    # csrrs: CSR_RS 操作，使用 rs1 作为操作数
    (
        "csrrs",
        BP("????????????_?????_010_?????_1110011"),
        ImmType.Z,
        (ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RS, CSRRe.ENABLE, CSRWe.ENABLE),
    ),
    # csrrc: CSR_RC 操作，使用 rs1 作为操作数
    (
        "csrrc",
        BP("????????????_?????_011_?????_1110011"),
        ImmType.Z,
        (ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RC, CSRRe.ENABLE, CSRWe.ENABLE),
    ),
    # 立即数操作指令 (Immediate-Register Operations)
    # csrrwi: CSR_RW 操作，使用立即数 (zimm) 作为操作数
    (
        "csrrwi",
        BP("????????????_?????_101_?????_1110011"),
        ImmType.Z,
        (ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.IMM, CSRALUOp.CSR_RW, CSRRe.ENABLE, CSRWe.ENABLE),
    ),
    # csrrsi: CSR_RS 操作，使用立即数 (zimm) 作为操作数
    (
        "csrrsi",
        BP("????????????_?????_110_?????_1110011"),
        ImmType.Z,
        (ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.IMM, CSRALUOp.CSR_RS, CSRRe.ENABLE, CSRWe.ENABLE),
    ),
    # csrrci: CSR_RC 操作，使用立即数 (zimm) 作为操作数
    (
        "csrrci",
        BP("????????????_?????_111_?????_1110011"),
        ImmType.Z,
        (ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.IMM, CSRALUOp.CSR_RC, CSRRe.ENABLE, CSRWe.ENABLE),
    ),
    # --- MRET 指令 ---
    # mret: M-mode 返回指令
    (
        "mret",
        BP("001100000010_00000_000_00000_1110011"),
        ImmType.Z,
        (ALUOp.SYS, Op1Sel.RS1, Op2Sel.IMM, BranchType.NO_BRANCH),
        (MemOp.NONE, MemWidth.WORD, MemSign.SIGNED),
        (CSROpSel.RS1, CSRALUOp.CSR_RW, CSRRe.DISABLE, CSRWe.DISABLE),
    ),
]
