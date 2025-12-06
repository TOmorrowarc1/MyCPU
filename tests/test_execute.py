import sys
import os
import re

# 1. 环境路径设置 (确保能 import src)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from assassyn.frontend import *

# 导入你的设计
from src.execution import Execution
from src.control_signals import *
from tests.common import run_test_module


# ==============================================================================
# 1. Driver 模块定义：前三行不能改，这是Assassyn的约定。
# ==============================================================================
class Driver(Module):
    def __init__(self):
        super().__init__(ports={})

    @module.combinational
    def build(
        self,
        dut: Module,
        mem_module: Module,
        ex_mem_bypass: Array,
        mem_wb_bypass: Array,
        wb_bypass: Array,
        branch_target_reg: Array,
    ):
        # --- 测试向量定义 ---
        # 格式: (alu_func, rs1_sel, rs2_sel, op1_sel, op2_sel, branch_type,
        #       next_pc_addr, pc, rs1_data, rs2_data, imm, ex_mem_fwd, mem_wb_fwd, wb_fwd, expected_result)
        #
        # alu_func: ALU功能码 (独热码)
        # rs1_sel/rs2_sel: 数据来源选择 (独热码)
        # op1_sel/op2_sel: 操作数选择 (独热码)
        # branch_type: 分支类型 (16位独热码)
        # next_pc_addr: 预测的下一条PC地址
        # pc: 当前PC值
        # rs1_data/rs2_data: 寄存器数据
        # imm: 立即数
        # ex_mem_fwd: EX-MEM旁路数据
        # mem_wb_fwd: MEM-WB旁路数据
        # wb_fwd: WB旁路数据
        # expected_result: 预期的ALU结果

        vectors = [
            # --- ALU 操作测试 ---
            # Case 0: ADD 指令 (rs1 + rs2)
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(10),
                Bits(32)(20),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(30),
            ),
            # Case 1: SUB 指令 (rs1 - rs2)
            (
                ALUOp.SUB,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(20),
                Bits(32)(10),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(10),
            ),
            # Case 2: AND 指令 (rs1 & rs2)
            (
                ALUOp.AND,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(0xF0F0F0F0),
                Bits(32)(0x0F0F0F0F),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x00000000),
            ),
            # Case 3: OR 指令 (rs1 | rs2)
            (
                ALUOp.OR,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(0xF0F0F0F0),
                Bits(32)(0x0F0F0F0F),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0xFFFFFFFF),
            ),
            # Case 4: SLL 指令 (rs1 << rs2[4:0])
            (
                ALUOp.SLL,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(0x0000000F),
                Bits(32)(2),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x0000003C),
            ),
            # Case 5: SRL 指令 (rs1 >> rs2[4:0])
            (
                ALUOp.SRL,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(0xFFFFFFFC),
                Bits(32)(2),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x3FFFFFFF),
            ),
            # Case 6: SRA 指令 (有符号右移)
            (
                ALUOp.SRA,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(0xFFFFFFF0),
                Bits(32)(2),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0xFFFFFFFC),
            ),
            # Case 7: SLT 指令 (有符号比较)
            (
                ALUOp.SLT,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(0xFFFFFFFB),
                Bits(32)(5),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(1),
            ),
            # Case 8: SLTU 指令 (无符号比较)
            (
                ALUOp.SLTU,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(0x80000000),
                Bits(32)(5),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
            ),
            # --- 旁路测试 ---
            # Case 9: 使用EX-MEM旁路数据
            (
                ALUOp.ADD,
                Rs1Sel.EX_MEM_BYPASS,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(10),
                Bits(32)(20),
                Bits(32)(0),
                Bits(32)(100),
                Bits(32)(0),
                Bits(32)(120),
            ),
            # Case 10: 使用MEM-WB旁路数据
            (
                ALUOp.ADD,
                Rs1Sel.MEM_WB_BYPASS,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(10),
                Bits(32)(20),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(200),
                Bits(32)(220),
            ),
            # --- WB旁路测试 ---
            # Case 11: 使用WB_BYPASS的ADD指令
            (
                ALUOp.ADD,
                Rs1Sel.WB_BYPASS,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(10),
                Bits(32)(20),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(300),
                Bits(32)(320),
            ),
            # Case 12: 使用WB_BYPASS的SUB指令
            (
                ALUOp.SUB,
                Rs1Sel.WB_BYPASS,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(20),
                Bits(32)(10),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(300),
                Bits(32)(290),
            ),
            # Case 13: 使用WB_BYPASS的AND指令
            (
                ALUOp.AND,
                Rs1Sel.WB_BYPASS,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(0xF0F0F0F0),
                Bits(32)(0x0F0F0F0F),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x12345678),
                Bits(32)(0x12345678 & 0x0F0F0F0F),
            ),
            # Case 14: 使用WB_BYPASS的OR指令
            (
                ALUOp.OR,
                Rs1Sel.WB_BYPASS,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(0xF0F0F0F0),
                Bits(32)(0x0F0F0F0F),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x12345678),
                Bits(32)(0x12345678 | 0x0F0F0F0F),
            ),
            # --- 旁路对比测试 ---
            # Case 15: 对比三种旁路 - ADD指令
            (
                ALUOp.ADD,
                Rs1Sel.EX_MEM_BYPASS,
                Rs2Sel.WB_BYPASS,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(10),
                Bits(32)(20),
                Bits(32)(0),
                Bits(32)(100),
                Bits(32)(200),
                Bits(32)(300),
            ),
            # Case 16: 对比三种旁路 - SUB指令
            (
                ALUOp.SUB,
                Rs1Sel.MEM_WB_BYPASS,
                Rs2Sel.WB_BYPASS,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(200),
                Bits(32)(100),
                Bits(32)(0),
                Bits(32)(200),
                Bits(32)(100),
                Bits(32)(100),
            ),
            # --- 分支指令测试 ---
            # Case 17: BEQ (相等分支)
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.BEQ,
                Bits(32)(0x1008),
                Bits(32)(0x1000),
                Bits(32)(10),
                Bits(32)(10),
                Bits(32)(8),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
            ),  # 10-10=0，BEQ条件成立
            # Case 18: BNE (不等分支)
            (
                ALUOp.SUB,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.BNE,
                Bits(32)(0x1008),
                Bits(32)(0x1000),
                Bits(32)(10),
                Bits(32)(20),
                Bits(32)(8),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0xFFFFFFFE),
            ),  # 10-20=-10≠0，BNE条件成立
            # Case 19: BLT (小于分支)
            (
                ALUOp.SLT,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.BLT,
                Bits(32)(0x1008),
                Bits(32)(0x1000),
                Bits(32)(5),
                Bits(32)(10),
                Bits(32)(8),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(1),
            ),  # 5<10，BLT条件成立
            # Case 20: BGE (大于等于分支)
            (
                ALUOp.SLTU,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.BGE,
                Bits(32)(0x1008),
                Bits(32)(0x1000),
                Bits(32)(10),
                Bits(32)(5),
                Bits(32)(8),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
            ),  # 10>=5，BGE条件成立
            # --- JAL/JALR 指令测试 ---
            # Case 21: JAL (直接跳转)
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.PC,
                Op2Sel.CONST_4,
                BranchType.JAL,
                Bits(32)(0x1008),
                Bits(32)(0x1000),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(8),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1004),
            ),  # PC+4=0x1004
            # Case 22: JALR (间接跳转)
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.PC,
                Op2Sel.CONST_4,
                BranchType.JALR,
                Bits(32)(0x2000),
                Bits(32)(0x1000),
                Bits(32)(0x2000),
                Bits(32)(0),
                Bits(32)(8),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1004),
            ),  # PC+4=0x1004，但跳转到0x2008
            # --- 更多分支指令测试 ---
            # Case 23: BEQ (不相等分支，不跳转)
            (
                ALUOp.SUB,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.BEQ,
                Bits(32)(0x1008),
                Bits(32)(0x1000),
                Bits(32)(10),
                Bits(32)(20),
                Bits(32)(8),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0xFFFFFFFE),
            ),  # 10-20=-10≠0，BEQ条件不成立
            # Case 24: BNE (相等分支，不跳转)
            (
                ALUOp.SUB,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.BNE,
                Bits(32)(0x1008),
                Bits(32)(0x1000),
                Bits(32)(10),
                Bits(32)(10),
                Bits(32)(8),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
            ),  # 10-10=0，BNE条件不成立
            # Case 25: BLT (不小于分支，不跳转)
            (
                ALUOp.SLT,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.BLT,
                Bits(32)(0x1008),
                Bits(32)(0x1000),
                Bits(32)(10),
                Bits(32)(5),
                Bits(32)(8),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
            ),  # 10>=5，BLT条件不成立
            # Case 26: BGE (小于分支，不跳转)
            (
                ALUOp.SLTU,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.BGE,
                Bits(32)(0x1008),
                Bits(32)(0x1000),
                Bits(32)(5),
                Bits(32)(10),
                Bits(32)(8),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(1),
            ),  # 5<10，BGE条件不成立
            # Case 27: BLTU (无符号不小于分支，不跳转)
            (
                ALUOp.SLTU,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.BLTU,
                Bits(32)(0x1008),
                Bits(32)(0x1000),
                Bits(32)(10),
                Bits(32)(5),
                Bits(32)(8),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
            ),  # 10>=5，BLTU条件不成立
            # Case 28: BGEU (无符号小于分支，不跳转)
            (
                ALUOp.SLTU,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.RS2,
                BranchType.BGEU,
                Bits(32)(0x1008),
                Bits(32)(0x1000),
                Bits(32)(5),
                Bits(32)(10),
                Bits(32)(8),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(1),
            ),  # 5<10，BGEU条件不成立
            # --- Store 指令测试 ---
            # Case 29: SW (Store Word) - 存储数据到地址0x1000
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(0x1000),
                Bits(32)(0x12345678),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1004),
            ),  # 地址=0x1000, 数据=0x12345678
            # Case 30: SW (Store Word) - 存储数据到地址0x1004
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1008),
                Bits(32)(0x1004),
                Bits(32)(0x1004),
                Bits(32)(0xABCDEF00),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1008),
            ),  # 地址=0x1004, 数据=0xABCDEF00
            # Case 31: SW (Store Word) - 存储数据到地址0x1008
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x100C),
                Bits(32)(0x1008),
                Bits(32)(0x1008),
                Bits(32)(0x11223344),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x100C),
            ),  # 地址=0x1008, 数据=0x11223344
            # --- Load 指令测试 ---
            # Case 32: LW (Load Word) - 从地址0x1000加载数据
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(0x1000),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1004),
            ),  # 地址=0x1000, 预期加载0x12345678
            # Case 33: LW (Load Word) - 从地址0x1004加载数据
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1008),
                Bits(32)(0x1004),
                Bits(32)(0x1004),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1008),
            ),  # 地址=0x1004, 预期加载0xABCDEF00
            # Case 34: LW (Load Word) - 从地址0x1008加载数据
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x100C),
                Bits(32)(0x1008),
                Bits(32)(0x1008),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x100C),
            ),  # 地址=0x1008, 预期加载0x11223344
            # --- 地址对齐测试 ---
            # Case 35: SW (Store Word) - 未对齐地址访问
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(0x1001),
                Bits(32)(0x55555555),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1004),
            ),  # 未对齐地址=0x1001
            # Case 36: LW (Load Word) - 未对齐地址访问
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1004),
                Bits(32)(0x1000),
                Bits(32)(0x1003),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1004),
            ),  # 未对齐地址=0x1003
            # --- 不同宽度的Store指令测试 ---
            # Case 37: SH (Store Half) - 存储半字到地址0x1010
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1014),
                Bits(32)(0x1010),
                Bits(32)(0x1010),
                Bits(32)(0xABCD),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1014),
            ),  # 地址=0x1010, 数据=0xABCD
            # Case 38: SB (Store Byte) - 存储字节到地址0x1011
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1014),
                Bits(32)(0x1010),
                Bits(32)(0x1011),
                Bits(32)(0xEF),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1014),
            ),  # 地址=0x1011, 数据=0xEF
            # --- 不同宽度的Load指令测试 ---
            # Case 39: LH (Load Half) - 从地址0x1010加载半字（有符号）
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1014),
                Bits(32)(0x1010),
                Bits(32)(0x1010),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1014),
            ),  # 地址=0x1010, 预期加载0xABCD
            # Case 40: LHU (Load Half Unsigned) - 从地址0x1010加载半字（无符号）
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1014),
                Bits(32)(0x1010),
                Bits(32)(0x1010),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1014),
            ),  # 地址=0x1010, 预期加载0x0000ABCD
            # Case 41: LB (Load Byte) - 从地址0x1011加载字节（有符号）
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1014),
                Bits(32)(0x1010),
                Bits(32)(0x1011),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1014),
            ),  # 地址=0x1011, 预期加载0xFFFFFFEF
            # Case 42: LBU (Load Byte Unsigned) - 从地址0x1011加载字节（无符号）
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1014),
                Bits(32)(0x1010),
                Bits(32)(0x1011),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1014),
            ),  # 地址=0x1011, 预期加载0x000000EF
            # --- 混合宽度测试 ---
            # Case 43: SW + SH + SB - 连续存储不同宽度的数据
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1020),
                Bits(32)(0x1020),
                Bits(32)(0x12345678),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1024),
            ),  # 地址=0x1020, 数据=0x12345678
            # Case 44: 从0x1020读取字，验证之前存储的数据
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1024),
                Bits(32)(0x1020),
                Bits(32)(0x1020),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1024),
            ),  # 地址=0x1020, 预期加载0x12345678
            # --- 半字和字节未对齐测试 ---
            # Case 45: SH (Store Half) - 未对齐地址访问
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1024),
                Bits(32)(0x1020),
                Bits(32)(0x1021),
                Bits(32)(0x1234),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1024),
            ),  # 未对齐地址=0x1021
            # Case 46: LH (Load Half) - 未对齐地址访问
            (
                ALUOp.ADD,
                Rs1Sel.RS1,
                Rs2Sel.RS2,
                Op1Sel.RS1,
                Op2Sel.CONST_4,
                BranchType.NO_BRANCH,
                Bits(32)(0x1024),
                Bits(32)(0x1020),
                Bits(32)(0x1023),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0),
                Bits(32)(0x1024),
            ),  # 未对齐地址=0x1023
        ]

        # --- 激励生成逻辑 ---
        # 1. 计数器：跟踪当前测试进度
        cnt = RegArray(UInt(32), 1)
        (cnt & self)[0] <= cnt[0] + UInt(32)(1)

        idx = cnt[0]

        # 2. 创建EX阶段输入寄存器
        ex_ctrl_reg = RegArray(Bits(32), 1)  # 存储控制信号
        pc_reg = RegArray(Bits(32), 1)  # 存储PC值
        rs1_data_reg = RegArray(Bits(32), 1)  # 存储rs1数据
        rs2_data_reg = RegArray(Bits(32), 1)  # 存储rs2数据
        imm_reg = RegArray(Bits(32), 1)  # 存储立即数

        # 3. 组合逻辑 Mux：根据 idx 选择当前的测试向量
        # 初始化默认值
        current_alu_func = Bits(16)(0)
        current_rs1_sel = Bits(4)(0)
        current_rs2_sel = Bits(4)(0)
        current_op1_sel = Bits(3)(0)
        current_op2_sel = Bits(3)(0)
        current_branch_type = Bits(16)(0)
        current_next_pc_addr = Bits(32)(0)
        current_pc = Bits(32)(0)
        current_rs1_data = Bits(32)(0)
        current_rs2_data = Bits(32)(0)
        current_imm = Bits(32)(0)
        current_ex_mem_fwd = Bits(32)(0)
        current_mem_wb_fwd = Bits(32)(0)
        current_wb_fwd = Bits(32)(0)
        current_expected = Bits(32)(0)

        # 这里的循环展开会生成一棵 Mux 树
        for i, (
            alu_func,
            rs1_sel,
            rs2_sel,
            op1_sel,
            op2_sel,
            branch_type,
            next_pc_addr,
            pc,
            rs1_data,
            rs2_data,
            imm,
            ex_mem_fwd,
            mem_wb_fwd,
            wb_fwd,
            expected,
        ) in enumerate(vectors):
            is_match = idx == UInt(32)(i)

            current_alu_func = is_match.select(alu_func, current_alu_func)
            current_rs1_sel = is_match.select(rs1_sel, current_rs1_sel)
            current_rs2_sel = is_match.select(rs2_sel, current_rs2_sel)
            current_op1_sel = is_match.select(op1_sel, current_op1_sel)
            current_op2_sel = is_match.select(op2_sel, current_op2_sel)
            current_branch_type = is_match.select(branch_type, current_branch_type)
            current_next_pc_addr = is_match.select(next_pc_addr, current_next_pc_addr)
            current_pc = is_match.select(pc, current_pc)
            current_rs1_data = is_match.select(rs1_data, current_rs1_data)
            current_rs2_data = is_match.select(rs2_data, current_rs2_data)
            current_imm = is_match.select(imm, current_imm)
            current_ex_mem_fwd = is_match.select(ex_mem_fwd, current_ex_mem_fwd)
            current_mem_wb_fwd = is_match.select(mem_wb_fwd, current_mem_wb_fwd)
            current_wb_fwd = is_match.select(wb_fwd, current_wb_fwd)
            current_expected = is_match.select(expected, current_expected)

        # 4. 构建控制信号包
        # 首先创建mem_ctrl信号
        # 根据测试用例索引设置不同的内存操作
        mem_opcode = MemOp.NONE  # 默认不进行内存操作
        mem_width = MemWidth.WORD  # 默认字访问
        mem_unsigned = MemSign.UNSIGNED  # 默认无符号扩展

        # 为Store和Load操作设置内存操作码和宽度
        with Condition(idx >= UInt(32)(29) & idx < UInt(32)(32)):  # Cases 29-31: SW操作
            mem_opcode = MemOp.STORE
            mem_width = MemWidth.WORD

        with Condition(idx >= UInt(32)(32) & idx < UInt(32)(35)):  # Cases 32-34: LW操作
            mem_opcode = MemOp.LOAD
            mem_width = MemWidth.WORD

        with Condition(
            idx >= UInt(32)(35) & idx < UInt(32)(37)
        ):  # Cases 35-36: 未对齐访问测试
            mem_opcode = MemOp.STORE if (idx == UInt(32)(35)) else MemOp.LOAD
            mem_width = MemWidth.WORD

        # 不同宽度的Store操作
        with Condition(idx == UInt(32)(37)):  # Case 37: SH操作
            mem_opcode = MemOp.STORE
            mem_width = MemWidth.HALF

        with Condition(idx == UInt(32)(38)):  # Case 38: SB操作
            mem_opcode = MemOp.STORE
            mem_width = MemWidth.BYTE

        # 不同宽度的Load操作
        with Condition(idx == UInt(32)(39)):  # Case 39: LH操作
            mem_opcode = MemOp.LOAD
            mem_width = MemWidth.HALF
            mem_unsigned = MemSign.SIGNED  # 有符号扩展

        with Condition(idx == UInt(32)(40)):  # Case 40: LHU操作
            mem_opcode = MemOp.LOAD
            mem_width = MemWidth.HALF
            mem_unsigned = MemSign.UNSIGNED  # 无符号扩展

        with Condition(idx == UInt(32)(41)):  # Case 41: LB操作
            mem_opcode = MemOp.LOAD
            mem_width = MemWidth.BYTE
            mem_unsigned = MemSign.SIGNED  # 有符号扩展

        with Condition(idx == UInt(32)(42)):  # Case 42: LBU操作
            mem_opcode = MemOp.LOAD
            mem_width = MemWidth.BYTE
            mem_unsigned = MemSign.UNSIGNED  # 无符号扩展

        # 混合宽度测试
        with Condition(idx == UInt(32)(43)):  # Case 43: SW操作
            mem_opcode = MemOp.STORE
            mem_width = MemWidth.WORD

        with Condition(idx == UInt(32)(44)):  # Case 44: LW操作
            mem_opcode = MemOp.LOAD
            mem_width = MemWidth.WORD

        # 半字和字节未对齐测试
        with Condition(idx == UInt(32)(45)):  # Case 45: SH操作
            mem_opcode = MemOp.STORE
            mem_width = MemWidth.HALF

        with Condition(idx == UInt(32)(46)):  # Case 46: LH操作
            mem_opcode = MemOp.LOAD
            mem_width = MemWidth.HALF
            mem_unsigned = MemSign.SIGNED  # 有符号扩展

        mem_ctrl = mem_ctrl_signals.bundle(
            mem_opcode=mem_opcode,
            mem_width=mem_width,
            mem_unsigned=mem_unsigned,
            rd_addr=Bits(5)(1),  # 默认写入x1寄存器
        )

        # 然后创建ex_ctrl信号
        ctrl_pkt = ex_ctrl_signals.bundle(
            alu_func=current_alu_func,
            rs1_sel=current_rs1_sel,
            rs2_sel=current_rs2_sel,
            op1_sel=current_op1_sel,
            op2_sel=current_op2_sel,
            branch_type=current_branch_type,
            next_pc_addr=current_next_pc_addr,
            mem_ctrl=mem_ctrl,
        )

        # 5. 将测试向量数据写入寄存器
        # 使用RegArray为每个输入信号创建寄存器
        ex_ctrl_reg[0] <= ctrl_pkt
        pc_reg[0] <= current_pc
        rs1_data_reg[0] <= current_rs1_data
        rs2_data_reg[0] <= current_rs2_data
        imm_reg[0] <= current_imm

        # 6. 设置旁路数据
        ex_mem_bypass[0] = current_ex_mem_fwd
        mem_wb_bypass[0] = current_mem_wb_fwd
        wb_bypass[0] = current_wb_fwd

        # 7. 发送数据到Execution模块
        # 只有当 idx 在向量范围内时才发送 (valid)
        valid_test = idx < UInt(32)(len(vectors))

        with Condition(valid_test):
            # 打印 Driver 发出的请求，方便对比调试
            log(
                "Driver: idx={} alu_func={} rs1_sel={} rs2_sel={} op1_sel={} op2_sel={} branch_type={} pc=0x{:x} rs1=0x{:x} rs2=0x{:x} imm=0x{:x} ex_mem_fwd=0x{:x} mem_wb_fwd=0x{:x} wb_fwd=0x{:x} expected=0x{:x}",
                idx,
                current_alu_func,
                current_rs1_sel,
                current_rs2_sel,
                current_op1_sel,
                current_op2_sel,
                current_branch_type,
                current_pc,
                current_rs1_data,
                current_rs2_data,
                current_imm,
                current_ex_mem_fwd,
                current_mem_wb_fwd,
                current_wb_fwd,
                current_expected,
            )

            # 从寄存器读取数据并调用Execution模块
            dut.async_called(
                ctrl=ex_ctrl_reg[0],
                pc=pc_reg[0],
                rs1_data=rs1_data_reg[0],
                rs2_data=rs2_data_reg[0],
                imm=imm_reg[0],
            )

        # [关键] 返回 cnt 和预期结果，让它们成为模块的输出
        return cnt, current_expected


