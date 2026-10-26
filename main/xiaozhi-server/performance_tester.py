import os
import importlib.util
import asyncio

print("使用前请根据仓库根目录下 docs/performance_tester.md 的说明准备配置。")


def list_performance_tester_modules():
    performance_tester_dir = os.path.join(
        os.path.dirname(__file__), "performance_tester"
    )
    modules = []
    for file in os.listdir(performance_tester_dir):
        if file.endswith(".py"):
            modules.append(file[:-3])
    return modules


async def load_and_execute_module(module_name):
    module_path = os.path.join(
        os.path.dirname(__file__), "performance_tester", f"{module_name}.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "main"):
        main_func = module.main
        if asyncio.iscoroutinefunction(main_func):
            await main_func()
        else:
            main_func()
    else:
        print(f"模块 {module_name} 中没有找到 main 函数。")


def get_module_description(module_name):
    module_path = os.path.join(
        os.path.dirname(__file__), "performance_tester", f"{module_name}.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "description", "暂无描述")


def main():
    modules = list_performance_tester_modules()
    if not modules:
        print("performance_tester 目录中没有可用的性能测试工具。")
        return

    print("可用的性能测试工具：")
    for idx, module in enumerate(modules, 1):
        description = get_module_description(module)
        print(f"{idx}. {module} - {description}")

    try:
        choice = int(input("请选择要调用的性能测试工具编号：")) - 1
        if 0 <= choice < len(modules):
            asyncio.run(load_and_execute_module(modules[choice]))
        else:
            print("无效的选择。")
    except ValueError:
        print("请输入有效的数字。")


if __name__ == "__main__":
    main()
