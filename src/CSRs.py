from assassyn.frontend import *


class CSRsUnit(Downstream):
    def __init__(self):
        super().__init__()
        self.name = "CSRs_Unit"

    @downstream.combinational
    def build(
        self,
        # CSR 寄存器
        current_mode: Array,
        mstatus: Array,
        mie: Array,
        mip: Array,
        mtvec: Array,
        mepc: Array,
        mcause: Array,
        mtval: Array,
        mscratch: Array,
        # 输入信号
        csr_raddr: Value,
        csr_waddr: Value,
        csr_wdata: Value,
        Exception_Valid: Value,
        Exception_Code: Value,
        Exception_Val: Value,
        WB_PC: Value,
        MEM_PC: Value,
        is_mret: Value,
        # 输出接口：全局寄存器
        flush_all_pc: Array,
    ):
        # 弹出信号
        csr_raddr_val = csr_raddr.optional(Bits(12)(0))
        csr_waddr_val = csr_waddr.optional(Bits(12)(0))
        csr_wdata_val = csr_wdata.optional(Bits(32)(0))
        Exception_Valid_val = Exception_Valid.optional(Bits(1)(0))
        Exception_Code_val = Exception_Code.optional(Bits(32)(0))
        Exception_Val_val = Exception_Val.optional(Bits(32)(0))
        WB_PC_val = WB_PC.optional(Bits(32)(0))
        MEM_PC_val = MEM_PC.optional(Bits(32)(0))
        is_mret_val = is_mret.optional(Bits(1)(0))

        # 1. CSR 读取逻辑 (ID Stage)
        # 读取 CSR 寄存器值，其他合法寄存器返回 0
        csr_rdata = Bits(32)(0)
        csr_rdata |= (csr_raddr_val == Bits(12)(0x300)).select(mstatus[0], Bits(32)(0))
        csr_rdata |= (csr_raddr_val == Bits(12)(0x301)).select(
            Bits(32)(0x40000100), Bits(32)(0)
        )
        csr_rdata |= (csr_raddr_val == Bits(12)(0x304)).select(mie[0], Bits(32)(0))
        csr_rdata |= (csr_raddr_val == Bits(12)(0x344)).select(mip[0], Bits(32)(0))
        csr_rdata |= (csr_raddr_val == Bits(12)(0x305)).select(mtvec[0], Bits(32)(0))
        csr_rdata |= (csr_raddr_val == Bits(12)(0x341)).select(mepc[0], Bits(32)(0))
        csr_rdata |= (csr_raddr_val == Bits(12)(0x342)).select(mcause[0], Bits(32)(0))
        csr_rdata |= (csr_raddr_val == Bits(12)(0x343)).select(mtval[0], Bits(32)(0))
        csr_rdata |= (csr_raddr_val == Bits(12)(0x340)).select(mscratch[0], Bits(32)(0))

        # 2. Trap & Write 状态机逻辑

        # 检查是否需要处理 Trap 或中断
        exception_handling = Exception_Valid_val == Bits(1)(1)
        # 检查中断受理逻辑: 仅在 MIE=1 且有挂起的中断时受理中断
        interrupt_enabled = mstatus[0][3:3] == Bits(1)(1)  # MIE 位
        interrupt_pending = (mie[0] & mip[0]) != Bits(32)(0)  # 有挂起的中断
        interrupt_handling = (
            (~exception_handling) & interrupt_enabled & interrupt_pending
        )
        # 确定是否出现 Trap
        trap_handling = exception_handling | interrupt_handling
        with Condition(trap_handling):
            log(
                "CSRs: Handling Trap - Exception: {}, Interrupt: {}",
                exception_handling,
                interrupt_handling,
            )
            # 检查是否在 M-mode 下发生 Trap（二重 Trap）
            with Condition(current_mode[0] == Bits(2)(0b11)):
                log("ERROR: Double trap in M-mode!")
                finish()
                
        # 综合 Trap 与 MRET 信号，确定是否进行状态更新
        update_handling = trap_handling | is_mret_val
        
        # 根据 Trap 信号、 mret 信号与写入信号进行状态迁移
        # Current_Mode ← M-Mode (11) 或 mstatus.MPP > 不变
        untrap_current_mode = mstatus[0][11:12]
        trap_current_mode = Bits(2)(0b11)
        update_current_mode = is_mret_val.select(untrap_current_mode, trap_current_mode)
        current_mode[0] <= update_handling.select(update_current_mode, current_mode[0])
        
        # 更新 mstatus: Trap/UnTrap > 写入 > 原值
        # Trap mstatus 更新
        trap_mstatus = mstatus[0]
        old_mie = mstatus[0][3:3]
        trap_mstatus[7:7] = old_mie  # MPIE ← MIE
        trap_mstatus[11:12] = current_mode[0]  # mstatus.MPP ← Current_Mode
        trap_mstatus[3:3] = Bits(1)(0)  # mstatus.MIE ← 0
        # Mret mstatus 更新
        untrap_mstatus = mstatus[0]
        old_mpie = mstatus[0][7:7]
        untrap_mstatus[3:3] = old_mpie  # MIE ← MPIE
        untrap_mstatus[7:7] = Bits(1)(1)  # MPIE ← 1
        untrap_mstatus[11:12] = Bits(2)(0b00)  # MPP ← U-Mode (00)
        update_mstatus = is_mret_val.select(untrap_mstatus, trap_mstatus)
        # CSR 写入 mstatus
        mstatus_mask = Bits(32)(0x00001888)
        w_mstatus_value = (mstatus[0] & ~mstatus_mask) | (csr_wdata_val & mstatus_mask)
        mpp = w_mstatus_value[11:12]
        legal_mpp = (mpp[1:1] == Bits(1)(1)).select(Bits(2)(0b11), Bits(2)(0b00))
        w_mstatus_value[11:12] = legal_mpp
        write_mstatus = (csr_waddr_val == Bits(12)(0x300)).select(
            w_mstatus_value, mstatus[0]
        )
        mstatus[0] <= update_handling.select(update_mstatus, write_mstatus)
        
        # mie 只因写入更改，但中断所在周期不进行更改
        mie_mask = Bits(32)(0x00000888)
        w_mie_value = (mie[0] & ~mie_mask) | (csr_wdata_val & mie_mask)
        mie[0] <= ((csr_waddr_val == Bits(12)(0x304)) & ~update_handling).select(
            w_mie_value, mie[0]
        )
        
        # mip 只因写入更改，但中断所在周期不进行更改
        mip_mask = Bits(32)(0x00000008)
        w_mip_value = (mip[0] & ~mip_mask) | (csr_wdata_val & mip_mask)
        mip[0] <= ((csr_waddr_val == Bits(12)(0x344)) & ~update_handling).select(
            w_mip_value, mip[0]
        )
        
        # mepc ← Trap_PC > 写入 > 原值
        Trap_PC = exception_handling.select(WB_PC_val, MEM_PC_val)
        trap_mepc = Trap_PC & Bits(32)(0xFFFFFFFC)
        mepc_mask = Bits(32)(0xFFFFFFFC)
        w_mepc_value = csr_wdata_val & mepc_mask
        write_mepc = (csr_waddr_val == Bits(12)(0x341)).select(w_mepc_value, mepc[0])
        mepc[0] <= trap_handling.select(trap_mepc, write_mepc)
        
        # mcause ← Exception Code/ Interrupt Code > 写入 > 原值
        mti_code = (mie[0][7:7] & mip[0][7:7] != Bits(1)(0)).select(
            Bits(32)(7), Bits(32)(0)
        )
        msi_code = (mie[0][3:3] & mip[0][3:3] != Bits(1)(0)).select(
            Bits(32)(3), mti_code
        )
        mei_code = (mie[0][11:11] & mip[0][11:11] != Bits(1)(0)).select(
            Bits(32)(11), msi_code
        )
        interrupt_code = Bits(32)(0x80000000) | mei_code
        exception_code = Exception_Code_val & Bits(32)(0x7FFFFFFF)
        trap_mcause = exception_handling.select(exception_code, interrupt_code)
        write_mcause = (csr_waddr_val == Bits(12)(0x342)).select(
            csr_wdata_val, mcause[0]
        )
        mcause[0] <= trap_handling.select(trap_mcause, write_mcause)
        
        # mtval ← Exception_Val > 写入 > 原值
        trap_mtval = exception_handling.select(Exception_Val_val, Bits(32)(0))
        write_mtval = (csr_waddr_val == Bits(12)(0x343)).select(csr_wdata_val, mtval[0])
        mtval[0] <= trap_handling.select(trap_mtval, write_mtval)
        
        # mtvec 只因写入改变，但中断所在周期不进行更改
        mtvec_mask = Bits(32)(0xFFFFFFFD)
        w_mtvec_value = (mtvec[0] & ~mtvec_mask) | (csr_wdata_val & mtvec_mask)
        mode = w_mtvec_value[0:1]
        legal_mode = (mode == Bits(2)(1)).select(Bits(2)(1), Bits(2)(0))
        w_mtvec_value[0:1] = legal_mode
        mtvec[0] <= ((csr_waddr_val == Bits(12)(0x305)) & ~update_handling).select(
            w_mtvec_value, mtvec[0]
        )
        
        # mscratch 写入
        mscratch[0] <= ((csr_waddr_val == Bits(12)(0x340)) & ~update_handling).select(
            csr_wdata_val, mscratch[0]
        )
        
        # Trap 时跳转到 mtvec 指示位置，设置冲刷信号。
        mtvec_base = mtvec[0] & Bits(32)(0xFFFFFFFC)
        mtvec_mode = mtvec[0][0:1]
        # 如果是 Vectored 模式且是中断，则根据当周期计算出的中断类型偏移
        vector_val = interrupt_code & Bits(32)(0x0FFFFFFF)
        interrupt_offset = vector_val.bitcast(UInt(32)) << UInt(32)(2)
        vector_pc = (mtvec_base.bitcast(UInt(32)) + interrupt_offset).bitcast(Bits(32))
        trap_pc = (mtvec_mode == Bits(2)(1) & interrupt_handling).select(
            vector_pc, mtvec_base
        )
        untrap_pc = mepc[0]
        update_pc = is_mret_val.select(untrap_pc, trap_pc)
        # 接口寄存器更新
        flush_all_pc[0] <= update_handling.select(update_pc, Bits(32)(0))


        # 返回输出信号
        return csr_rdata, update_handling
