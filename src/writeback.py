from assassyn.frontend import *

# 定义WB控制信号结构
wb_ctrl_t = Record(
    # 对于 Store, Branch 等不需要写回的指令，Decoder 保证 rd_addr == 0
    rd_addr = Bits(5)
)

class WriteBack(Module):
    
    def __init__(self):
        super().__init__(
            ports={
                # 控制通路：包含 rd_addr
                'ctrl': Port(wb_ctrl_t),
                
                # 数据通路：来自 MEM 级的最终结果 (Mux 后的结果)
                'wdata': Port(Bits(32))
            }
        )
        self.name = 'WB'

    @module.combinational
    def build(self, reg_file: Array):
        # 1. 获取输入 (Consume)
        # 从 MEM->WB 的 FIFO 中弹出数据
        # 由于采用刚性流水线（NOP注入），这里假定总是能 pop 到数据
        ctrl, wdata = self.pop_all_ports(False)
        
        # 使用.optional()处理可能无效的数据
        ctrl_valid = ctrl.optional(wb_ctrl_t())
        wdata_valid = wdata.optional(Bits(32)(0))
        
        rd = ctrl_valid.rd_addr

        # 2. 写入逻辑 (Write Logic)
        # 物理含义：生成寄存器堆的 Write Enable 信号
        # 只有当目标寄存器不是 x0 时，才允许写入
        with Condition(rd != Bits(5)(0)):
            # 调试日志：打印写回操作
            log("WB: Write x{} <= 0x{:x}", rd, wdata_valid)
            
            # 驱动寄存器堆的 D 端和 WE 端
            reg_file[rd] = wdata_valid

        # 3. 状态反馈 (Feedback to Hazard Unit)
        # 将当前的 rd 返回，供 DataHazardUnit (Downstream) 使用
        return rd