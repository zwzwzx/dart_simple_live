import glob, re, os

# 扫 pub-cache 里所有插件的 android gradle（kts + groovy），统一降级到 Flutter 3.38 的 AGP8.9.1
cache = os.path.expanduser("~/.pub-cache/hosted/pub.dev")
files = glob.glob(cache + "/*/android/build.gradle.kts") + glob.glob(cache + "/*/android/build.gradle")


def strip_top_kotlin(txt):
    """删掉文件顶层的 kotlin { ... } 块（AGP9 专用顶层扩展，AGP8.9.1 下未 apply 会报错）。"""
    lines = txt.splitlines(keepends=True)
    out, in_block, depth = [], False, 0
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


def has_kotlin_src(android_dir):
    """该插件 android 目录是否有 .kt 源码（有则必须 apply kotlin 才会被编译出类）。"""
    for root, _, fnames in os.walk(android_dir):
        for n in fnames:
            if n.endswith(".kt"):
                return True
    return False


for f in files:
    with open(f) as fh:
        txt = fh.read()
    orig = txt

    # 1) 删 AGP9 顶层 kotlin{} 块
    txt = strip_top_kotlin(txt)

    # 2) 只对「含 Kotlin 源码 且 还没 apply kotlin」的插件补 apply（副作用最小化）
    is_kts = f.endswith(".kts")
    android_dir = os.path.dirname(f)
    already = ("kotlin-android" in txt) or ("org.jetbrains.kotlin.android" in txt)
    if (not already) and has_kotlin_src(android_dir):
        if is_kts:
            # Kotlin DSL 写法
            txt = 'apply(plugin = "org.jetbrains.kotlin.android")\n' + txt
        else:
            # Groovy 写法（冒号形式）：插到 com.android apply 之后，没有就插顶部
            marker = "apply plugin: 'com.android.library'"
            if marker in txt:
                txt = txt.replace(
                    marker,
                    marker + "\napply plugin: 'org.jetbrains.kotlin.android'",
                    1,
                )
            else:
                txt = "apply plugin: 'org.jetbrains.kotlin.android'\n" + txt

    # 3) AGP9 的 classpath 降回 Flutter 3.38 的 8.9.1
    txt = txt.replace("com.android.tools.build:gradle:9.4.1", "com.android.tools.build:gradle:8.9.1")
    # 4) compileSdk 36 降到 35（AGP8.9 支持范围）
    txt = re.sub(r"compileSdkVersion\s+36\b", "compileSdkVersion 35", txt)
    txt = re.sub(r"compileSdk\s*=\s*36\b", "compileSdk = 35", txt)

    if txt != orig:
        with open(f, "w") as fh:
            fh.write(txt)
        print("patched", f)
    else:
        print("unchanged", f)
print("total plugin gradle files:", len(files))
