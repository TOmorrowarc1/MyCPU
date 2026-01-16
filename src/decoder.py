from assassyn.frontend import *
from .control_signals import *
from .instruction_table import rv32i_table


# 辅助函数：生成填充位
def get_pad(width, hex_mask, sign):
    return sign.select(Bits(width)(hex_mask), Bits(width)(0))


class Decoder(Module):
    def __init__(self):
        super().__init__(
            ports={
                "ctrl": Port(id_ctrl_signals),
                "next_pc": Port(Bits(32)),
            }
        )
        self.name = "Decoder"

    @module.combinational
    def build(
        self,
        icache_dout: Array,
        reg_file: Array,
        current_mode: Array,
    ):

        # 内部寄存器: 记录上一个周期的Ins，用于在 Stall 时稳住输入
        last_ins_reg = RegArray(Bits(32), 1, initializer=[0])

        # 1. 获取输入信号
        id_ctrl, next_pc_val = self.pop_all_ports(False)
        fetch_exception_vaild = id_ctrl.Exception_Valid
        fetch_exception_code = id_ctrl.Exception_Code
        fetch_exception_val = id_ctrl.Exception_Val
        stall_if = id_ctrl.stall_if
        pc = id_ctrl.PC
        # 从 SRAM 输出获取指令
        icache_inst = icache_dout[0].bitcast(Bits(32))

        # 2. 选择指令与特殊约定:
        # Stall > IF EXCEPTION 根据信号选择指令并更新寄存器
        NOP = Bits(32)(0x00000013)  # NOP
        fetch_inst = fetch_exception_vaild.select(NOP, icache_inst)
        raw_inst = stall_if.select(last_ins_reg[0], fetch_inst)
        last_ins_reg[0] <= raw_inst
        # 将初始化时出现的 0b0 指令替换为 NOP (TODO)
        inst = (raw_inst == Bits(32)(0)).select(NOP, raw_inst)
        log("ID: Fetched Instruction=0x{:x} at PC=0x{:x}", inst, pc)
        # 补充：sb x0, -1(x0) 指令停机
        halt_if = inst == Bits(32)(0xFE000FA3)
        with Condition(halt_if == Bits(1)(1)):
            log("ID: Halt Ins in ID with pc=0x{:x}", pc)

        # 3. 指令解析
        # 3.1 字段获取
        rd = inst[7:11]
        rs1 = inst[15:19]
        rs2 = inst[20:24]
        csr_addr = inst[20:31]
        # 立即数并行生成
        sign = inst[31:31]
        # I-Type: [31]*20 | [31:20]
        pad_20 = get_pad(20, 0xFFFFF, sign)
        imm_i = concat(pad_20, inst[20:31])
        # S-Type: [31]*20 | [31:25] | [11:7]
        imm_s = concat(pad_20, inst[25:31], inst[7:11])
        # B-Type: [31]*19 | [31] | [7] | [30:25] | [11:8] | 0
        pad_19 = get_pad(19, 0x7FFFF, sign)
        imm_b = concat(
            pad_19, inst[31:31], inst[7:7], inst[25:30], inst[8:11], Bits(1)(0)
        )
        # U-Type: [31:12] | 0*12
        imm_u = concat(inst[12:31], Bits(12)(0))
        # J-Type: [31]*11 | [31] | [19:12] | [20] | [30:21] | 0
        pad_11 = get_pad(11, 0x7FF, sign)
        imm_j = concat(
            pad_11, inst[31:31], inst[12:19], inst[20:20], inst[21:30], Bits(1)(0)
        )
        # Z-Type: CSR 指令立即数 (零扩展)
        imm_z = concat(Bits(27)(0), inst[15:19])

        # 3.2 查表译码 (Signal Accumulation Loop)
        # 初始化累加器
        acc_alu_func = Bits(16)(0)
        acc_op1_sel = Bits(3)(0)
        acc_op2_sel = Bits(3)(0)
        acc_imm_type = Bits(7)(0)
        acc_br_type = Bits(16)(0)
        acc_mem_op = Bits(3)(0)
        acc_mem_wid = Bits(3)(0)
        acc_mem_uns = Bits(1)(0)
        acc_mem_we = Bits(1)(0)
        # CSR 相关控制信号累加器
        acc_csr_op_sel = Bits(1)(0)
        acc_csr_alu_func = Bits(3)(0)
        acc_csr_re = Bits(1)(0)
        acc_csr_we = Bits(1)(0)
        # 并行匹配并累加信号
        match_if = Bits(1)(0)
        has_match = Bits(1)(0)
        for entry in rv32i_table:
            (
                _,
                (t_value, t_mask),
                t_imm_type,
                (t_alu_func, t_op1_sel, t_op2_sel, t_branch_type),
                (t_mem_op, t_mem_width, t_mem_sign),
                t_we,
                (t_csr_op_sel, t_csr_alu_func, t_csr_re, t_csr_we),
            ) = entry

            # --- A. 匹配逻辑 ---
            # 使用 BP 函数返回的 (value, mask) 进行匹配
            match_if = (inst & t_mask) == t_value
            has_match |= match_if
            # --- B. 信号累加 (Mux Logic) ---
            # 使用 select 实现 OR 逻辑
            acc_imm_type |= match_if.select(t_imm_type, Bits(7)(0))
            acc_alu_func |= match_if.select(t_alu_func, Bits(16)(0))
            acc_op1_sel |= match_if.select(t_op1_sel, Bits(3)(0))
            acc_op2_sel |= match_if.select(t_op2_sel, Bits(3)(0))
            acc_br_type |= match_if.select(t_branch_type, Bits(16)(0))
            acc_mem_op |= match_if.select(t_mem_op, Bits(3)(0))
            acc_mem_wid |= match_if.select(t_mem_width, Bits(3)(0))
            acc_mem_uns |= match_if.select(t_mem_sign, Bits(1)(0))
            acc_mem_we |= match_if.select(t_we, Bits(1)(0))
            # CSR 相关信号累加
            acc_csr_op_sel |= match_if.select(t_csr_op_sel, Bits(1)(0))
            acc_csr_alu_func |= match_if.select(t_csr_alu_func, Bits(3)(0))
            acc_csr_re |= match_if.select(t_csr_re, Bits(1)(0))
            acc_csr_we |= match_if.select(t_csr_we, Bits(1)(0))

        acc_imm = acc_imm_type.select1hot(
            Bits(32)(0),
            imm_i,
            imm_s,
            imm_b,
            imm_u,
            imm_j,
            imm_z,
        )
        # 加工: rd & csr_addr 读写使能
        id_rd = acc_mem_we.select(rd, Bits(5)(0))
        # Ziscr 指令 rd = x0 时不读 CSR, rs1/zimm = 0 时不写 CSR
        id_csr_re = (rd != Bits(5)(0)) & (acc_csr_re == CSRRe.ENABLE)
        id_csr_we = ((rs1 != Bits(5)(0)) | (acc_csr_alu_func == CSRALUOp.CSR_RW)) & (
            acc_csr_we == CSRWe.ENABLE
        )
        csr_raddr = id_csr_re.select(csr_addr, Bits(12)(0))
        csr_waddr = id_csr_we.select(csr_addr, Bits(12)(0))

        # 4. 异常处理
        # 4.1 权限与合法性检查
        in_mmode = current_mode[0] == Bits(2)(0b11)
        in_umode = current_mode[0] == Bits(2)(0b00)
        # 4.1.1 CSR 访问权限检查
        # 规则1: 当前权限 < CSR 定义的最低权限 (Bits 9:8) -> 非法
        # 规则2: 尝试写入 (WE=1) 只读 CSR (Bits 11:10 == 11) -> 非法
        # 规则3: 尝试写入尚未定义的 CSR -> 非法
        csr_in_mmode = csr_addr[8:9] == Bits(2)(0b11)
        is_csr_ro = csr_addr[10:11] == Bits(2)(0b11)
        # TODO: 完善 CSR 未定义列表
        csr_access_fault = (
            (acc_csr_re | acc_csr_we) & ((in_umode & csr_in_mmode))
        ) | (acc_csr_we & is_csr_ro)
        # 4.1.2 MRET 权限检查: 只有 M-Mode (11) 可以执行 mret，否则报非法指令
        is_mret_inst = inst == Bits(32)(0x30200073)
        mret_priv_fault = is_mret_inst & (~in_mmode)
        # 4.1.3 汇总非法指令条件
        is_illegal_inst = (has_match == Bits(1)(0)) | csr_access_fault | mret_priv_fault
        # 4.2 特殊指令检测
        is_ecall = inst == Bits(32)(0x00000073)
        is_ebreak = inst == Bits(32)(0x00100073)
        # 4.3 异常信号生成
        exception_valid = fetch_exception_vaild | is_illegal_inst | is_ecall | is_ebreak
        # 级联选择 Exception_Code
        ecall_code_target = in_mmode.select(EXC_ECALL_MMODE, EXC_ECALL_UMODE)
        code_sel_ecall = is_ecall.select(ecall_code_target, Bits(32)(0))
        code_sel_ebreak = is_ebreak.select(EXC_EBREAK, code_sel_ecall)
        code_sel_illegal = is_illegal_inst.select(EXC_ILLEGAL_INST, code_sel_ebreak)
        exception_code = fetch_exception_vaild.select(
            fetch_exception_code, code_sel_illegal
        )
        # 级联选择 Exception_Val (mtval)
        val_sel_illegal = is_illegal_inst.select(inst, Bits(32)(0))
        exception_val = fetch_exception_vaild.select(
            fetch_exception_val, val_sel_illegal
        )

        # 5. 读取寄存器堆 & 打包
        raw_rs1_data = reg_file[rs1]
        raw_rs2_data = reg_file[rs2]
        # 构造预解码包
        wb_ctrl_t = wb_ctrl_signals.bundle(
            rd_addr=id_rd,
            halt_if=halt_if,
            is_MRET=is_mret_inst,
            Exception_Valid=exception_valid,
            Exception_Code=exception_code,
            Exception_Val=exception_val,
            PC=pc,
            csr_waddr=csr_waddr,
        )

        mem_ctrl_t = mem_ctrl_signals.bundle(
            mem_opcode=acc_mem_op,
            mem_width=acc_mem_wid,
            mem_unsigned=acc_mem_uns,
            wb_ctrl=wb_ctrl_t,
        )

        pre = pre_decode_t.bundle(
            alu_func=acc_alu_func,
            csr_alu_func=acc_csr_alu_func,
            op1_sel=acc_op1_sel,
            op2_sel=acc_op2_sel,
            csr_op_sel=acc_csr_op_sel,
            branch_type=acc_br_type,
            next_pc_addr=next_pc_val,
            mem_ctrl=mem_ctrl_t,
            rs1_data=raw_rs1_data,
            rs2_data=raw_rs2_data,
            imm=acc_imm,
        )

        # 添加日志信息
        log(
            "Control signals: alu_func=0x{:x} op1_sel=0x{:x} op2_sel=0x{:x} branch_type=0x{:x} mem_op=0x{:x} mem_wid=0x{:x} mem_uns=0x{:x} rd=0x{:x} csr_op_sel=0x{:x} csr_alu_op=0x{:x} csr_re=0x{:x} csr_we=0x{:x}",
            acc_alu_func,
            acc_op1_sel,
            acc_op2_sel,
            acc_br_type,
            acc_mem_op,
            acc_mem_wid,
            acc_mem_uns,
            rd,
            acc_csr_op_sel,
            acc_csr_alu_func,
            acc_csr_re,
            acc_csr_we,
        )
        log(
            "Forwarding data: imm=0x{:x} pc=0x{:x} rs1_data=0x{:x} rs2_data=0x{:x} csr_addr=0x{:x}",
            acc_imm,
            pc,
            raw_rs1_data,
            raw_rs2_data,
            csr_addr,
        )
        log(
            "Exception: valid=0x{:x} code=0x{:x} val=0x{:x} is_mret(No Exception Check)=0x{:x}",
            exception_valid,
            exception_code,
            exception_val,
            is_mret_inst,
        )

        # 返回: 预解码包, 冒险检测需要的原始信号
        return pre, rs1, rs2, csr_raddr


