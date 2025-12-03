import sys
import os

# 添加MyCPU目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.writeback import WriteBack, wb_ctrl_t
from tests.common import run_test_module
from assassyn.frontend import *
from assassyn.backend import elaborate
from assassyn import utils

class WBDriver(Module):
    """模拟上游模块发送测试数据"""
    
    def __init__(self):
        super().__init__()
        self.name = 'WBDriver'
    
    @module.combinational
    def build(self):
        # 构造测试数据包，包含不同的rd_addr和wdata
        test_cases = [
            (1, 0x12345678),  # 正常写回操作（非零寄存器）
            (5, 0xABCDEF00),  # 正常写回操作（非零寄存器）
            (0, 0xDEADBEEF),  # 零寄存器写回保护（不执行写回）
            (10, 0x11111111), # 正常写回操作（非零寄存器）
            (0, 0x00000000),  # 零寄存器写回保护（不执行写回）
            (15, 0x22222222)  # 正常写回操作（非零寄存器）
        ]
        
        # 创建计数器来跟踪测试用例
        test_counter = RegArray(Bits(3), 1, initializer=[0])
        
        # 根据计数器值选择测试用例
        current_test = test_counter[0]
        
        # 创建当前测试用例的控制信号和数据
        current_ctrl = Bits(5)(0)
        current_wdata = Bits(32)(0)
        
        # 使用条件语句选择当前测试用例
        for i, (rd_addr, wdata) in enumerate(test_cases):
            with Condition(current_test == Bits(3)(i)):
                current_ctrl = Bits(5)(rd_addr)
                current_wdata = Bits(32)(wdata)
                log("WBDriver: Sending test case - rd_addr={}, wdata=0x{:x}", rd_addr, wdata)
        
        # 更新计数器
        with Condition(test_counter[0] < Bits(3)(len(test_cases) - 1)):
            test_counter[0] <= test_counter[0] + Bits(3)(1)
        
        # 返回测试数据
        # 注意：这里需要返回Record类型，而不是单独的Bits
        ctrl = wb_ctrl_t()
        ctrl.rd_addr = current_ctrl
        return ctrl, current_wdata

class WriteBackTester(Module):
    """WriteBack测试器，负责连接所有模块并运行测试"""
    
    def __init__(self):
        super().__init__()
        self.name = 'WriteBackTester'
    
    @module.combinational
    def build(self):
        # 创建寄存器堆
        reg_file = RegArray(Bits(32), 32)
        
        # 实例化WriteBack模块
        wb_module = WriteBack()
        
        # 实例化WBDriver
        wb_driver = WBDriver()
        
        # 构建WBDriver
        wb_driver.build()
        
        # 使用async_called连接WBDriver到WriteBack
        wb_call = wb_module.async_called(
            ctrl=wb_ctrl_t(),
            wdata=Bits(32)(0)
        )
        wb_call.bind.set_fifo_depth(ctrl=2, wdata=2)
        
        # 构建WriteBack模块，传入寄存器堆
        wb_rd = wb_module.build(reg_file)
        
        # 记录写回的寄存器地址
        log("WriteBack: rd_addr={}", wb_rd)

def check(raw_output):
    """验证仿真输出"""
    # 检查日志中是否包含预期的写回操作
    output_lines = raw_output.split('\n')
    
    # 统计写回操作
    writeback_ops = []
    driver_sends = []
    
    for line in output_lines:
        if "WB: Write x" in line:
            # 提取写回操作信息
            parts = line.split()
            reg_num = int(parts[2][1:])  # 去掉'x'
            data = parts[4][:-1]  # 去掉结尾的','
            writeback_ops.append((reg_num, data))
        elif "WBDriver: Sending test case" in line:
            # 提取发送的测试用例
            parts = line.split()
            rd_addr = int(parts[4].split('=')[1].rstrip(','))
            wdata = parts[6][:-1]  # 去掉结尾的'}'
            driver_sends.append((rd_addr, wdata))
    
    # 验证非零寄存器的写回操作
    expected_non_zero_writes = [(1, "0x12345678"), (5, "0xabcdef00"), (10, "0x11111111"), (15, "0x22222222")]
    
    for reg_num, data in expected_non_zero_writes:
        found = False
        for op_reg, op_data in writeback_ops:
            if op_reg == reg_num and op_data.lower() == data.lower():
                found = True
                break
        assert found, f"Expected writeback to x{reg_num} with data {data} not found"
    
    # 验证零寄存器(x0)不会执行写回操作
    for op_reg, _ in writeback_ops:
        assert op_reg != 0, f"Unexpected writeback to zero register (x0) found"
    
    # 验证有足够的写回操作
    assert len(writeback_ops) == len(expected_non_zero_writes), \
        f"Expected {len(expected_non_zero_writes)} writeback operations, got {len(writeback_ops)}"

def main():
    """主函数，创建并运行测试"""
    # 创建SysBuilder实例
    sys_builder = SysBuilder("test_writeback")
    
    with sys_builder:
        # 实例化WriteBackTester
        tester = WriteBackTester()
        tester.build()
    
    # 调用run_test_module运行测试
    run_test_module(sys_builder, check, cycles=200)

if __name__ == "__main__":
    main()