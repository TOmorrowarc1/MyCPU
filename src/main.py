import os
import shutil

from assassyn.frontend import *
from assassyn.backend import elaborate, config
from assassyn import utils

# 导入所有模块
from .control_signals import *
from .fetch import Fetcher, FetcherImpl
from .decoder import Decoder, DecoderImpl
from .hazard_unit import HazardUnit
from .execution import Execution
from .memory import MemoryAccess, SingleMemory
from .writeback import WriteBack
from .btb import BTB, BTBImpl
from .CSRs import CSRsUnit

# 全局工作区路径
current_path = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.join(current_path, ".workspace")


# 复制文件进入当前目录下指定路径（沙盒）
def load_test_case(case_name, source_subdir="workloads"):
    # =========================================================
    # 1. 路径计算 (使用绝对路径解决 Apptainer/挂载问题)
    # =========================================================

    # 获取当前脚本 (src/main.py) 的绝对路径
    current_file_path = os.path.abspath(__file__)
    # 获取 src 目录
    src_dir = os.path.dirname(current_file_path)
    # 获取项目根目录 (假设 src 的上一级是项目根目录)
    project_root = os.path.dirname(src_dir)

    # 构造源文件目录: .../MyCPU/workloads
    source_dir = os.path.join(project_root, source_subdir)

    # 构造沙盒目录: .../MyCPU/src/workspace
    workspace_dir = os.path.join(src_dir, ".workspace")

    print(f"[*] Source Dir: {source_dir}")
    print(f"[*] Workspace : {workspace_dir}")

    # =========================================================
    # 2. 环境清理 (沙盒重置)
    # =========================================================
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir)  # 暴力删除旧目录
    os.makedirs(workspace_dir)  # 重建空目录

    # =========================================================
    # 3. 文件搬运 (Copy & Rename)
    # =========================================================

    # 定义源文件名
    src_exe = os.path.join(source_dir, f"{case_name}.exe")

    # 定义目标文件名
    dst_RAM = os.path.join(workspace_dir, f"workload.exe")

    # --- 复制 RAM 文件 (.exe) -> cache ---
    if os.path.exists(src_exe):
        shutil.copy(src_exe, dst_RAM)
        print(f"  -> Copied Instruction: {case_name}.exe ==> workload.exe")
    else:
        # 如果找不到源文件，抛出错误（因为指令文件是必须的）
        raise FileNotFoundError(f"Test case not found: {src_exe}")


class Driver(Module):
    def __init__(self):
        super().__init__(ports={})

    @module.combinational
    def build(self, fetcher: Module):
        fetcher.async_called()


