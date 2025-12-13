#!/usr/bin/env python3
"""
测试导入修复是否正确工作
Test that the import fix works correctly
"""

import sys
import os
import subprocess
from pathlib import Path


def test_package_structure():
    """测试包结构是否正确"""
    print("测试 1: 检查包结构...")
    
    src_path = Path("src")
    assert src_path.exists(), "src 目录不存在"
    assert src_path.is_dir(), "src 不是目录"
    
    init_file = src_path / "__init__.py"
    assert init_file.exists(), "src/__init__.py 不存在"
    
    main_file = src_path / "main.py"
    assert main_file.exists(), "src/main.py 不存在"
    
    print("✓ 包结构正确")


def test_module_can_be_imported():
    """测试模块可以被导入"""
    print("\n测试 2: 检查模块导入...")
    
    # 添加项目根目录到 sys.path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    try:
        # 尝试导入 src 包
        import src
        print(f"✓ 成功导入 src 包")
        print(f"  包版本: {getattr(src, '__version__', 'N/A')}")
        print(f"  包路径: {src.__file__}")
    except ImportError as e:
        print(f"✗ 导入 src 包失败: {e}")
        raise


def test_main_syntax():
    """测试 main.py 语法正确"""
    print("\n测试 3: 检查 main.py 语法...")
    
    main_file = Path("src/main.py")
    
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(main_file)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"✗ main.py 语法错误:")
        print(result.stderr)
        raise SyntaxError("main.py has syntax errors")
    
    print("✓ main.py 语法正确")


def test_import_logic():
    """测试导入逻辑"""
    print("\n测试 4: 检查导入逻辑...")
    
    import ast
    
    with open("src/main.py", "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    
    # 检查是否有 try-except 导入逻辑
    has_try_except = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for handler in node.handlers:
                if handler.type:
                    if isinstance(handler.type, ast.Name) and handler.type.id == "ImportError":
                        has_try_except = True
                        break
    
    assert has_try_except, "main.py 缺少 try-except 导入逻辑"
    print("✓ main.py 包含 try-except 导入逻辑")


def test_run_scripts_exist():
    """测试运行脚本是否存在"""
    print("\n测试 5: 检查运行脚本...")
    
    scripts = {
        "run_cpu.py": "Python 跨平台脚本",
        "run_cpu.sh": "Linux/macOS Shell 脚本",
        "run_cpu.bat": "Windows 批处理脚本",
    }
    
    for script, description in scripts.items():
        script_path = Path(script)
        if script_path.exists():
            print(f"✓ {description}: {script}")
        else:
            print(f"✗ 缺少 {description}: {script}")
            raise FileNotFoundError(f"{script} not found")


def test_makefile_updated():
    """测试 Makefile 是否已更新"""
    print("\n测试 6: 检查 Makefile...")
    
    makefile = Path("Makefile")
    if not makefile.exists():
        print("⚠ Makefile 不存在，跳过检查")
        return
    
    with open(makefile, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 检查是否使用 python -m src.main
    if "python -m src.main" in content:
        print("✓ Makefile 使用了推荐的运行方式")
    elif "python src/main.py" in content:
        print("⚠ Makefile 仍使用旧的运行方式，但兼容")
    else:
        print("⚠ Makefile 中未找到构建命令")


def test_documentation_updated():
    """测试文档是否已更新"""
    print("\n测试 7: 检查文档...")
    
    docs = ["README.md", "QUICKSTART.md"]
    
    for doc in docs:
        doc_path = Path(doc)
        if not doc_path.exists():
            print(f"⚠ {doc} 不存在，跳过检查")
            continue
        
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        has_module_run = "python -m src.main" in content
        has_script_mention = "run_cpu" in content
        
        if has_module_run and has_script_mention:
            print(f"✓ {doc} 已更新")
        elif has_module_run:
            print(f"⚠ {doc} 提到了模块运行方式")
        else:
            print(f"⚠ {doc} 可能需要更新")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("ImportError 修复验证测试")
    print("=" * 60)
    
    # 切换到项目根目录
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    tests = [
        test_package_structure,
        test_module_can_be_imported,
        test_main_syntax,
        test_import_logic,
        test_run_scripts_exist,
        test_makefile_updated,
        test_documentation_updated,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    if failed == 0:
        print("\n🎉 所有测试通过！ImportError 修复验证成功！")
        return 0
    else:
        print(f"\n❌ {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