# ==============================================================================
# 2. Mock 模块定义：用于接收EX模块的输出
# ==============================================================================
class MockSRAM(Downstream):
    def __init__(self):
        super().__init__()

    @module.combinational
    def build(self, we, re, addr, wdata):
        # 捕获并打印 EX 模块发出的信号
        with Condition(we):
            log("SRAM: EX阶段 - we=True re=False addr=0x{:x} wdata=0x{:x}", addr, wdata)
            # 模拟SRAM存储操作
            log("SRAM: MEM阶段 - Write WORD addr=0x{:x} data=0x{:x}", addr, wdata)

            # 检查未对齐访问
            if addr[1:0] != Bits(2)(0):
                log("SRAM: Warning - Unaligned access addr=0x{:x} we=True", addr)

        with Condition(re):
            log("SRAM: EX阶段 - we=False re=True addr=0x{:x}", addr)
            # 模拟SRAM加载操作
            # 根据地址返回不同的数据，模拟真实的SRAM行为
            if addr == Bits(32)(0x1000):
                data = Bits(32)(0x12345678)
            elif addr == Bits(32)(0x1004):
                data = Bits(32)(0xABCDEF00)
            elif addr == Bits(32)(0x1008):
                data = Bits(32)(0x11223344)
            elif addr == Bits(32)(0x1010):
                data = Bits(32)(0x0000ABCD)
            elif addr == Bits(32)(0x1011):
                data = Bits(32)(0xFFFFFFEF)
            else:
                data = Bits(32)(0x00000000)

            log("SRAM: MEM阶段 - Read WORD addr=0x{:x} data=0x{:x}", addr, data)

            # 检查未对齐访问
            if addr[1:0] != Bits(2)(0):
                log("SRAM: Warning - Unaligned access addr=0x{:x} re=True", addr)

            # 返回读取的数据
            return data


