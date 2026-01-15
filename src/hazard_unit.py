from assassyn.frontend import *
from .control_signals import *


class HazardUnit(Downstream):
    def __init__(self):
        super().__init__()
        self.name = "HazardUnit"

    @downstream.combinational
    def build(
        self,
        # --- 1. 来自 ID 级 (当前指令需求) ---
        rs1_idx: Value,  # 源寄存器 1 索引 (Value)
        rs2_idx: Value,  # 源寄存器 2 索引 (Value)
        csr_raddr: Value,  # CSR 读寄存器索引 (Value)
        # --- 2. 来自流水线各级 (实时状态回传) ---
        # 各级 Module build() 的返回值
        ex_rd: Value,  # EX 级目标寄存器索引
        ex_csr_waddr: Value,  # EX 级 CSR 写寄存器索引
        ex_is_load: Value,  # EX 级是否为 Load 指令
        ex_is_store: Value,  # EX 级是否为 Store 指令
        mem_is_store: Value,  # MEM 级是否为 Store 指令
        mem_rd: Value,  # MEM 级目标寄存器索引
        mem_csr_waddr: Value,  # MEM 级 CSR 写寄存器索引
        wb_rd: Value,  # WB 级目标寄存器索引
        wb_csr_waddr: Value,  # WB 级 CSR 写寄存器索引
    ):
        # 使用 optional() 处理 Value 接口，如果无效则使用默认值 Bits(x)(0)
        rs1_idx_val = rs1_idx.optional(Bits(5)(0))
        rs2_idx_val = rs2_idx.optional(Bits(5)(0))
        csr_raddr_val = csr_raddr.optional(Bits(12)(0))
        ex_rd_val = ex_rd.optional(Bits(5)(0))
        ex_csr_waddr_val = ex_csr_waddr.optional(Bits(12)(0))
        ex_is_load_val = ex_is_load.optional(Bits(1)(0))
        ex_is_store_val = ex_is_store.optional(Bits(1)(0))
        mem_is_store_val = mem_is_store.optional(Bits(1)(0))
        mem_rd_val = mem_rd.optional(Bits(5)(0))
        mem_csr_waddr_val = mem_csr_waddr.optional(Bits(12)(0))
        wb_rd_val = wb_rd.optional(Bits(5)(0))
        wb_csr_waddr_val = wb_csr_waddr.optional(Bits(12)(0))

        # 检查寄存器是否为零寄存器（x0），避免对零寄存器的冒险检测
        rs1_is_zero = rs1_idx_val == Bits(5)(0)
        rs2_is_zero = rs2_idx_val == Bits(5)(0)
        csr_is_zero = csr_raddr_val == Bits(12)(0)

        # 1. 检测 Load/Store 并生成 Stall 信号
        # 条件： ex_is_load == 1 || ex_is_store == 1 || mem_is_store == 1
        stall_if = ex_is_load_val | ex_is_store_val | mem_is_store_val

        # 2. 检测 Forwarding 并生成 Mux 选择码
        # 根据先前指令 rd 与当前指令 rs1、rs2 生成选择码 rs1_sel 与 rs2_sel
        # rs1 旁路选择
        rs1_wb_bypass = (rs1_idx_val == wb_rd_val).select(Rs1Sel.WB_BYPASS, Rs1Sel.RS1)
        rs1_mem_bypass = (rs1_idx_val == mem_rd_val).select(
            Rs1Sel.MEM_BYPASS, rs1_wb_bypass
        )
        rs1_ex_bypass = (rs1_idx_val == ex_rd_val).select(
            Rs1Sel.EX_BYPASS, rs1_mem_bypass
        )
        rs1_sel = (~rs1_is_zero).select(rs1_ex_bypass, Rs1Sel.RS1)

        # rs2 旁路选择
        rs2_wb_bypass = (rs2_idx_val == wb_rd_val).select(Rs2Sel.WB_BYPASS, Rs2Sel.RS2)
        rs2_mem_bypass = (rs2_idx_val == mem_rd_val).select(
            Rs2Sel.MEM_BYPASS, rs2_wb_bypass
        )
        rs2_ex_bypass = (rs2_idx_val == ex_rd_val).select(
            Rs2Sel.EX_BYPASS, rs2_mem_bypass
        )
        rs2_sel = (~rs2_is_zero).select(rs2_ex_bypass, Rs2Sel.RS2)

        # CSR 旁路选择
        csr_wb_bypass = (csr_raddr_val == wb_csr_waddr_val).select(
            CSRReadSel.CSR_WB_BYPASS, CSRReadSel.CSR
        )
        csr_mem_bypass = (csr_raddr_val == mem_csr_waddr_val).select(
            CSRReadSel.CSR_MEM_BYPASS, csr_wb_bypass
        )
        csr_ex_bypass = (csr_raddr_val == ex_csr_waddr_val).select(
            CSRReadSel.CSR_EX_BYPASS, csr_mem_bypass
        )
        csr_sel = (~csr_is_zero).select(csr_ex_bypass, CSRReadSel.CSR)
        log(
            "HazardUnit: rs1_sel={} rs2_sel={} csr_sel={} stall_if={}",
            rs1_sel,
            rs2_sel,
            csr_sel,
            stall_if,
        )

        # 返回旁路选择信号和停顿信号
        return rs1_sel, rs2_sel, csr_sel, stall_if