class DecoderImpl(Downstream):
    def __init__(self):
        super().__init__()
        self.name = "Decoder_Impl"

    @downstream.combinational
    def build(
        self,
        # --- 1. 来自 Decoder Shell 的静态数据 (Record) ---
        pre: Record,
        # --- 2. 外部模块引用 ---
        executor: Module,
        # --- 3. DataHazardUnit 反馈信号 ---
        rs1_sel: Bits(4),
        rs2_sel: Bits(4),
        csr_sel: Bits(4),
        stall_if: Bits(1),
        # --- 4. Flush 信号 ---
        br_target_pc: Array,
        flush_all_pc: Array,
        # --- 5. CSR 读数据 (来自 CSR File) ---
        csr_data: Bits(32),
    ):
        # 1. 获取输入信号
        mem_ctrl = mem_ctrl_signals.view(pre.mem_ctrl)
        wb_ctrl = wb_ctrl_signals.view(mem_ctrl.wb_ctrl)
        # 计算 NOP 信号
        flush_if = (br_target_pc[0] != Bits(32)(0)) | (flush_all_pc[0] != Bits(32)(0))
        nop_if = flush_if | stall_if

        # 2. 计算控制信号
        exception_valid = nop_if.select(Bits(1)(0), wb_ctrl.Exception_Valid)
        clear_if = exception_valid | nop_if
        id_result_rd = clear_if.select(Bits(5)(0), wb_ctrl.rd_addr)
        id_result_halt_if = clear_if.select(Bits(1)(0), wb_ctrl.halt_if)
        id_result_is_mret = clear_if.select(Bits(1)(0), wb_ctrl.is_MRET)
        id_result_csr_waddr = clear_if.select(Bits(12)(0), wb_ctrl.csr_waddr)
        id_result_mem_opcode = clear_if.select(MemOp.NONE, mem_ctrl.mem_opcode)
        id_result_alu_func = clear_if.select(ALUOp.NOP, pre.alu_func)
        id_result_branch_type = clear_if.select(BranchType.NO_BRANCH, pre.branch_type)

        with Condition(nop_if == Bits(1)(1)):
            log(
                "ID: Inserting NOP (Stall={} Flush={})",
                stall_if == Bits(1)(1),
                flush_if == Bits(1)(1),
            )

        id_result_wb_ctrl = wb_ctrl_signals.bundle(
            rd_addr=id_result_rd,
            halt_if=id_result_halt_if,
            is_MRET=id_result_is_mret,
            Exception_Valid=exception_valid,
            Exception_Code=wb_ctrl.Exception_Code,
            Exception_Val=wb_ctrl.Exception_Val,
            PC=wb_ctrl.PC,
            csr_waddr=id_result_csr_waddr,
        )

        id_result_mem_ctrl = mem_ctrl_signals.bundle(
            mem_opcode=id_result_mem_opcode,
            mem_width=mem_ctrl.mem_width,
            mem_unsigned=mem_ctrl.mem_unsigned,
            wb_ctrl=id_result_wb_ctrl,
        )

        id_result_ex_ctrl = ex_ctrl_signals.bundle(
            alu_func=id_result_alu_func,
            op1_sel=pre.op1_sel,
            op2_sel=pre.op2_sel,
            rs1_sel=rs1_sel,
            rs2_sel=rs2_sel,
            csr_sel=csr_sel,
            csr_op_sel=pre.csr_op_sel,
            csr_alu_func=pre.csr_alu_func,
            branch_type=id_result_branch_type,
            next_pc_addr=pre.next_pc_addr,
            mem_ctrl=id_result_mem_ctrl,
        )

        log(
            "Output: alu_func=0x{:x} rs1_sel=0x{:x} rs2_sel=0x{:x} branch_type=0x{:x} mem_op=0x{:x} rd=0x{:x}",
            id_result_alu_func,
            rs1_sel,
            rs2_sel,
            id_result_branch_type,
            id_result_mem_opcode,
            id_result_rd,
        )

        # 无论是否 Stall，都向 EX 发送数据 (刚性流水线)
        # 如果是 NOP，数据线上的值(pc, imm等)是无意义的，EX 不会使用
        call = executor.async_called(
            ctrl=id_result_ex_ctrl,
            rs1_data=pre.rs1_data,
            rs2_data=pre.rs2_data,
            csr_data=csr_data,
            imm=pre.imm,
        )
        call.bind.set_fifo_depth(
            ctrl=1,
            rs1_data=1,
            rs2_data=1,
            csr_data=1,
            imm=1,
        )