class MockMEM(Module):
    def __init__(self):
        # 定义与 MEM 模块一致的输入端口
        super().__init__(
            ports={"ctrl": Port(mem_ctrl_signals), "alu_result": Port(Bits(32))}
        )

    @module.combinational
    def build(self):
        # 接收并打印
        ctrl, res = self.pop_all_ports(False)
        # 打印有效数据
        # 这里可以验证 EX 算出的结果
        log("[MEM_Sink] Recv: ALU_Res=0x{:x} Is_Load={}", res, ctrl.is_load)


class MockFeedback(Module):
    def __init__(self):
        super().__init__(ports={})
        self.name = "FeedbackSink"

    @module.combinational
    def build(self, branch_target: Array, exec_bypass: Array):
        # 读取寄存器的当前值 (Q端)
        # 注意：这里读到的是上一拍 EX 阶段写入的结果
        tgt = branch_target[0]
        byp = exec_bypass[0]

        # 打印日志供 check 函数验证
        # 格式建议包含 [Feedback] 标签以便区分
        log("[Feedback] Target=0x{:x} Bypass=0x{:x}", tgt, byp)

        # 检验branch_target_reg的值
        log("Sink: 检验branch_target_reg - value=0x{:x}", tgt)


# ==============================================================================
# 3. 验证逻辑 (Python Check)
# ==============================================================================
def check(raw_output):
    print(">>> 开始验证EX模块输出...")

    # 预期结果列表 (必须与Driver中的vectors严格对应)
    # 根据用户反馈，SRAM在EX阶段只输入目标地址，无论读写都在下周期进行，只有MEM阶段能看到，所以预期输出是地址而非结果
    expected_results = [
        0x0000001E,  # Case 0: ADD (10+20=30) - 非内存操作，输出ALU结果
        0x0000000A,  # Case 1: SUB (20-10=10) - 非内存操作，输出ALU结果
        0x00000000,  # Case 2: AND (0xF0F0F0F0 & 0x0F0F0F0F = 0x00000000) - 非内存操作，输出ALU结果
        0xFFFFFFFF,  # Case 3: OR (0xF0F0F0F0 | 0x0F0F0F0F = 0xFFFFFFFF) - 非内存操作，输出ALU结果
        0x0000003C,  # Case 4: SLL (0x0000000F << 2 = 0x0000003C) - 非内存操作，输出ALU结果
        0x3FFFFFFF,  # Case 5: SRL (0xFFFFFFFC >> 2 = 0x3FFFFFFF) - 非内存操作，输出ALU结果
        0xFFFFFFFC,  # Case 6: SRA (0xFFFFFFF0 >> 2 = 0xFFFFFFFC) - 非内存操作，输出ALU结果
        0x00000001,  # Case 7: SLT (-5 < 5 = 1) - 非内存操作，输出ALU结果
        0x00000000,  # Case 8: SLTU (0x80000000 < 5 = 0, 无符号比较) - 非内存操作，输出ALU结果
        0x00000078,  # Case 9: 使用EX-MEM旁路 (100+20=120) - 非内存操作，输出ALU结果
        0x000000DC,  # Case 10: 使用MEM-WB旁路 (200+20=220) - 非内存操作，输出ALU结果
        0x00000140,  # Case 11: 使用WB_BYPASS的ADD指令 (300+20=320) - 非内存操作，输出ALU结果
        0x00000122,  # Case 12: 使用WB_BYPASS的SUB指令 (300-10=290) - 非内存操作，输出ALU结果
        0x01040408,  # Case 13: 使用WB_BYPASS的AND指令 (0x12345678 & 0x0F0F0F0F = 0x01040408) - 非内存操作，输出ALU结果
        0x1B3F5F7F,  # Case 14: 使用WB_BYPASS的OR指令 (0x12345678 | 0x0F0F0F0F = 0x1B3F5F7F) - 非内存操作，输出ALU结果
        0x0000012C,  # Case 15: 对比三种旁路 - ADD指令 (100+200=300) - 非内存操作，输出ALU结果
        0x00000064,  # Case 16: 对比三种旁路 - SUB指令 (200-100=100) - 非内存操作，输出ALU结果
        0x00000000,  # Case 17: BEQ (10-10=0) - 非内存操作，输出ALU结果
        0xFFFFFFFE,  # Case 18: BNE (10-20=-10) - 非内存操作，输出ALU结果
        0x00000001,  # Case 19: BLT (5<10=1) - 非内存操作，输出ALU结果
        0x00000000,  # Case 20: BGE (10>=5=0) - 非内存操作，输出ALU结果
        0x00001004,  # Case 21: JAL (PC+4=0x1004) - 非内存操作，输出ALU结果
        0x00001004,  # Case 22: JALR (PC+4=0x1004) - 非内存操作，输出ALU结果
        0xFFFFFFFE,  # Case 23: BEQ (10-20=-10≠0，BEQ条件不成立) - 非内存操作，输出ALU结果
        0x00000000,  # Case 24: BNE (10-10=0，BNE条件不成立) - 非内存操作，输出ALU结果
        0x00000000,  # Case 25: BLT (10>=5，BLT条件不成立) - 非内存操作，输出ALU结果
        0x00000001,  # Case 26: BGE (5<10，BGE条件不成立) - 非内存操作，输出ALU结果
        0x00000000,  # Case 27: BLTU (10>=5，BLTU条件不成立) - 非内存操作，输出ALU结果
        0x00000001,  # Case 28: BGEU (5<10，BGEU条件不成立) - 非内存操作，输出ALU结果
        0x00001000,  # Case 29: SW (地址=0x1000) - 内存操作，输出地址而非结果
        0x00001004,  # Case 30: SW (地址=0x1004) - 内存操作，输出地址而非结果
        0x00001008,  # Case 31: SW (地址=0x1008) - 内存操作，输出地址而非结果
        0x00001000,  # Case 32: LW (地址=0x1000) - 内存操作，输出地址而非结果
        0x00001004,  # Case 33: LW (地址=0x1004) - 内存操作，输出地址而非结果
        0x00001008,  # Case 34: LW (地址=0x1008) - 内存操作，输出地址而非结果
        0x00001001,  # Case 35: SW (未对齐地址=0x1001) - 内存操作，输出地址而非结果
        0x00001003,  # Case 36: LW (未对齐地址=0x1003) - 内存操作，输出地址而非结果
        0x00001020,  # Case 37: SW (地址=0x1020) - 内存操作，输出地址而非结果
        0x00001020,  # Case 38: LW (地址=0x1020) - 内存操作，输出地址而非结果
        0x00001021,  # Case 39: SH (未对齐地址=0x1021) - 内存操作，输出地址而非结果
        0x00001023,  # Case 40: LH (未对齐地址=0x1023) - 内存操作，输出地址而非结果
    ]

    # 预期分支类型列表 (必须与Driver中的vectors严格对应)
    expected_branch_types = [
        "NO_BRANCH",  # Case 0: ADD
        "NO_BRANCH",  # Case 1: SUB
        "NO_BRANCH",  # Case 2: AND
        "NO_BRANCH",  # Case 3: OR
        "NO_BRANCH",  # Case 4: SLL
        "NO_BRANCH",  # Case 5: SRL
        "NO_BRANCH",  # Case 6: SRA
        "NO_BRANCH",  # Case 7: SLT
        "NO_BRANCH",  # Case 8: SLTU
        "NO_BRANCH",  # Case 9: 使用EX-MEM旁路
        "NO_BRANCH",  # Case 10: 使用MEM-WB旁路
        "NO_BRANCH",  # Case 11: 使用WB_BYPASS的ADD指令
        "NO_BRANCH",  # Case 12: 使用WB_BYPASS的SUB指令
        "NO_BRANCH",  # Case 13: 使用WB_BYPASS的AND指令
        "NO_BRANCH",  # Case 14: 使用WB_BYPASS的OR指令
        "NO_BRANCH",  # Case 15: 对比三种旁路 - ADD指令
        "NO_BRANCH",  # Case 16: 对比三种旁路 - SUB指令
        "BEQ",  # Case 17: BEQ (相等分支)
        "BNE",  # Case 18: BNE (不等分支)
        "BLT",  # Case 19: BLT (小于分支)
        "BGE",  # Case 20: BGE (大于等于分支)
        "JAL",  # Case 21: JAL (直接跳转)
        "JALR",  # Case 22: JALR (间接跳转)
        "BEQ",  # Case 23: BEQ (不相等分支，不跳转)
        "BNE",  # Case 24: BNE (相等分支，不跳转)
        "BLT",  # Case 25: BLT (不小于分支，不跳转)
        "BGE",  # Case 26: BGE (小于分支，不跳转)
        "BLTU",  # Case 27: BLTU (无符号不小于分支，不跳转)
        "BGEU",  # Case 28: BGEU (无符号小于分支，不跳转)
        "NO_BRANCH",  # Case 29: SW
        "NO_BRANCH",  # Case 30: LW
        "NO_BRANCH",  # Case 31: SH
        "NO_BRANCH",  # Case 32: LH
        "NO_BRANCH",  # Case 33: LHU
        "NO_BRANCH",  # Case 34: LB
        "NO_BRANCH",  # Case 35: LBU
        "NO_BRANCH",  # Case 36: SW
        "NO_BRANCH",  # Case 37: LW
        "NO_BRANCH",  # Case 38: SH
        "NO_BRANCH",  # Case 39: LH
    ]

    # 预期分支目标地址列表 (只有分支指令会更新分支目标寄存器)
    expected_branch_targets = [
        None,  # Case 0: ADD (无分支)
        None,  # Case 1: SUB (无分支)
        None,  # Case 2: AND (无分支)
        None,  # Case 3: OR (无分支)
        None,  # Case 4: SLL (无分支)
        None,  # Case 5: SRL (无分支)
        None,  # Case 6: SRA (无分支)
        None,  # Case 7: SLT (无分支)
        None,  # Case 8: SLTU (无分支)
        None,  # Case 9: 使用EX-MEM旁路 (无分支)
        None,  # Case 10: 使用MEM-WB旁路 (无分支)
        None,  # Case 11: 使用WB_BYPASS的ADD指令 (无分支)
        None,  # Case 12: 使用WB_BYPASS的SUB指令 (无分支)
        None,  # Case 13: 使用WB_BYPASS的AND指令 (无分支)
        None,  # Case 14: 使用WB_BYPASS的OR指令 (无分支)
        None,  # Case 15: 对比三种旁路 - ADD指令 (无分支)
        None,  # Case 16: 对比三种旁路 - SUB指令 (无分支)
        0x1008,  # Case 17: BEQ (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 18: BNE (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 19: BLT (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 20: BGE (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 21: JAL (PC + 8 = 0x1000 + 8 = 0x1008)
        0x2008,  # Case 22: JALR (rs1 + imm = 0x2000 + 8 = 0x2008)
        0x1008,  # Case 23: BEQ (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 24: BNE (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 25: BLT (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 26: BGE (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 27: BLTU (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 28: BGEU (PC + 8 = 0x1000 + 8 = 0x1008)
        None,  # Case 29: SW (无分支)
        None,  # Case 30: LW (无分支)
        None,  # Case 31: SH (无分支)
        None,  # Case 32: LH (无分支)
        None,  # Case 33: LHU (无分支)
        None,  # Case 34: LB (无分支)
        None,  # Case 35: LBU (无分支)
        None,  # Case 36: SW (无分支)
        None,  # Case 37: LW (无分支)
        None,  # Case 38: SH (无分支)
        None,  # Case 39: LH (无分支)
    ]

    # 预期分支是否跳转列表
    expected_branch_taken = [
        False,  # Case 0: ADD (无分支)
        False,  # Case 1: SUB (无分支)
        False,  # Case 2: AND (无分支)
        False,  # Case 3: OR (无分支)
        False,  # Case 4: SLL (无分支)
        False,  # Case 5: SRL (无分支)
        False,  # Case 6: SRA (无分支)
        False,  # Case 7: SLT (无分支)
        False,  # Case 8: SLTU (无分支)
        False,  # Case 9: 使用EX-MEM旁路 (无分支)
        False,  # Case 10: 使用MEM-WB旁路 (无分支)
        False,  # Case 11: 使用WB_BYPASS的ADD指令 (无分支)
        False,  # Case 12: 使用WB_BYPASS的SUB指令 (无分支)
        False,  # Case 13: 使用WB_BYPASS的AND指令 (无分支)
        False,  # Case 14: 使用WB_BYPASS的OR指令 (无分支)
        False,  # Case 15: 对比三种旁路 - ADD指令 (无分支)
        False,  # Case 16: 对比三种旁路 - SUB指令 (无分支)
        True,  # Case 17: BEQ (10 == 10，条件成立，跳转)
        True,  # Case 18: BNE (10 != 20，条件成立，跳转)
        True,  # Case 19: BLT (5 < 10，条件成立，跳转)
        True,  # Case 20: BGE (10 >= 5，条件成立，跳转)
        True,  # Case 21: JAL (无条件跳转)
        True,  # Case 22: JALR (无条件跳转)
        False,  # Case 23: BEQ (10 != 20，条件不成立，不跳转)
        False,  # Case 24: BNE (10 == 10，条件不成立，不跳转)
        False,  # Case 25: BLT (10 >= 5，BLT条件不成立)
        False,  # Case 26: BGE (5 < 10，BGE条件不成立)
        False,  # Case 27: BLTU (10 >= 5，BLTU条件不成立)
        False,  # Case 28: BGEU (5 < 10，BGEU条件不成立)
        False,  # Case 29: SW (无分支)
        False,  # Case 30: LW (无分支)
        False,  # Case 31: SH (无分支)
        False,  # Case 32: LH (无分支)
        False,  # Case 33: LHU (无分支)
        False,  # Case 34: LB (无分支)
        False,  # Case 35: LBU (无分支)
        False,  # Case 36: SW (无分支)
        False,  # Case 37: LW (无分支)
        False,  # Case 38: SH (无分支)
        False,  # Case 39: LH (无分支)
    ]

    # 预期SRAM操作列表
    # 根据用户反馈，SRAM在EX阶段只输入目标地址，无论读写都在下周期进行，只有MEM阶段能看到
    expected_sram_ops = [
        None,  # Case 0: ADD (无SRAM操作)
        None,  # Case 1: SUB (无SRAM操作)
        None,  # Case 2: AND (无SRAM操作)
        None,  # Case 3: OR (无SRAM操作)
        None,  # Case 4: SLL (无SRAM操作)
        None,  # Case 5: SRL (无SRAM操作)
        None,  # Case 6: SRA (无SRAM操作)
        None,  # Case 7: SLT (无SRAM操作)
        None,  # Case 8: SLTU (无SRAM操作)
        None,  # Case 9: 使用EX-MEM旁路 (无SRAM操作)
        None,  # Case 10: 使用MEM-WB旁路 (无SRAM操作)
        None,  # Case 11: 使用WB_BYPASS的ADD指令 (无SRAM操作)
        None,  # Case 12: 使用WB_BYPASS的SUB指令 (无SRAM操作)
        None,  # Case 13: 使用WB_BYPASS的AND指令 (无SRAM操作)
        None,  # Case 14: 使用WB_BYPASS的OR指令 (无SRAM操作)
        None,  # Case 15: 对比三种旁路 - ADD指令 (无SRAM操作)
        None,  # Case 16: 对比三种旁路 - SUB指令 (无SRAM操作)
        None,  # Case 17: BEQ (无SRAM操作)
        None,  # Case 18: BNE (无SRAM操作)
        None,  # Case 19: BLT (无SRAM操作)
        None,  # Case 20: BGE (无SRAM操作)
        None,  # Case 21: JAL (无SRAM操作)
        None,  # Case 22: JALR (无SRAM操作)
        None,  # Case 23: BEQ (无SRAM操作)
        None,  # Case 24: BNE (无SRAM操作)
        None,  # Case 25: BLT (无SRAM操作)
        None,  # Case 26: BGE (无SRAM操作)
        None,  # Case 27: BLTU (无SRAM操作)
        None,  # Case 28: BGEU (无SRAM操作)
        (
            "EX_STORE",
            0x1000,
            0x12345678,
        ),  # Case 29: SW (EX阶段输出地址=0x1000, MEM阶段实际存储数据=0x12345678)
        (
            "EX_STORE",
            0x1004,
            0xABCDEF00,
        ),  # Case 30: SW (EX阶段输出地址=0x1004, MEM阶段实际存储数据=0xABCDEF00)
        (
            "EX_STORE",
            0x1008,
            0x11223344,
        ),  # Case 31: SW (EX阶段输出地址=0x1008, MEM阶段实际存储数据=0x11223344)
        (
            "EX_LOAD",
            0x1000,
            0x12345678,
        ),  # Case 32: LW (EX阶段输出地址=0x1000, MEM阶段实际加载数据=0x12345678)
        (
            "EX_LOAD",
            0x1004,
            0xABCDEF00,
        ),  # Case 33: LW (EX阶段输出地址=0x1004, MEM阶段实际加载数据=0xABCDEF00)
        (
            "EX_LOAD",
            0x1008,
            0x11223344,
        ),  # Case 34: LW (EX阶段输出地址=0x1008, MEM阶段实际加载数据=0x11223344)
        (
            "EX_STORE",
            0x1001,
            0x55555555,
        ),  # Case 35: SW (EX阶段输出未对齐地址=0x1001, MEM阶段尝试存储数据=0x55555555)
        (
            "EX_LOAD",
            0x1003,
            None,
        ),  # Case 36: LW (EX阶段输出未对齐地址=0x1003, MEM阶段尝试加载数据)
        (
            "EX_STORE",
            0x1010,
            0xABCD,
        ),  # Case 37: SH (EX阶段输出地址=0x1010, MEM阶段实际存储数据=0xABCD)
        (
            "EX_LOAD",
            0x1010,
            0xABCD,
        ),  # Case 38: LH (EX阶段输出地址=0x1010, MEM阶段实际加载数据=0xABCD)
        (
            "EX_STORE",
            0x1011,
            0xEF,
        ),  # Case 39: SB (EX阶段输出地址=0x1011, MEM阶段实际存储数据=0xEF)
        (
            "EX_LOAD",
            0x1011,
            0xFFFFFFEF,
        ),  # Case 40: LB (EX阶段输出地址=0x1011, MEM阶段实际加载数据=0xFFFFFFEF)
    ]

    # 捕获实际的ALU结果
    actual_results = []
    bypass_updates = []
    branch_updates = []
    branch_types = []
    branch_taken = []
    sram_ops = []  # 捕获SRAM操作

    for line in raw_output.split("\n"):
        # 捕获ALU结果
        if "EX: ALU Result" in line:
            # 示例行: "[100] EX: ALU Result: 0x12345678"
            parts = line.split()
            for part in parts:
                if part.startswith("0x"):
                    result = int(part, 16)
                    actual_results.append(result)
                    print(f"  [捕获] ALU Result: 0x{result:08x}")
                    break

        # 捕获旁路寄存器更新
        if "EX: Bypass Update" in line:
            # 示例行: "[100] EX: Bypass Update: 0x12345678"
            parts = line.split()
            for part in parts:
                if part.startswith("0x"):
                    bypass = int(part, 16)
                    bypass_updates.append(bypass)
                    print(f"  [捕获] Bypass Update: 0x{bypass:08x}")
                    break

        # 捕获分支目标更新
        if "EX: Branch Target" in line:
            # 示例行: "[100] EX: Branch Target: 0x12345678"
            parts = line.split()
            for part in parts:
                if part.startswith("0x"):
                    target = int(part, 16)
                    branch_updates.append(target)
                    print(f"  [捕获] Branch Target: 0x{target:08x}")
                    break

        # 捕获分支类型
        if "EX: Branch Type" in line:
            # 示例行: "[100] EX: Branch Type: BEQ"
            parts = line.split()
            if len(parts) >= 5:  # 确保有足够的部分
                branch_type = parts[4]  # 获取分支类型
                branch_types.append(branch_type)
                print(f"  [捕获] Branch Type: {branch_type}")

        # 捕获分支是否跳转
        if "EX: Branch Taken" in line:
            # 示例行: "[100] EX: Branch Taken: True"
            parts = line.split()
            if len(parts) >= 5:  # 确保有足够的部分
                taken = parts[4] == "True"  # 获取分支是否跳转
                branch_taken.append(taken)
                print(f"  [捕获] Branch Taken: {taken}")

        # 捕获EX阶段SRAM地址输出
        if "SRAM: EX阶段 - we=" in line:
            # 示例行: "SRAM: EX阶段 - we=True re=False addr=0x1000 wdata=0x12345678"
            addr_match = re.search(r"addr=(0x[0-9a-fA-F]+)", line)
            data_match = re.search(r"wdata=(0x[0-9a-fA-F]+)", line)
            we_match = re.search(r"we=(True|False)", line)
            re_match = re.search(r"re=(True|False)", line)

            if addr_match and we_match and re_match:
                addr = int(addr_match.group(1), 16)
                we = we_match.group(1) == "True"
                re = re_match.group(1) == "True"
                data = int(data_match.group(1), 16) if data_match else None

                if we:
                    sram_ops.append(("EX_STORE", addr, data))
                    print(
                        f"  [捕获] EX阶段Store地址: addr=0x{addr:08x}, data=0x{data:08x if data else 0:08x}"
                    )
                elif re:
                    sram_ops.append(("EX_LOAD", addr, data))
                    print(f"  [捕获] EX阶段Load地址: addr=0x{addr:08x}")

        # 捕获MEM阶段SRAM实际操作
        if "SRAM: MEM阶段 - " in line:
            # 示例行: "SRAM: MEM阶段 - Write WORD addr=0x1000 data=0x12345678"
            if "Write" in line:
                addr_match = re.search(r"addr=(0x[0-9a-fA-F]+)", line)
                data_match = re.search(r"data=(0x[0-9a-fA-F]+)", line)
                if addr_match and data_match:
                    addr = int(addr_match.group(1), 16)
                    data = int(data_match.group(1), 16)
                    print(
                        f"  [捕获] MEM阶段实际Write: addr=0x{addr:08x}, data=0x{data:08x}"
                    )
            elif "Read" in line:
                addr_match = re.search(r"addr=(0x[0-9a-fA-F]+)", line)
                data_match = re.search(r"data=(0x[0-9a-fA-F]+)", line)
                if addr_match and data_match:
                    addr = int(addr_match.group(1), 16)
                    data = int(data_match.group(1), 16)
                    print(
                        f"  [捕获] MEM阶段实际Read: addr=0x{addr:08x}, data=0x{data:08x}"
                    )

        # 捕获SRAM未对齐访问警告
        if "SRAM: Warning - Unaligned access" in line:
            # 示例行: "SRAM: Warning - Unaligned access addr=0x1001"
            addr_match = re.search(r"addr=(0x[0-9a-fA-F]+)", line)
            if addr_match:
                addr = int(addr_match.group(1), 16)
                # 检查是Store还是Load操作
                if "we=True" in line:
                    sram_ops.append(
                        ("EX_STORE", addr, None)
                    )  # 未对齐的Store操作，数据不重要
                    print(f"  [捕获] EX阶段未对齐Store: addr=0x{addr:08x}")
                elif "re=True" in line:
                    sram_ops.append(
                        ("EX_LOAD", addr, None)
                    )  # 未对齐的Load操作，数据不重要
                    print(f"  [捕获] EX阶段未对齐Load: addr=0x{addr:08x}")

    # --- 断言比对 ---

    # 1. ALU结果数量检查
    if len(actual_results) != len(expected_results):
        print(
            f"❌ 错误：预期ALU结果 {len(expected_results)} 个，实际捕获 {len(actual_results)} 个"
        )
        assert False

    # 2. ALU结果内容检查
    for i, (exp_result, act_result) in enumerate(zip(expected_results, actual_results)):
        if exp_result != act_result:
            print(f"❌ 错误：第 {i} 个ALU结果不匹配")
            print(f"  预期: 0x{exp_result:08x}")
            print(f"  实际: 0x{act_result:08x}")
            assert False

    # 3. 旁路寄存器更新检查 (每个测试用例都会更新旁路寄存器)
    if len(bypass_updates) != len(expected_results):
        print(
            f"❌ 错误：预期旁路更新 {len(expected_results)} 次，实际更新 {len(bypass_updates)} 次"
        )
        assert False

    # 4. 分支类型检查
    if len(branch_types) != len(expected_branch_types):
        print(
            f"❌ 错误：预期分支类型 {len(expected_branch_types)} 个，实际捕获 {len(branch_types)} 个"
        )
        assert False

    # 5. 分支类型内容检查
    for i, (exp_type, act_type) in enumerate(zip(expected_branch_types, branch_types)):
        if exp_type != act_type:
            print(f"❌ 错误：第 {i} 个分支类型不匹配")
            print(f"  预期: {exp_type}")
            print(f"  实际: {act_type}")
            assert False

    # 6. 分支目标更新检查 (只有分支指令会更新分支目标寄存器)
    # 过滤掉None值，只检查实际有分支目标的情况
    expected_targets = [
        target for target in expected_branch_targets if target is not None
    ]
    if len(branch_updates) != len(expected_targets):
        print(
            f"❌ 错误：预期分支目标更新 {len(expected_targets)} 次，实际更新 {len(branch_updates)} 次"
        )
        print(f"  预期分支目标: {[hex(t) for t in expected_targets]}")
        print(f"  实际分支目标: {[hex(t) for t in branch_updates]}")
        assert False

    # 7. 分支目标内容检查
    branch_target_idx = 0
    for i, target in enumerate(expected_branch_targets):
        if target is not None:  # 只检查有分支目标的情况
            if target != branch_updates[branch_target_idx]:
                print(f"❌ 错误：第 {i} 个分支目标不匹配")
                print(f"  预期: 0x{target:08x}")
                print(f"  实际: 0x{branch_updates[branch_target_idx]:08x}")
                assert False
            branch_target_idx += 1

    # 8. 分支是否跳转检查
    if len(branch_taken) != len(expected_branch_taken):
        print(
            f"❌ 错误：预期分支跳转状态 {len(expected_branch_taken)} 个，实际捕获 {len(branch_taken)} 个"
        )
        assert False

    # 9. 分支跳转状态内容检查
    for i, (exp_taken, act_taken) in enumerate(
        zip(expected_branch_taken, branch_taken)
    ):
        if exp_taken != act_taken:
            print(f"❌ 错误：第 {i} 个分支跳转状态不匹配")
            print(f"  预期: {exp_taken}")
            print(f"  实际: {act_taken}")
            assert False

    # 10. branch_target_reg状态检查
    # 根据用户反馈，对于分支指令，检验方法的关键在branch_target_reg是否随预测成功为0且失败时有值
    # 捕获branch_target_reg的值
    branch_target_reg_values = []
    for line in raw_output.split("\n"):
        if "Sink: 检验branch_target_reg - value=" in line:
            # 示例行: "Sink: 检验branch_target_reg - value=0x12345678"
            value_match = re.search(r"value=(0x[0-9a-fA-F]+)", line)
            if value_match:
                value = int(value_match.group(1), 16)
                branch_target_reg_values.append(value)
                print(f"  [捕获] branch_target_reg值: 0x{value:08x}")

    # 检查branch_target_reg的值是否正确反映预测成功/失败状态
    expected_branch_target_reg_values = []
    for i, taken in enumerate(expected_branch_taken):
        if expected_branch_types[i] == "NO_BRANCH":
            # 非分支指令，branch_target_reg应该为0
            expected_branch_target_reg_values.append(0)
        else:
            # 分支指令
            if taken:
                # 预测成功，branch_target_reg应该为0
                expected_branch_target_reg_values.append(0)
            else:
                # 预测失败，branch_target_reg应该有值（目标地址）
                expected_branch_target_reg_values.append(expected_branch_targets[i])

    # 验证branch_target_reg的值
    if len(branch_target_reg_values) != len(expected_branch_target_reg_values):
        print(
            f"❌ 错误：预期branch_target_reg值 {len(expected_branch_target_reg_values)} 个，实际捕获 {len(branch_target_reg_values)} 个"
        )
        assert False

    for i, (exp_value, act_value) in enumerate(
        zip(expected_branch_target_reg_values, branch_target_reg_values)
    ):
        if exp_value != act_value:
            print(f"❌ 错误：第 {i} 个branch_target_reg值不匹配")
            print(f"  预期: 0x{exp_value:08x}")
            print(f"  实际: 0x{act_value:08x}")
            print(f"  分支类型: {expected_branch_types[i]}")
            print(f"  预期跳转: {expected_branch_taken[i]}")
            assert False

    # 11. SRAM操作检查
    # 过滤掉None值，只检查实际有SRAM操作的情况
    expected_sram_filtered = [op for op in expected_sram_ops if op is not None]
    if len(sram_ops) != len(expected_sram_filtered):
        print(
            f"❌ 错误：预期SRAM操作 {len(expected_sram_filtered)} 次，实际操作 {len(sram_ops)} 次"
        )
        print(f"  预期SRAM操作: {expected_sram_filtered}")
        print(f"  实际SRAM操作: {sram_ops}")
        assert False

    # 12. SRAM操作内容检查
    sram_op_idx = 0
    for i, sram_op in enumerate(expected_sram_ops):
        if sram_op is not None:  # 只检查有SRAM操作的情况
            exp_type, exp_addr, exp_data = sram_op
            act_type, act_addr, act_data = sram_ops[sram_op_idx]

        # 检查操作类型
        if exp_type != act_type:
            print(f"❌ 错误：第 {i} 个SRAM操作类型不匹配")
            print(f"  预期: {exp_type}")
            print(f"  实际: {act_type}")
            assert False

        # 检查地址
        if exp_addr != act_addr:
            print(f"❌ 错误：第 {i} 个SRAM操作地址不匹配")
            print(f"  预期: 0x{exp_addr:08x}")
            print(f"  实际: 0x{act_addr:08x}")
            assert False

        # 对于未对齐访问，只检查操作类型和地址，不检查数据
        if exp_data is not None and act_data is not None:
            if exp_data != act_data:
                print(f"❌ 错误：第 {i} 个SRAM操作数据不匹配")
                print(f"  预期: 0x{exp_data:08x}")
                print(f"  实际: 0x{act_data:08x}")
                assert False

        sram_op_idx += 1

    print("✅ EX模块测试通过！(所有ALU操作、分支指令、旁路功能和SRAM操作均正确)")
    print("✅ branch_target_reg正确反映了预测成功/失败状态")
    print("✅ EX阶段正确输出地址而非结果，MEM阶段正确处理内存操作")
    print("✅ WB_BYPASS功能正常工作，能够正确从写回阶段旁路数据到执行阶段")


