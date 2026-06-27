import os
import sys


def setup_autostart():
    app_dir = os.path.dirname(os.path.abspath(__file__))

    # Use pythonw.exe to avoid console window popping up
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")

    if not os.path.exists(pythonw):
        print(f"错误：找不到 pythonw.exe，路径: {pythonw}")
        print("请确认 Python 安装完整。")
        return

    main_py = os.path.join(app_dir, "main.py")

    # Create VBS launcher (no console window)
    vbs_path = os.path.join(app_dir, "launch.vbs")
    vbs_code = (
        f'CreateObject("Wscript.Shell").Run '
        f'"""{pythonw}"" ""{main_py}""", 0, False'
    )
    with open(vbs_path, "w", encoding="utf-8") as f:
        f.write(vbs_code)

    # Put VBS shortcut in Windows Startup folder
    startup_dir = os.path.join(
        os.environ["APPDATA"],
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
    )

    if not os.path.exists(startup_dir):
        os.makedirs(startup_dir, exist_ok=True)

    startup_vbs = os.path.join(startup_dir, "概念复习.vbs")
    with open(startup_vbs, "w", encoding="utf-8") as f:
        f.write(vbs_code)

    print("✓ 已添加开机自启")
    print(f"  启动脚本: {startup_vbs}")
    print(f"  下次登录时自动打开「概念复习」。")
    print()
    print("如需取消自启，删除此文件即可:")
    print(f"  {startup_vbs}")


if __name__ == "__main__":
    setup_autostart()
