from assassyn.frontend import *
from .control_signals import *


class Fetcher(Module):
    def __init__(self):
        super().__init__(
            ports={}, no_arbiter=True  # Fetcher 是起点，通常不需要被别人 async_called
        )
        self.name = "Fetcher"

    @module.combinational
    def build(self):
        # 1. PC 寄存器
        # 初始化为 0 (Reset Vector)
        pc_reg = RegArray(Bits(32), 1, initializer=[0])
        # 用于驱动 FetcherImpl（Assassyn特性）
        pc_addr = pc_reg[0]
        # 记录上一个周期的PC，用于在 Stall 时稳住输入（Assassyn不允许"不输入"）
        last_pc_reg = RegArray(Bits(32), 1, initializer=[0])

        # 暴露寄存器引用供 Impl 使用
        return pc_reg, pc_addr, last_pc_reg


class FetcherImpl(Downstream):

    def __init__(self):
        super().__init__()
        self.name = "Fetcher_Impl"

    @downstream.combinational
    def build(
        self,
        # --- 资源引用 ---
        pc_reg: Array,  # 引用 Fetcher 的 PC
        pc_addr: Bits(32),  # 引用 Fetcher 的 PC 地址
        last_pc_reg: Array,  # 引用 Fetcher 的 Last PC
        decoder: Module,  # 下一级模块 (用于发送指令)
        # --- 反馈控制信号 (来自 DataHazardUnit/ControlHazardReg) ---
        stall_if: Value,  # 暂停取指 (保持当前 PC)
        branch_target: Array,  # 不为0时，根据目标地址冲刷流水线。
        flush_all_pc: Array,  # 不为0时，跳转到该地址，且优先级高于前者。
        # --- BTB 分支预测 ---
        btb_impl: "BTBImpl",  # BTB 实现逻辑
        btb_valid: Array,  # BTB 有效位数组
        btb_tags: Array,  # BTB 标签数组
        btb_targets: Array,  # BTB 目标地址数组
    ):
        # 1. 判断 Flush 与 Stall 与否
        trap_flush_if = flush_all_pc[0] != Bits(32)(0)
        br_flush_if = branch_target[0] != Bits(32)(0)
        flush_if = trap_flush_if | br_flush_if
        current_stall_if = stall_if.optional(Bits(1)(0))
        with Condition(current_stall_if == Bits(1)(1)):
            log("IF: Stall")
        with Condition(flush_if == Bits(1)(1)):
            log("IF: Flush")

        # 2. 计算当前 PC
        # Trap Flush > Branch Flush > Stall > 正常取指
        stall_pc = current_stall_if.select(last_pc_reg[0], pc_addr)
        flush_pc = trap_flush_if.select(flush_all_pc[0], branch_target[0])
        target_pc = flush_if.select(flush_pc, stall_pc)
        log("IF: Current PC=0x{:x}", target_pc)

        # 3. 异常检测: Ins addr misaligned
        exception_vaild = target_pc[0:1] != Bits(2)(0)
        exception_code = exception_vaild.select(EXC_INST_ADDR_MISALIGNED, Bits(32)(0))
        exception_val = exception_vaild.select(target_pc, Bits(32)(0))

        # 4. 计算 Next PC
        # 使用 BTB 进行分支预测
        btb_hit, btb_predicted_target = btb_impl.predict(
            pc=target_pc,
            btb_valid=btb_valid,
            btb_tags=btb_tags,
            btb_targets=btb_targets,
        )
        # 如果 BTB 命中，使用预测目标；否则默认 PC + 4
        btb_miss_target = (target_pc.bitcast(UInt(32)) + UInt(32)(4)).bitcast(Bits(32))
        predicted_next_pc = btb_hit.select(btb_predicted_target, btb_miss_target)
        # 最终的 Next PC
        next_pc = predicted_next_pc

        # 5. 更新 PC 寄存器
        last_pc_reg[0] <= target_pc
        pc_reg[0] <= next_pc
        log("IF: Next PC=0x{:x}  Next Last PC={:x}", next_pc, target_pc)

        # 6. 驱动下游 Decoder
        # 打包控制信号
        id_ctrl = id_ctrl_signals.bundle(
            PC=target_pc,
            Exception_Valid=exception_vaild,
            Exception_Code=exception_code,
            Exception_Val=exception_val,
            stall_if=current_stall_if,
        )
        # 发送到下一级，传递 PC 值与 Stall 信号（使用上一周期指令信号）
        call = decoder.async_called(
            ctrl=id_ctrl,
            next_pc=next_pc,
        )
        call.bind.set_fifo_depth(ctrl=1,next_pc=1)

        return target_pc
