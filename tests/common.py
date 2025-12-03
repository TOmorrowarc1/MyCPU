from assassyn.frontend import *
from assassyn.backend import elaborate, config
from assassyn import utils
import os

# [修复] 移除 cycles 参数，改用 config 控制
def run_test_module(sys_builder, check_func):
    print(f"🚀 Compiling system: {sys_builder.name}...")
    
    # 1. 配置仿真参数
    # 参考 minor_cpu: 使用 config 对象控制仿真阈值
    cfg = config(
        verilog=False,          # 单元测试不需要生成 Verilog
        sim_threshold=1000,     # 最大仿真周期数 (替代 cycles 参数)
        idle_threshold=100      # 空闲检测阈值
    )

    # 2. 生成仿真器源码 (Elaborate)
    # elaborate 返回的是一个包含路径的元组/列表
    ret = elaborate(sys_builder, **cfg)
    
    # [关键修复]: 安全解包路径
    # 无论返回 (sim, ver) 还是 [sim, ver]，我们都强制取第一个元素
    if isinstance(ret, (tuple, list)):
        sim_source_path = ret[0]
    else:
        sim_source_path = ret
        
    # 确保路径是绝对路径字符串，避免 pathlib.PosixPath 导致的兼容性问题
    sim_source_path = str(os.path.abspath(sim_source_path))

    print(f"🔨 Building binary from: {sim_source_path}")

    # 3. [新增步骤] 显式编译二进制文件
    # 参考 minor_cpu: 先 build_simulator，再 run
    # 这一步会调用 cargo build，生成可执行文件
    try:
        binary_path = utils.build_simulator(sim_source_path)
    except Exception as e:
        print(f"❌ Simulator build failed: {e}")
        raise e

    print(f"🏃 Running simulation...")
    
    # 4. 运行二进制文件
    # 此时传入的是确定的二进制文件路径，不再依赖 cargo run 的动态行为
    try:
        # run_simulator(binary_path) 是最稳健的调用方式
        raw_output = utils.run_simulator(binary_path=binary_path)
    except Exception as e:
        print(f"❌ Simulation execution failed: {e}")
        raise e

    print("🔍 Verifying output...")
    try:
        check_func(raw_output)
        print(f"✅ {sys_builder.name} Passed!")
    except AssertionError as e:
        print(f"❌ {sys_builder.name} Failed: {e}")
        # 调试时可打开下行查看日志
        print(raw_output)
        raise e