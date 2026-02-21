import os

src = r"d:\playground\pytron\pytron\engines\chrome"
dst = r"d:\playground\pytron\pytron\engines\servo"
xforms = [
    ("ChromeWebView", "ServoWebView"),
    ("ChromeAdapter", "ServoAdapter"),
    ("ChromeIPCServer", "ServoIPCServer"),
    ("ChromeBridge", "ServoBridge"),
    ("ChromeForge", "ServoForge"),
    ("Chrome Shell", "Servo Shell"),
    ("Chrome", "Servo"),
    ("chrome", "servo"),
    ("Mojo", "ServoNative"),
    ("electron", "miniservo"),
    ("Chromium", "Servo"),
]

os.makedirs(dst, exist_ok=True)
os.makedirs(os.path.join(dst, "shell"), exist_ok=True)

for root, dirs, files in os.walk(src):
    for f in files:
        if f.endswith(".pyc") or f.endswith(".pyo") or f == "__pycache__":
            continue
        rel = os.path.relpath(root, src)
        outdir = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(outdir, exist_ok=True)

        in_path = os.path.join(root, f)
        out_path = os.path.join(outdir, f)

        with open(in_path, "r", encoding="utf-8") as fin:
            content = fin.read()

        for old, new in xforms:
            content = content.replace(old, new)

        with open(out_path, "w", encoding="utf-8") as fout:
            fout.write(content)

print("Done")