def build_cpu(depth_log):
    sys_name = "rv32i_cpu"
    sys = SysBuilder(sys_name)

    RAM_path = os.path.join(workspace, f"workload.exe")
    print(f"[*] Ins Path: {RAM_path}")

    with sys:
        # 1. 物理资源初始化
        cache = SRAM(width=32, depth=1 << depth_log, init_file=RAM_path)
        cache.name = "cache"

        # 寄存器堆
        reg_file = RegArray(Bits(32), 32)

        # 全局状态寄存器
        branch_target_reg = RegArray(Bits(32), 1)
        wb_bypass_reg = RegArray(Bits(32), 1)
        ex_bypass_reg = RegArray(Bits(32), 1)
        mem_bypass_reg = RegArray(Bits(32), 1)

        # CSR 寄存器
        # Current_Mode: 当前权限模式 (2位，合法值为 00: U-mode 与 11: M-mode)
        current_mode_reg = RegArray(Bits(2), 1, initializer=[0b00])
        # misa (0x301): 只读，硬连线为 0x40000100 (RV32I)
        misa_reg = RegArray(Bits(32), 1, initializer=[0x40000100])
        # mstatus (0x300): 当前处理器状态，包含 MPP、MPIE、MIE 等字段
        mstatus_reg = RegArray(Bits(32), 1)
        # mie (0x304): Machine Interrupt Enable，包含 MEIE、MTIE、MSIE 字段
        mie_reg = RegArray(Bits(32), 1)
        # mip (0x344): Machine Interrupt Pending，包含 MEIP、MTIP、MSIP 字段
        mip_reg = RegArray(Bits(32), 1)
        # mtvec (0x305): Trap 向量基地址与模式
        mtvec_reg = RegArray(Bits(32), 1)
        # mepc (0x341): Trap 发生时保存 PC
        mepc_reg = RegArray(Bits(32), 1)
        # mcause (0x342): Trap 发生时保存原因
        mcause_reg = RegArray(Bits(32), 1)
        # mtval (0x343): Trap 发生时保存附加信息
        mtval_reg = RegArray(Bits(32), 1)
        # mtscratch (0x340): 可读写，任意用途寄存器
        mtscratch_reg = RegArray(Bits(32), 1)

        # CSR 全局状态寄存器
        flush_all_pc = RegArray(Bits(32), 1)
        csr_wb_bypass_reg = RegArray(Bits(32), 1)
        csr_mem_bypass_reg = RegArray(Bits(32), 1)
        csr_ex_bypass_reg = RegArray(Bits(32), 1)

        # 2. 模块实例化
        fetcher = Fetcher()
        fetcher_impl = FetcherImpl()

        # BTB for branch prediction
        btb = BTB(num_entries=64, index_bits=6)
        btb_impl = BTBImpl(num_entries=64, index_bits=6)

        decoder = Decoder()
        decoder_impl = DecoderImpl()
        hazard_unit = HazardUnit()

        executor = Execution()
        memory_unit = MemoryAccess()
        memory_single = SingleMemory()
        writeback = WriteBack()

        csrs_unit = CSRsUnit()

        driver = Driver()

        # 3. 逆序构建

        # --- BTB 构建（需要在使用前构建） ---
        btb_valid, btb_tags, btb_targets = btb.build()

        # --- WB 阶段 ---
        (
            wb_rd,
            wb_csr_waddr,
            csr_wdata,
            exception_valid,
            exception_code,
            exception_val,
            wb_pc,
            is_mret,
        ) = writeback.build(
            reg_file=reg_file,
            wb_bypass_reg=wb_bypass_reg,
            csr_wb_bypass_reg=csr_wb_bypass_reg,
            flush_all_pc=flush_all_pc,
        )

        # --- MEM 阶段 ---
        mem_rd, mem_csr_waddr, mem_pc, mem_is_store = memory_unit.build(
            wb_module=writeback,
            sram_dout=cache.dout,
            mem_bypass_reg=mem_bypass_reg,
            csr_mem_bypass_reg=csr_mem_bypass_reg,
            flush_all_pc=flush_all_pc,
        )

        # --- EX 阶段 ---
        (
            ex_rd,
            ex_csr_addr,
            ex_mem_addr,
            ex_is_load,
            ex_is_store,
            ex_width,
            ex_mem_data,
        ) = executor.build(
            mem_module=memory_unit,
            ex_bypass=ex_bypass_reg,
            mem_bypass=mem_bypass_reg,
            wb_bypass=wb_bypass_reg,
            csr_ex_bypass=csr_ex_bypass_reg,
            csr_mem_bypass=csr_mem_bypass_reg,
            csr_wb_bypass=csr_wb_bypass_reg,
            br_target_reg=branch_target_reg,
            flush_all_pc=flush_all_pc,
            btb_impl=btb_impl,
            btb_valid=btb_valid,
            btb_tags=btb_tags,
            btb_targets=btb_targets,
        )

        # --- ID 阶段-解码 ---
        pre_pkt, rs1, rs2, csr_raddr = decoder.build(
            icache_dout=cache.dout,
            reg_file=reg_file,
            current_mode=current_mode_reg,
        )

        # --- Hazard Unit ---
        rs1_sel, rs2_sel, csr_sel, stall_if = hazard_unit.build(
            rs1_idx=rs1,
            rs2_idx=rs2,
            csr_raddr=csr_raddr,
            ex_rd=ex_rd,
            ex_csr_waddr=ex_csr_addr,
            ex_is_load=ex_is_load,
            ex_is_store=ex_is_store,
            mem_is_store=mem_is_store,
            mem_rd=mem_rd,
            mem_csr_waddr=mem_csr_waddr,
            wb_rd=wb_rd,
            wb_csr_waddr=wb_csr_waddr,
        )

        # --- CSRs Unit ---
        csr_rdata, update_handling = csrs_unit.build(
            current_mode=current_mode_reg,
            mstatus=mstatus_reg,
            mie=mie_reg,
            mip=mip_reg,
            mtvec=mtvec_reg,
            mepc=mepc_reg,
            mcause=mcause_reg,
            mtval=mtval_reg,
            mscratch=mtscratch_reg,
            csr_raddr=csr_raddr,
            csr_waddr=wb_csr_waddr,
            csr_wdata=csr_wdata,
            Exception_Valid=exception_valid,
            Exception_Code=exception_code,
            Exception_Val=exception_val,
            WB_PC=wb_pc,
            MEM_PC=mem_pc,
            is_mret=is_mret,
            flush_all_pc=flush_all_pc,
        )

        # --- ID 阶段-仲裁 ---
        decoder_impl.build(
            pre=pre_pkt,
            executor=executor,
            rs1_sel=rs1_sel,
            rs2_sel=rs2_sel,
            csr_sel=csr_sel,
            stall_if=stall_if,
            br_target_pc=branch_target_reg,
            flush_all_pc=flush_all_pc,
            csr_data=csr_rdata,
        )

        # --- IF 阶段 ---
        pc_reg, pc_addr, last_pc_reg = fetcher.build()
        current_pc = fetcher_impl.build(
            pc_reg=pc_reg,
            pc_addr=pc_addr,
            last_pc_reg=last_pc_reg,
            decoder=decoder,
            stall_if=stall_if,
            branch_target=branch_target_reg,
            flush_all_pc=flush_all_pc,
            btb_impl=btb_impl,
            btb_valid=btb_valid,
            btb_tags=btb_tags,
            btb_targets=btb_targets,
        )

        # --- SRAM 驱动 ---
        memory_single.build(
            if_addr=current_pc,
            mem_addr=ex_mem_addr,
            re=ex_is_load,
            we=ex_is_store,
            wdata=ex_mem_data,
            width=ex_width,
            sram=cache,
            flush_all_signal=update_handling,
        )

        # --- 辅助驱动 ---
        driver.build(fetcher=fetcher)

    return sys


