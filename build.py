import sys
import os
import subprocess

BUILD_DIR = "build"
COMPILER_SCRIPT = "main_compiler.py"
RUNTIME_SRC = "runtime.c"

OUTPUT_IR = os.path.join(BUILD_DIR, "output.ll")
RUNTIME_OBJ = os.path.join(BUILD_DIR, "runtime.obj")
PROGRAM_OBJ = os.path.join(BUILD_DIR, "program.obj")
OUTPUT_EXE = os.path.join(BUILD_DIR, "program.exe")

def print_step(msg):
    print(f"\n[BUILD] === {msg} ===")

def ensure_build_dir():
    if not os.path.exists(BUILD_DIR):
        os.makedirs(BUILD_DIR)
        print(f"[BUILD] Создана папка: {BUILD_DIR}")

def run_command(cmd):
    print(f"Exec: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, shell=(os.name == 'nt'))
    except subprocess.CalledProcessError:
        print(f"❌ ОШИБКА при выполнении команды.")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Использование: python build.py <файл_кода.dsl>")
        sys.exit(1)

    source_file = sys.argv[1]
    ensure_build_dir()
    
    # Zig через python модуль
    zig_cc = [sys.executable, "-m", "ziglang", "cc"]

    # 1. Генерация LLVM IR (передаем путь сохранения аргументом)
    print_step(f"1. Компиляция DSL: {source_file} -> {OUTPUT_IR}")
    run_command([sys.executable, COMPILER_SCRIPT, source_file, OUTPUT_IR])

    # 2. Компиляция Runtime (C -> OBJ)
    print_step(f"2. Компиляция Runtime: {RUNTIME_SRC} -> {RUNTIME_OBJ}")
    run_command(zig_cc + ["-c", RUNTIME_SRC, "-o", RUNTIME_OBJ, "-target", "x86_64-windows-gnu"])

    # 3. Компиляция IR (LL -> OBJ)
    print_step(f"3. Компиляция IR: {OUTPUT_IR} -> {PROGRAM_OBJ}")
    run_command(zig_cc + ["-c", OUTPUT_IR, "-o", PROGRAM_OBJ, "-Wno-override-module"])

    # 4. Линковка (OBJ + OBJ -> EXE)
    print_step(f"4. Линковка: {PROGRAM_OBJ} + {RUNTIME_OBJ} -> {OUTPUT_EXE}")
    run_command(zig_cc + [PROGRAM_OBJ, RUNTIME_OBJ, "-o", OUTPUT_EXE])

    print_step("Сборка успешно завершена! ✅")
    
    # 5. Запуск
    print_step(f"Запуск {OUTPUT_EXE}")
    print("-" * 40)
    subprocess.run([os.path.abspath(OUTPUT_EXE)], shell=(os.name == 'nt'))
    print("-" * 40)

if __name__ == "__main__":
    main()