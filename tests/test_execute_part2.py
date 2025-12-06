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
from tests.test_mocks import MockSRAM, MockMEM, MockFeedback, check_alu_results, check_bypass_updates, check_branch_operations, check_branch_target_reg


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
        vectors = [
            # --- 旁路测试 ---
            # Case 0: 使用EX-MEM旁路数据
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
            # Case 1: 使用MEM-WB旁路数据
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
            # Case 2: 使用WB_BYPASS的ADD指令
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
            # Case 3: 使用WB_BYPASS的SUB指令
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
            # Case 4: 使用WB_BYPASS的AND指令
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
            # Case 5: 使用WB_BYPASS的OR指令
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
            # Case 6: 对比三种旁路 - ADD指令
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
            # Case 7: 对比三种旁路 - SUB指令
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
            # Case 8: BEQ (相等分支)
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
            # Case 9: BNE (不等分支)
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
            # Case 10: BLT (小于分支)
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
            # Case 11: BGE (大于等于分支)
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
            # Case 12: BLTU (无符号小于分支)
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
            # Case 13: BGEU (无符号大于等于分支)
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
            # --- JAL/JALR 指令测试 ---
            # Case 14: JAL (直接跳转)
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
            # Case 15: JALR (间接跳转)
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
        mem_ctrl = mem_ctrl_signals.bundle(
            mem_opcode=MemOp.NONE,  # 第二部分测试不涉及内存操作
            mem_width=MemWidth.WORD,
            mem_unsigned=MemSign.UNSIGNED,
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
# 2. 验证逻辑 (Python Check)
# ==============================================================================
def check(raw_output):
    print(">>> 开始验证EX模块输出（第二部分：旁路和分支指令测试）...")

    # 预期结果列表 (必须与Driver中的vectors严格对应)
    expected_results = [
        0x00000078,  # Case 0: 使用EX-MEM旁路 (100+20=120)
        0x000000DC,  # Case 1: 使用MEM-WB旁路 (200+20=220)
        0x00000140,  # Case 2: 使用WB_BYPASS的ADD指令 (300+20=320)
        0x00000122,  # Case 3: 使用WB_BYPASS的SUB指令 (300-10=290)
        0x01040408,  # Case 4: 使用WB_BYPASS的AND指令 (0x12345678 & 0x0F0F0F0F = 0x01040408)
        0x1B3F5F7F,  # Case 5: 使用WB_BYPASS的OR指令 (0x12345678 | 0x0F0F0F0F = 0x1B3F5F7F)
        0x0000012C,  # Case 6: 对比三种旁路 - ADD指令 (100+200=300)
        0x00000064,  # Case 7: 对比三种旁路 - SUB指令 (200-100=100)
        0x00000000,  # Case 8: BEQ (10-10=0)
        0xFFFFFFFE,  # Case 9: BNE (10-20=-10)
        0x00000001,  # Case 10: BLT (5<10=1)
        0x00000000,  # Case 11: BGE (10>=5=0)
        0x00000000,  # Case 12: BLTU (10>=5=0, 无符号比较)
        0x00000001,  # Case 13: BGEU (5<10=1, 无符号比较)
        0x00001004,  # Case 14: JAL (PC+4=0x1004)
        0x00001004,  # Case 15: JALR (PC+4=0x1004)
    ]

    # 预期分支类型列表 (必须与Driver中的vectors严格对应)
    expected_branch_types = [
        "NO_BRANCH",  # Case 0: 使用EX-MEM旁路
        "NO_BRANCH",  # Case 1: 使用MEM-WB旁路
        "NO_BRANCH",  # Case 2: 使用WB_BYPASS的ADD指令
        "NO_BRANCH",  # Case 3: 使用WB_BYPASS的SUB指令
        "NO_BRANCH",  # Case 4: 使用WB_BYPASS的AND指令
        "NO_BRANCH",  # Case 5: 使用WB_BYPASS的OR指令
        "NO_BRANCH",  # Case 6: 对比三种旁路 - ADD指令
        "NO_BRANCH",  # Case 7: 对比三种旁路 - SUB指令
        "BEQ",  # Case 8: BEQ (相等分支)
        "BNE",  # Case 9: BNE (不等分支)
        "BLT",  # Case 10: BLT (小于分支)
        "BGE",  # Case 11: BGE (大于等于分支)
        "BLTU",  # Case 12: BLTU (无符号小于分支)
        "BGEU",  # Case 13: BGEU (无符号大于等于分支)
        "JAL",  # Case 14: JAL (直接跳转)
        "JALR",  # Case 15: JALR (间接跳转)
    ]

    # 预期分支目标地址列表 (只有分支指令会更新分支目标寄存器)
    expected_branch_targets = [
        None,  # Case 0: 使用EX-MEM旁路 (无分支)
        None,  # Case 1: 使用MEM-WB旁路 (无分支)
        None,  # Case 2: 使用WB_BYPASS的ADD指令 (无分支)
        None,  # Case 3: 使用WB_BYPASS的SUB指令 (无分支)
        None,  # Case 4: 使用WB_BYPASS的AND指令 (无分支)
        None,  # Case 5: 使用WB_BYPASS的OR指令 (无分支)
        None,  # Case 6: 对比三种旁路 - ADD指令 (无分支)
        None,  # Case 7: 对比三种旁路 - SUB指令 (无分支)
        0x1008,  # Case 8: BEQ (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 9: BNE (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 10: BLT (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 11: BGE (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 12: BLTU (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 13: BGEU (PC + 8 = 0x1000 + 8 = 0x1008)
        0x1008,  # Case 14: JAL (PC + 8 = 0x1000 + 8 = 0x1008)
        0x2008,  # Case 15: JALR (rs1 + imm = 0x2000 + 8 = 0x2008)
    ]

    # 预期分支是否跳转列表
    expected_branch_taken = [
        False,  # Case 0: 使用EX-MEM旁路 (无分支)
        False,  # Case 1: 使用MEM-WB旁路 (无分支)
        False,  # Case 2: 使用WB_BYPASS的ADD指令 (无分支)
        False,  # Case 3: 使用WB_BYPASS的SUB指令 (无分支)
        False,  # Case 4: 使用WB_BYPASS的AND指令 (无分支)
        False,  # Case 5: 使用WB_BYPASS的OR指令 (无分支)
        False,  # Case 6: 对比三种旁路 - ADD指令 (无分支)
        False,  # Case 7: 对比三种旁路 - SUB指令 (无分支)
        True,   # Case 8: BEQ (10 == 10，条件成立，跳转)
        True,   # Case 9: BNE (10 != 20，条件成立，跳转)
        True,   # Case 10: BLT (5 < 10，条件成立，跳转)
        True,   # Case 11: BGE (10 >= 5，条件成立，跳转)
        False,  # Case 12: BLTU (10 >= 5，BLTU条件不成立)
        False,  # Case 13: BGEU (5 < 10，BGEU条件不成立)
        True,   # Case 14: JAL (无条件跳转)
        True,   # Case 15: JALR (无条件跳转)
    ]

    # 使用公共验证函数
    check_alu_results(raw_output, expected_results)
    check_bypass_updates(raw_output, expected_results)
    check_branch_operations(raw_output, expected_branch_types, expected_branch_targets, expected_branch_taken)
    check_branch_target_reg(raw_output, expected_branch_types, expected_branch_targets, expected_branch_taken)

    print("✅ EX模块第二部分测试通过！（旁路功能和分支指令均正确）")
    print("✅ branch_target_reg正确反映了预测成功/失败状态")


# ==============================================================================
# 4. 主执行入口
# ==============================================================================
if __name__ == "__main__":
    sys = SysBuilder("test_execute_module_part2")

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