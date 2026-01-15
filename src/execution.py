from assassyn.frontend import *
from .control_signals import *


class Execution(Module):
    def __init__(self):
        super().__init__(
            ports={
                # --- [1] 控制通道 (Control Plane) ---
                # 包含 ex_ctrl_signals 定义的所有控制信号
                "ctrl": Port(ex_ctrl_signals),
                # --- [2] 数据通道群 (Data Plane) ---
                # 源寄存器 1 数据 (来自 RegFile)
                "rs1_data": Port(Bits(32)),
                # 源寄存器 2 数据 (来自 RegFile)
                "rs2_data": Port(Bits(32)),
                # CSR 寄存器数据 (来自 CSRsUnit)
                "csr_data": Port(Bits(32)),
                # 立即数 (在 ID 级已完成对应有/无符号扩展)
                "imm": Port(Bits(32)),
            }
        )
        self.name = "Executor"

    @module.combinational
    def build(
        self,
        mem_module: Module,  # 下一级流水线 (MEM)
        # --- 旁路数据源 (Forwarding Sources) ---
        ex_bypass: Array,  # 来自 EX-MEM 旁路寄存器的数据（上条指令结果）
        mem_bypass: Array,  # 来自 MEM-WB 旁路寄存器的数据 (上上条指令结果)
        wb_bypass: Array,  # 来自 WB 旁路寄存器的数据 (当前写回数据)
        # --- CSR 旁路数据源 (CSR Forwarding Sources) ---
        csr_ex_bypass: Array,  # 来自 EX-MEM 旁路寄存器的 CSR 数据
        csr_mem_bypass: Array,  # 来自 MEM-WB 旁路寄存器的 CSR 数据
        csr_wb_bypass: Array,  # 来自 WB 旁路寄存器的 CSR 数据
        # --- 分支反馈 ---
        br_target_reg: Array,  # 用于通知 IF 跳转目标的全局寄存器
        # --- 全局 Flush 信号 ---
        flush_all_pc: Array,  # 来自 CSRsUnit 的全局 Flush 信号
        # --- BTB 更新 (可选) ---
        btb_impl: "BTBImpl" = None,  # BTB 实现逻辑
        btb_valid: Array = None,  # BTB 有效位数组
        btb_tags: Array = None,  # BTB 标签数组
        btb_targets: Array = None,  # BTB 目标地址数组
    ):
        # 1. 弹出并初步处理所有端口数据
        # 根据 __init__ 定义顺序解包
        ctrl, rs1_data, rs2_data, csr_rdata, imm = self.pop_all_ports(False)
        mem_ctrl = mem_ctrl_signals.view(ctrl.mem_ctrl)
        wb_ctrl = wb_ctrl_signals.view(mem_ctrl.wb_ctrl)
        pc = wb_ctrl.PC
        # 确定是否要 Flush 指令
        flush_if = (br_target_reg[0] != Bits(32)(0)) | (flush_all_pc[0] != Bits(32)(0))
        with Condition(flush_if == Bits(1)(1)):
            log("EX: Flush")
        # 获取旁路数据
        fwd_from_ex = ex_bypass[0]
        fwd_from_mem = mem_bypass[0]
        fwd_from_wb = wb_bypass[0]
        csr_from_ex = csr_ex_bypass[0]
        csr_from_mem = csr_mem_bypass[0]
        csr_from_wb = csr_wb_bypass[0]
        # --- rs1 旁路处理 ---
        ex_rs1_data = ctrl.rs1_sel.select1hot(
            rs1_data, fwd_from_ex, fwd_from_mem, fwd_from_wb
        )
        # --- rs2 旁路处理 ---
        ex_rs2_data = ctrl.rs2_sel.select1hot(
            rs2_data, fwd_from_ex, fwd_from_mem, fwd_from_wb
        )
        # --- csr 旁路处理 ---
        ex_csr_data = ctrl.csr_sel.select1hot(
            csr_rdata, csr_from_ex, csr_from_mem, csr_from_wb
        )

        # --- ALU 计算 ---
        # 1. 操作数选择
        # 操作数 1 选择: 0-RS1  1-PC (AUIPC/JAL/Branch) 2-ZERO (LUI Link)
        alu_op1 = ctrl.op1_sel.select1hot(
            ex_rs1_data,
            pc,
            Bits(32)(0),
        )
        # 操作数 2 选择: 0-RS2  1-IMM  2-FOUR (JAL/JALR Link)
        alu_op2 = ctrl.op2_sel.select1hot(
            ex_rs2_data,
            imm,
            Bits(32)(4),
        )
        # 2. 运算
        # 转换为有符号数进行运算
        op1_signed = alu_op1.bitcast(Int(32))
        op2_signed = alu_op2.bitcast(Int(32))
        add_res = (op1_signed + op2_signed).bitcast(Bits(32))
        sub_res = (op1_signed - op2_signed).bitcast(Bits(32))
        and_res = alu_op1 & alu_op2
        or_res = alu_op1 | alu_op2
        xor_res = alu_op1 ^ alu_op2
        # 逻辑左移 (使用低5位作为移位位数)
        sll_res = alu_op1 << alu_op2[0:4]
        # 逻辑右移 (使用低5位作为移位位数)
        srl_res = alu_op1 >> alu_op2[0:4]
        # 算术右移 (使用低5位作为移位位数)
        sra_res = (op1_signed >> alu_op2[0:4]).bitcast(Bits(32))
        # 有符号比较小于
        slt_res = (op1_signed < op2_signed).bitcast(Bits(32))
        # 无符号比较小于
        sltu_res = (alu_op1 < alu_op2).bitcast(Bits(32))
        # 3. 结果选择
        alu_result = ctrl.alu_func.select1hot(
            add_res,  # ADD
            sub_res,  # SUB
            sll_res,  # SLL
            slt_res,  # SLT
            sltu_res,  # SLTU
            xor_res,  # XOR
            srl_res,  # SRL
            sra_res,  # SRA
            or_res,  # OR
            and_res,  # AND
            ex_csr_data,  # SYS
            alu_op2,  # 占位
            alu_op2,  # 占位
            alu_op2,  # 占位
            alu_op2,  # 占位
            alu_op2,  # 占位
        )
        with Condition(ctrl.alu_func == ALUOp.ADD):
            log("EX: ALU Operation: ADD")
        with Condition(ctrl.alu_func == ALUOp.SUB):
            log("EX: ALU Operation: SUB")
        with Condition(ctrl.alu_func == ALUOp.SLL):
            log("EX: ALU Operation: SLL")
        with Condition(ctrl.alu_func == ALUOp.SLT):
            log("EX: ALU Operation: SLT")
        with Condition(ctrl.alu_func == ALUOp.SLTU):
            log("EX: ALU Operation: SLTU")
        with Condition(ctrl.alu_func == ALUOp.XOR):
            log("EX: ALU Operation: XOR")
        with Condition(ctrl.alu_func == ALUOp.SRL):
            log("EX: ALU Operation: SRL")
        with Condition(ctrl.alu_func == ALUOp.SRA):
            log("EX: ALU Operation: SRA")
        with Condition(ctrl.alu_func == ALUOp.OR):
            log("EX: ALU Operation: OR")
        with Condition(ctrl.alu_func == ALUOp.AND):
            log("EX: ALU Operation: AND")
        with Condition(ctrl.alu_func == ALUOp.SYS):
            log("EX: ALU Operation: SYS")
        with Condition(ctrl.alu_func == ALUOp.NOP):
            log("EX: ALU Operation: NOP or Reserved")

        # 4. 更新本级 ALU_result Bypass 寄存器
        ex_bypass[0] <= alu_result
        log("EX: ALU Result & Bypass Update: 0x{:x}", alu_result)

        # --- CSR 写入数据计算 ---
        # 操作数 1 选择: 1-uimm  0-rs1
        csr_alu_op1 = ctrl.csr_op_sel.select(imm, ex_rs1_data)
        csr_alu_op2 = ex_csr_data
        csrrw_res = csr_alu_op1
        csrrs_res = csr_alu_op2 | csr_alu_op1
        csrrc_res = csr_alu_op2 & (~csr_alu_op1)
        csr_alu_result = ctrl.csr_alu_func.select1hot(csrrw_res, csrrs_res, csrrc_res)
        log("EX: CSR ALU Result: 0x{:x}", csr_alu_result)

        # --- 分支处理 (Branch Handling) ---
        # 1. 使用专用加法器计算跳转地址，对于 JALR，基址是 rs1；对于 JAL/Branch，基址是 PC
        is_jalr = ctrl.branch_type == BranchType.JALR
        target_base = is_jalr.select(ex_rs1_data, pc)  # 0: Branch / JAL  # 1: JALR
        # 专用加法器永远做 Base + Imm
        imm_signed = imm.bitcast(Int(32))
        log("EX: Branch Immediate: 0x{:x}", imm)
        target_base_signed = target_base.bitcast(Int(32))
        log("EX: Branch Target Base: 0x{:x}", target_base)
        raw_calc_target = (target_base_signed + imm_signed).bitcast(Bits(32))
        calc_target = is_jalr.select(
            concat(raw_calc_target[1:31], Bits(1)(0)),  # JALR: 目标地址最低位清0
            raw_calc_target,  # Branch / JAL: 直接使用计算结果
        )

        # 2. 计算分支条件
        # 对于 BEQ: alu_result == 0
        # 对于 BNE: alu_result != 0
        # 对于 BLT: alu_result[0] == 1
        # 对于 BGE: alu_result[0] == 0
        # 对于 BLTU: alu_result[0] == 1
        # 对于 BGEU: alu_result[0] == 0
        is_taken = Bits(1)(0)
        is_branch = ctrl.branch_type != BranchType.NO_BRANCH
        with Condition(ctrl.branch_type == BranchType.BEQ):
            log("EX: Branch Type: BEQ")
        with Condition(ctrl.branch_type == BranchType.BNE):
            log("EX: Branch Type: BNE")
        with Condition(ctrl.branch_type == BranchType.BLT):
            log("EX: Branch Type: BLT")
        with Condition(ctrl.branch_type == BranchType.BGE):
            log("EX: Branch Type: BGE")
        with Condition(ctrl.branch_type == BranchType.BLTU):
            log("EX: Branch Type: BLTU")
        with Condition(ctrl.branch_type == BranchType.BGEU):
            log("EX: Branch Type: BGEU")
        with Condition(ctrl.branch_type == BranchType.JAL):
            log("EX: Branch Type: JAL")
        with Condition(ctrl.branch_type == BranchType.JALR):
            log("EX: Branch Type: JALR")
        with Condition(ctrl.branch_type == BranchType.NO_BRANCH):
            log("EX: Branch Type: NO_BRANCH")
        # 根据不同的分支类型判断分支条件
        is_eq = alu_result == Bits(32)(0)
        is_lt = alu_result[0:0] == Bits(1)(1)  # 符号位为1表示小于
        # BEQ, BNE 使用等于判断
        is_taken_eq = (ctrl.branch_type == BranchType.BEQ) & is_eq
        is_taken_ne = (ctrl.branch_type == BranchType.BNE) & ~is_eq
        # BLT, BGE 使用小于判断
        is_taken_lt = (ctrl.branch_type == BranchType.BLT) & is_lt
        is_taken_ge = (ctrl.branch_type == BranchType.BGE) & ~is_lt
        # BLTU, BGEU 使用无符号小于判断
        is_taken_ltu = (ctrl.branch_type == BranchType.BLTU) & is_lt
        is_taken_geu = (ctrl.branch_type == BranchType.BGEU) & ~is_lt
        # 综合所有条件判断分支是否 taken
        is_taken = (
            is_taken_eq
            | is_taken_ne
            | is_taken_lt
            | is_taken_ge
            | is_taken_ltu
            | is_taken_geu
            | (ctrl.branch_type == BranchType.JAL)
            | is_jalr
        )
        # 3. 计算最终的下一个 PC
        final_next_pc = flush_if.select(
            Bits(32)(0),
            is_branch.select(
                is_taken.select(
                    calc_target,  # Taken
                    (pc.bitcast(UInt(32)) + UInt(32)(4)).bitcast(Bits(32)),  # Not Taken
                ),
                ctrl.next_pc_addr,
            ),
        )
        # 4. 判断 miss 与否并赋值分支目标寄存器，IF 与 ID 级用其判断 Flush 与否
        branch_miss = final_next_pc != ctrl.next_pc_addr
        br_target_reg[0] = branch_miss.select(
            final_next_pc,  # 跳转，写入目标地址
            Bits(32)(0),  # 不跳转，写 0 表示顺序执行
        )
        with Condition(is_branch):
            log("EX: Branch Target: 0x{:x}", calc_target)
            log("EX: Branch Taken: {}", is_taken == Bits(1)(1))
        # 5. 更新 BTB (如果提供了 BTB 引用)
        # 当分支指令 taken 时，更新 BTB 存储 PC -> Target 的映射
        if btb_impl is not None and btb_valid is not None:
            should_update_btb = is_branch & is_taken & ~flush_if
            btb_impl.update(
                pc=pc,
                target=calc_target,
                should_update=should_update_btb,
                btb_valid=btb_valid,
                btb_tags=btb_tags,
                btb_targets=btb_targets,
            )

        # --- 下一级绑定与状态反馈 ---
        # 1. 检查：L/S Addr Misaligned (Exception Code 0x04/0x06)
        alu_result_lower2 = alu_result[0:2]
        is_load_store = (mem_ctrl.mem_opcode == MemOp.LOAD) | (
            mem_ctrl.mem_opcode == MemOp.STORE
        )
        addr_misaligned = (
            (~flush_if)
            & is_load_store
            & (
                (
                    (mem_ctrl.mem_width == MemWidth.HALF)
                    & (alu_result_lower2[0:1] != Bits(1)(0))
                )
                | (
                    (mem_ctrl.mem_width == MemWidth.WORD)
                    & (alu_result_lower2 != Bits(2)(0))
                )
            )
        )
        exception_code = addr_misaligned.select(
            (mem_ctrl.mem_opcode == MemOp.LOAD).select(
                EXC_LOAD_ADDR_MISALIGNED, EXC_STORE_ADDR_MISALIGNED
            ),
            Bits(32)(0),
        )
        exception_val = addr_misaligned.select(alu_result, Bits(32)(0))
        with Condition(addr_misaligned):
            log("EX: Exception Detected - Load/Store Address Misaligned")

        # 2. 构造控制信号包
        ex_result_rd = (flush_if | addr_misaligned).select(Bits(5)(0), wb_ctrl.rd_addr)
        ex_result_halt_if = (flush_if | addr_misaligned).select(
            Bits(1)(0), wb_ctrl.halt_if
        )
        ex_result_Exception_Valid = flush_if.select(
            Bits(1)(0), wb_ctrl.Exception_Valid | addr_misaligned
        )
        ex_result_Exception_Code = addr_misaligned.select(
            exception_code, wb_ctrl.Exception_Code
        )
        ex_result_Exception_Val = addr_misaligned.select(
            exception_val, wb_ctrl.Exception_Val
        )
        ex_result_is_MRET = (flush_if | addr_misaligned).select(
            Bits(1)(0), wb_ctrl.is_MRET
        )
        ex_result_csr_waddr = (flush_if | addr_misaligned).select(
            Bits(12)(0), wb_ctrl.csr_waddr
        )
        ex_result_mem_opcode = (flush_if | addr_misaligned).select(
            MemOp.NONE, mem_ctrl.mem_opcode
        )
        log(
            "Control after Flush Check: mem_opcode=0x{:x} rd=0x{:x}",
            ex_result_mem_opcode,
            ex_result_rd,
        )
        ex_result_wb_ctrl = wb_ctrl_signals.bundle(
            rd_addr=ex_result_rd,
            halt_if=ex_result_halt_if,
            is_MRET=ex_result_is_MRET,
            Exception_Valid=ex_result_Exception_Valid,
            Exception_Code=ex_result_Exception_Code,
            Exception_Val=ex_result_Exception_Val,
            PC=wb_ctrl.PC,
            csr_waddr=ex_result_csr_waddr,
        )
        ex_result_mem_ctrl = mem_ctrl_signals.bundle(
            mem_opcode=ex_result_mem_opcode,
            mem_width=mem_ctrl.mem_width,
            mem_unsigned=mem_ctrl.mem_unsigned,
            wb_ctrl=ex_result_wb_ctrl,
        )
        # 3. 级间信号：控制 + 数据
        mem_call = mem_module.async_called(
            ctrl=ex_result_mem_ctrl, alu_result=alu_result, csr_result=csr_alu_result
        )
        mem_call.bind.set_fifo_depth(ctrl=1, alu_result=1, csr_result=1)
        # 4. 访存操作: 将所需的信号作为引脚给出，交给 SingleMemory 处理
        is_store = (ex_result_mem_opcode == MemOp.STORE) & (~ex_result_halt_if)
        is_load = ex_result_mem_opcode == MemOp.LOAD
        mem_width = ex_result_mem_ctrl.mem_width
        with Condition(is_store):
            log("EX: Memory Operation: STORE")
            log("EX: Store Address: 0x{:x}", alu_result)
            log("EX: Store Data: 0x{:x}", ex_rs2_data)
        with Condition(is_load):
            log("EX: Memory Operation: LOAD")
            log("EX: Load Address: 0x{:x}", alu_result)

        # 返回引脚 (供 HazardUnit 与 SingleMemory 使用)
        return (
            ex_result_rd,
            ex_result_csr_waddr,
            alu_result,
            is_load,
            is_store,
            mem_width,
            ex_rs2_data,
        )
