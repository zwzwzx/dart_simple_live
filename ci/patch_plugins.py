import glob, re, os

cache = os.path.expanduser("~/.pub-cache/hosted/pub.dev")
files = glob.glob(cache + "/*/android/build.gradle.kts") + glob.glob(cache + "/*/android/build.gradle")


def strip_top_kotlin(txt):
    """删掉文件顶层的 kotlin { ... } 块（AGP9 才有的顶层扩展，AGP8.9.1 下未 apply 会报错）。"""
    lines = txt.splitlines(keepends=True)
    out = []
    in_block = False
    depth = 0
    for ln in lines:
        s = ln.strip()
        if not in_block:
            if s.startswith("kotlin {"):
                depth = ln.count("{") - ln.count("}")
                in_block = True
                if depth <= 0:
                    in_block = False
                continue
            out.append(ln)
        else:
            depth += ln.count("{") - ln.count("}")
            if depth <= 0:
                in_block = False
    return "".join(out)


KOTLIN_APPLY = 'apply(plugin = "org.jetbrains.kotlin.android")\n'

for f in files:
    with open(f) as fh:
        txt = fh.read()
    orig = txt

    txt = strip_top_kotlin(txt)
    # 给没 apply kotlin 的插件补上，确保其 Kotlin 源码被编译出类
    if ("kotlin-android" not in txt) and ("org.jetbrains.kotlin.android" not in txt):
        txt = KOTLIN_APPLY + txt
    # AGP9 的 classpath 降回 Flutter 3.38 的 8.9.1
    txt = txt.replace("com.android.tools.build:gradle:9.4.1", "com.android.tools.build:gradle:8.9.1")
    # compileSdk 36 降到 35（AGP8.9 支持范围）
    txt = re.sub(r"compileSdkVersion\s+36\b", "compileSdkVersion 35", txt)
    txt = re.sub(r"compileSdk\s*=\s*36\b", "compileSdk = 35", txt)

    if txt != orig:
        with open(f, "w") as fh:
            fh.write(txt)
        print("patched", f)
    else:
        print("unchanged", f)
print("total plugin gradle files:", len(files))
