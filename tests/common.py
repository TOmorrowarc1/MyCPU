from assassyn.frontend import *
from assassyn.backend import elaborate
from assassyn import utils

# 通用仿真运行器
def run_test_module(sys_builder, check_func, cycles=100):
    print(f"🚀 Compiling system: {sys_builder.name}...")
    # 编译
    sim_path, _ = elaborate(sys_builder, verilog=False) # 仅生成二进制用于快速测试
    # 运行
    print(f"🏃 Running simulation ({cycles} cycles)...")
    raw_output = utils.run_simulator(sim_path, cycles=cycles)
    # 验证
    print("🔍 Verifying output...")
    try:
        check_func(raw_output)
        print(f"✅ {sys_builder.name} Passed!")
    except AssertionError as e:
        print(f"❌ {sys_builder.name} Failed: {e}")
        # print(raw_output) # 出错时打印完整日志

# 基础 Mock 模块：用于模拟上下游
class MockModule(Module):
    def __init__(self, ports):
        super().__init__(ports=ports)
    
    @module.combinational
    def build(self):
        # 简单地消耗掉所有输入，防止 FIFO 堵塞
        self.pop_all_ports(False)