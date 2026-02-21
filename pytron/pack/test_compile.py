import subprocess
import sys


def try_compile():
    cmd = [
        "zig",
        "cc",
        "test.c",
        "-o",
        "test.exe",
        "-target",
        "x86_64-windows-msvc",
        "-Wl,/DELAYLOAD:python313.dll",
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("Return code:", result.returncode)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    cmd2 = [
        "zig",
        "build-exe",
        "test.c",
        "-target",
        "x86_64-windows-msvc",
        "-lc",
        "-Wl,/DELAYLOAD:python313.dll",
    ]
    print(f"\nRunning: {' '.join(cmd2)}")
    result2 = subprocess.run(cmd2, capture_output=True, text=True)
    print("Return code:", result2.returncode)
    print("STDOUT:", result2.stdout)
    print("STDERR:", result2.stderr)


if __name__ == "__main__":
    try_compile()
