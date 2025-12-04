import warnings
warnings.filterwarnings("ignore")

import sys
import os
import io
import contextlib
from typing import Tuple, Optional

lib_path = os.path.abspath(os.path.join(os.path.dirname("driver.qmd"), '../python/'))
sys.path.append(lib_path)
from function_t import run_quietly

from assassyn.frontend import *
from assassyn.backend import elaborate
from assassyn import utils

class Driver(Module):
    def __init__(self):
        super().__init__(ports={})

    @module.combinational
    def build(self):
        cnt = RegArray(UInt(32), 1)

        v = cnt[0] + UInt(32)(1)
        (cnt & self)[0] <= v

        log('cnt: {}', cnt[0])

print("✅ 计数器模块定义完成")

print("开始构建和仿真...")

# 1. 构建系统
sys = SysBuilder('driver')
with sys:
    driver = Driver()
    driver.build()
print(sys)
# 2. 生成仿真器
def generate_simulator():
    return elaborate(sys, verilog=utils.has_verilator())

(simulator_path, verilator_path), _, _ = run_quietly(generate_simulator)
print("✅ 仿真器生成完成")

# 3. 运行仿真器
def run_sim():
    return utils.run_simulator(simulator_path)

raw, _, _ = run_quietly(run_sim)

print("\n=== 模拟器输出 ===")
# 只显示计数器的值
for line in raw.split('\n'):
    if 'cnt:' in line:
        print(line.strip())

# 验证输出
check(raw)

# 如果有 Verilator，也运行 Verilator 验证
if verilator_path:
    print("\n=== Verilator 验证 ===")

    def run_verilator():
        return utils.run_verilator(verilator_path)

    raw_verilator, _, _ = run_quietly(run_verilator)

    # 显示 Verilator 的计数器输出
    for line in raw_verilator.split('\n'):
        if 'cnt:' in line:
            print(line.strip())

    # 验证 Verilator 的输出
    check(raw_verilator)
else:
    print("⚠️ Verilator 未安装，跳过 Verilator 验证")