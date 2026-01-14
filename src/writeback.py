from assassyn.frontend import *
from .control_signals import wb_ctrl_signals


class WriteBack(Module):

    def __init__(self):
        super().__init__(
            ports={
                # 控制通路：包含 wb_ctrl 信号
                "ctrl": Port(wb_ctrl_signals),
                # 数据通路
                # rd 写入数据
                "wdata": Port(Bits(32)),
                # CSR 写入数据
                "csr_wdata": Port(Bits(32)),
            }
        )
        self.name = "WB"

    @module.combinational
    def build(
        self,
        reg_file: Array,
        wb_bypass_reg: Array,
        csr_wb_bypass_reg: Array,
        flush_all_pc: Array,
    ):

        # 1. 获取输入
        wb_ctrl, wdata, csr_wdata = self.pop_all_ports(False)

        # 2. 判定是否 Flush 并确定相关门控信号
        flush_if = flush_all_pc[0] != Bits(32)(0)
        rd = flush_if.select(Bits(5)(0), wb_ctrl.rd_addr)
        wdata = flush_if.select(Bits(32)(0), wdata)
        csr_waddr = flush_if.select(Bits(12)(0), wb_ctrl.csr_waddr)
        csr_wdata = flush_if.select(Bits(32)(0), csr_wdata)
        halt_if = wb_ctrl.halt_if & (~flush_if)
        exception_valid = wb_ctrl.Exception_Valid & (~flush_if)

        log("Input: rd=x{} wdata=0x{:x}", rd, wdata)
        log("Input: csr_waddr=0x{:x} csr_wdata=0x{:x}", csr_waddr, csr_wdata)
        log("Input: halt_if={} exception_valid={}", halt_if, exception_valid)

        # 3. 写入 Unprivileged 寄存器
        # 当目标寄存器不是 x0 时写入指定寄存器，否则写入全 0，同时更新旁路寄存器
        wdata = (rd == Bits(5)(0)).select(Bits(32)(0), wdata)
        reg_file[rd] = wdata
        wb_bypass_reg[0] = wdata
        log("WB: Write x{} <= 0x{:x}", rd, wdata)

        # 4. 写入 CSR 旁路寄存器
        csr_wdata = (csr_waddr == Bits(12)(0)).select(Bits(32)(0), csr_wdata)
        csr_wb_bypass_reg[0] = csr_wdata
        log("WB: CSR Write 0x{:x} <= 0x{:x}", csr_waddr, csr_wdata)

        # 5. 获取其他 CSR 信号
        exception_code = wb_ctrl.Exception_Code
        exception_val = wb_ctrl.Exception_Val
        pc = wb_ctrl.PC
        is_mret = wb_ctrl.is_MRET

        # 6. 仿真终止检测 (Halt Detection)
        with Condition(halt_if == Bits(1)(1)):
            log("WB: HALT triggered!")
            finish()

        # 引脚暴露 (供 HazardUnit 与 CSRsUnit 使用)
        return (
            rd,
            csr_waddr,
            csr_wdata,
            exception_valid,
            exception_code,
            exception_val,
            pc,
            is_mret,
        )
