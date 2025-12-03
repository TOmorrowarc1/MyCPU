这是一份更新后的 **AI Agent 开发指导文档**。

我已将 **Apptainer 容器化运行环境** 的要求深度整合到工作流中，重点修改了 **环境配置** 和 **测试运行** 章节。请将以下完整内容作为 Prompt 发送给 Agent。

---

# 指导文档：Assassyn RV32I 五级流水线 CPU 实现指南 (Containerized)

**角色定义**：你是一名精通 Python 元编程、计算机体系结构及容器化开发的硬件工程师。
**任务目标**：基于 `Assassyn` 框架，按照设计文档逐步实现一个 RV32I 处理器。**特别注意：所有代码的执行、仿真与验证必须在 Apptainer 容器环境中进行。**



## 1. 核心设计文档位置 (Context)

请严格参考以下已确认的设计逻辑（Context）：
*   **IF 阶段**：[IF与IFImpl分离设计文档] - 关注 `Flush > Stall > Normal` 优先级与 `Next_PC` 预计算。
*   **ID 阶段**：[ID模块设计文档] - 关注 `Record` 分层打包、`DataHazardUnit` 的真值回传机制、以及 `instructions_table` 查表实现。
*   **EX 阶段**：[EX模块设计文档] - 关注 `Main ALU` (数据/Link) 和 `Target Adder` (跳转目标) 的交叉调度。
*   **MEM 阶段**：[MEM模块设计文档] - 关注 `pop_all_ports` 解包、SRAM 数据对齐逻辑。
*   **WB 阶段**：[WB模块设计文档] - 关注极简接口与 `x0` 写保护。

## 2. 目标代码写入地址 (File Structure)

所有代码必须严格写入以下路径：

```text
riscv_cpu/
├── assassyn.sif          # [关键] Apptainer 容器镜像
├── src/                  # 源代码目录
│   ├── __init__.py
│   ├── consts.py         # 常量定义 (ALUOp, Op1Sel, etc.)
│   ├── interfaces.py     # 接口定义 (Record, Port)
│   ├── fetch.py          # IF 阶段
│   ├── decode.py         # ID 阶段 (含 HazardUnit)
│   ├── execute.py        # EX 阶段
│   ├── memory.py         # MEM 阶段
│   ├── writeback.py      # WB 阶段
│   └── top.py            # 顶层集成
└── tests/                # 测试代码目录
    ├── common.py         # 通用测试工具
    ├── test_fetch.py     # 各模块单元测试
    └── ...
```

## 3. 如何使用测试平台 (Workflow with Apptainer)

**这是与传统开发最大的不同点。** 你不能直接使用 `python` 命令，必须通过 `apptainer` 包装器。

### 3.1 编写测试驱动 (`tests/common.py`)
代码编写逻辑不变，依然使用 `run_simulator`。Assassyn 库在容器内会自动调用容器内的 Verilator。

### 3.2 运行测试 (Execution Command)

当你需要运行测试脚本（例如 `tests/test_fetch.py`）时，请使用以下指令格式：

```bash
# 格式：apptainer exec --bind <宿主机代码目录> <镜像路径> python <脚本路径>

# 示例（假设在 riscv_cpu 根目录下运行）：
apptainer exec --bind $(pwd) /tmp/assassyn.sif python tests/test_fetch.py
```

*   **`--bind $(pwd)`**: 极其重要！这将当前目录挂载到容器内，确保 Python 能找到 `src` 和 `tests` 模块。
*   **验证标准**：如果终端输出了 Assassyn 的 Logo 和仿真日志（`log()` 内容），说明容器调用成功。

## 4. 分步开发路线图 (Roadmap)

请按以下顺序执行开发。**每完成一步，必须生成对应的测试代码，并给出在该容器环境下运行成功的确认。**

### Phase 1: 基础设施 (Infrastructure)
1.  **定义常量 (`src/consts.py`)**：定义 `ALUOp`, `Op1Sel`, `ImmType` 等。
2.  **定义接口 (`src/interfaces.py`)**：实现 `wb_ctrl_t` -> `mem_ctrl_t` -> `ex_ctrl_t` -> `decode_packet_t` 的嵌套 Record。

### Phase 2: 取指与状态 (Fetch)
1.  **实现 IF (`src/fetch.py`)**：编写 `Fetcher` 和 `FetcherImpl`。
2.  **测试 IF**：编写 `tests/test_fetch.py`。
    *   *运行指令*: `apptainer exec --bind $(pwd) assassyn.sif python tests/test_fetch.py`

### Phase 3: 译码与冒险 (Decode)
1.  **实现 Hazard (`src/decode.py`)**：编写 `DataHazardUnit` (Downstream)。
2.  **实现 ID (`src/decode.py`)**：编写 `Decoder`，集成指令真值表。
3.  **测试 ID**：验证控制信号生成与 Stall 逻辑。

### Phase 4: 执行 (Execute)
1.  **实现 EX (`src/execute.py`)**：实现 `Execution`，重点在于 Mux 的选择逻辑与两个加法器的调度。
2.  **测试 EX**：验证算术运算、跳转目标计算及 Forwarding Mux 选择。

### Phase 5: 访存与写回 (Mem & WB)
1.  **实现 MEM (`src/memory.py`)**：实现数据对齐。
2.  **实现 WB (`src/writeback.py`)**：实现寄存器写入。
3.  **测试 MEM/WB**：验证 Load 数据通路。

### Phase 6: 系统集成 (Top)
1.  **实现 Top (`src/top.py`)**：连接所有模块与全局反馈寄存器。
2.  **集成测试**：在容器中运行完整的指令集测试。

---

**特别提示**：
*   如果遇到 `ModuleNotFoundError`，请检查 `apptainer` 命令中是否遗漏了 `--bind` 参数，或者 `PYTHONPATH` 设置。
*   Assassyn 的 `elaborate` 过程会在容器内生成临时的 C++ 文件，确保挂载的目录具有**写权限**。

**现在，请从 Phase 1 开始编码。**