# ==============================================================================
# 4. 主执行入口
# ==============================================================================
if __name__ == "__main__":
    sys = SysBuilder("test_execute_module")

    with sys:
        # 创建测试模块
        dut = Execution()
        driver = Driver()

        # 创建Mock模块
        mock_sram = MockSRAM()
        mock_feedback = MockFeedback()

        # 创建旁路寄存器和分支目标寄存器
        ex_mem_bypass = RegArray(Bits(32), 1)
        mem_wb_bypass = RegArray(Bits(32), 1)
        wb_bypass = RegArray(Bits(32), 1)
        branch_target_reg = RegArray(Bits(32), 1)

        # 创建一个虚拟的MEM模块，只用于接收EX的输出，不进行实际处理
        class MockMEM(Module):
            def __init__(self):
                # 定义与 MEM 模块一致的输入端口
                super().__init__(
                    ports={"ctrl": Port(mem_ctrl_signals), "alu_result": Port(Bits(32))}
                )
                self.name = "MockMEM"

            @module.combinational
            def build(self):
                # 接收并打印
                ctrl, res = self.pop_all_ports(False)
                # 打印有效数据
                # 这里可以验证 EX 算出的结果
                log("[MEM_Sink] Recv: ALU_Res=0x{:x} Is_Load={}", res, ctrl.is_load)
                # 更新MEM-WB旁路寄存器
                mem_wb_bypass[0] = res

        # 创建虚拟的MEM模块
        mock_mem_module = MockMEM()

        # [关键] 获取 Driver 的返回值
        driver_cnt, driver_expected = driver.build(
            dut,
            mock_mem_module,
            ex_mem_bypass,
            mem_wb_bypass,
            wb_bypass,
            branch_target_reg,
        )

        # 调用Execution模块，传入所有必要的参数
        dut.build(
            mem_module=mock_mem_module,
            ex_mem_bypass=ex_mem_bypass,
            mem_wb_bypass=mem_wb_bypass,
            wb_bypass=wb_bypass,
            branch_target_reg=branch_target_reg,
            dcache=mock_sram,
        )

        # 调用MockFeedback模块，检查旁路寄存器和分支目标寄存器的值
        mock_feedback.build(branch_target_reg, ex_mem_bypass)

    run_test_module(sys, check)