# ==============================================================================
# 主程序入口
# ==============================================================================

if __name__ == "__main__":
    # 构建 CPU 模块
    load_test_case("priv_illegal_ins1")
    sys_builder = build_cpu(depth_log=16)

    circ_path = os.path.join(workspace, f"circ.txt")
    with open(circ_path, "w") as f:
        print(sys_builder, file=f)

    print(f"🚀 Compiling system: {sys_builder.name}...")

    # 配置
    cfg = config(
        verilog=True,
        sim_threshold=50000,
        resource_base="",
        idle_threshold=50000,
    )

    # 生成源码
    simulator_path, verilog_path = elaborate(sys_builder, **cfg)

    # 编译二进制
    try:
        # build_simulator 内部会调用 cargo build，它的输出我们暂时不管
        # 只要最后 binary_path 存在就行
        binary_path = utils.build_simulator(simulator_path)
        print(f"🔨 Building binary from: {binary_path}")
    except Exception as e:
        print(f"❌ Simulator build failed: {e}")
        raise e

    # 运行模拟器，捕获输出
    print(f"🏃 Running simulation...")
    print(simulator_path)
    print(verilog_path)
    raw = utils.run_simulator(binary_path=binary_path)
    log_path = os.path.join(workspace, f"raw.log")
    with open(log_path, "w") as f:
        print(raw, file=f)

    # 运行verilog模拟器，捕获输出
    print(f"🏃 Running simulation(verilog)...")
    raw = utils.run_verilator(verilog_path)
    log_path = os.path.join(workspace, f"verilalog_raw.log")
    with open(log_path, "w") as f:
        print(raw, file=f)

    print("Done.")
