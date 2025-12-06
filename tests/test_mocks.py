import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from assassyn.frontend import *
from src.control_signals import *

# ==============================================================================
# 公共Mock模块定义
# ==============================================================================


# [修改 1] 去掉 (Module) 继承
class MockSRAM:
    def __init__(self):
        # [修改 2] 去掉 super().__init__，因为它不是 Module 了
        # self.dout = ... 可以保留，它会被归属到调用者 (EX) 名下
        self.dout = RegArray(Bits(32), 1)

    # [修改 3] 去掉装饰器 (因为它不是 Module 的入口了)
    # @module.combinational  <-- 删掉
    def build(self, we, re, addr, wdata):

        # 打印基本信息
        with Condition(we):
            log("SRAM: EX阶段 - WRITE addr=0x{:x} wdata=0x{:x}", addr, wdata)

            # 检查对齐
            is_unaligned = addr[0:1] != Bits(2)(0)
            with Condition(is_unaligned):
                log("SRAM: Warning - Unaligned WRITE addr=0x{:x}", addr)

        with Condition(re):
            log("SRAM: EX阶段 - READ addr=0x{:x}", addr)

            # 检查对齐
            is_unaligned = addr[0:1] != Bits(2)(0)
            with Condition(is_unaligned):
                log("SRAM: Warning - Unaligned READ addr=0x{:x}", addr)


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
        log(
            "[MEM_Sink] Recv: ALU_Res=0x{:x} Is_Load={}",
            res,
            ctrl.mem_opcode == MemOp.LOAD,
        )


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


# ==============================================================================
# 公共验证函数
# ==============================================================================


def check_alu_results(raw_output, expected_results, test_name="ALU"):
    """验证ALU结果的通用函数"""
    print(f">>> 开始验证{test_name}模块输出...")

    # 捕获实际的ALU结果
    actual_results = []

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

    # ALU结果数量检查
    if len(actual_results) != len(expected_results):
        print(
            f"❌ 错误：预期ALU结果 {len(expected_results)} 个，实际捕获 {len(actual_results)} 个"
        )
        assert False

    # ALU结果内容检查
    for i, (exp_result, act_result) in enumerate(zip(expected_results, actual_results)):
        if exp_result != act_result:
            print(f"❌ 错误：第 {i} 个ALU结果不匹配")
            print(f"  预期: 0x{exp_result:08x}")
            print(f"  实际: 0x{act_result:08x}")
            assert False

    print(f"✅ {test_name}模块测试通过！(所有ALU操作均正确)")


def check_bypass_updates(raw_output, expected_results):
    """验证旁路寄存器更新的通用函数"""
    # 捕获旁路寄存器更新
    bypass_updates = []

    for line in raw_output.split("\n"):
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

    # 旁路寄存器更新检查 (每个测试用例都会更新旁路寄存器)
    if len(bypass_updates) != len(expected_results):
        print(
            f"❌ 错误：预期旁路更新 {len(expected_results)} 次，实际更新 {len(bypass_updates)} 次"
        )
        assert False

    print("✅ 旁路寄存器更新测试通过！")


def check_branch_operations(
    raw_output, expected_branch_types, expected_branch_taken, expected_branch_targets
):
    """验证分支操作的通用函数"""
    # 捕获分支类型
    branch_types = []
    branch_taken = []
    branch_updates = []

    for line in raw_output.split("\n"):
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

    # 分支类型检查
    if len(branch_types) != len(expected_branch_types):
        print(
            f"❌ 错误：预期分支类型 {len(expected_branch_types)} 个，实际捕获 {len(branch_types)} 个"
        )
        assert False

    # 分支类型内容检查
    for i, (exp_type, act_type) in enumerate(zip(expected_branch_types, branch_types)):
        if exp_type != act_type:
            print(f"❌ 错误：第 {i} 个分支类型不匹配")
            print(f"  预期: {exp_type}")
            print(f"  实际: {act_type}")
            assert False

    # 分支是否跳转检查
    if len(branch_taken) != len(expected_branch_taken):
        print(
            f"❌ 错误：预期分支跳转状态 {len(expected_branch_taken)} 个，实际捕获 {len(branch_taken)} 个"
        )
        assert False

    # 分支跳转状态内容检查
    for i, (exp_taken, act_taken) in enumerate(
        zip(expected_branch_taken, branch_taken)
    ):
        if exp_taken != act_taken:
            print(f"❌ 错误：第 {i} 个分支跳转状态不匹配")
            print(f"  预期: {exp_taken}")
            print(f"  实际: {act_taken}")
            assert False

    # 分支目标更新检查 (只有分支指令会更新分支目标寄存器)
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

    # 分支目标内容检查
    branch_target_idx = 0
    for i, target in enumerate(expected_branch_targets):
        if target is not None:  # 只检查有分支目标的情况
            if target != branch_updates[branch_target_idx]:
                print(f"❌ 错误：第 {i} 个分支目标不匹配")
                print(f"  预期: 0x{target:08x}")
                print(f"  实际: 0x{branch_updates[branch_target_idx]:08x}")
                assert False
            branch_target_idx += 1

    print("✅ 分支指令测试通过！")


def check_branch_target_reg(
    raw_output, expected_branch_types, expected_branch_taken, expected_branch_targets
):
    """验证branch_target_reg的通用函数"""
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

    print("✅ branch_target_reg正确反映了预测成功/失败状态")


def check_sram_operations(raw_output, expected_sram_ops):
    """验证SRAM操作的通用函数"""
    sram_ops = []  # 捕获SRAM操作

    for line in raw_output.split("\n"):
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

    # SRAM操作检查
    # 过滤掉None值，只检查实际有SRAM操作的情况
    expected_sram_filtered = [op for op in expected_sram_ops if op is not None]
    if len(sram_ops) != len(expected_sram_filtered):
        print(
            f"❌ 错误：预期SRAM操作 {len(expected_sram_filtered)} 次，实际操作 {len(sram_ops)} 次"
        )
        print(f"  预期SRAM操作: {expected_sram_filtered}")
        print(f"  实际SRAM操作: {sram_ops}")
        assert False

    # SRAM操作内容检查
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

    print("✅ SRAM操作测试通过！")
    print("✅ EX阶段正确输出地址而非结果，MEM阶段正确处理内存操作")
