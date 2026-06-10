import pyautogui
import time
import os
import ctypes
import threading

# ========== 基础配置 ==========
pyautogui.FAILSAFE = True          # 鼠标移到屏幕角落 → 紧急停止

SUN_FOLDER = r"C:\Users\13170\PycharmProjects\gametest\PythonPlantsVsZombies-master\resources\graphics\Plants\Sun"

# ========== 全局状态 ==========
ENABLED = True
EXIT_FLAG = False
state_lock = threading.Lock()

# ========== 屏幕区域 ==========
screen_width, screen_height = pyautogui.size()
# 卡片槽在游戏顶部区域，排除顶部 12% 避免误触植物卡片
EXCLUDE_TOP_RATIO = 0.12
SEARCH_TOP = max(int(screen_height * EXCLUDE_TOP_RATIO), 80)
SEARCH_REGION = (0, SEARCH_TOP, screen_width, screen_height - SEARCH_TOP)

# ========== Windows API ==========
user32 = ctypes.windll.user32

VK_SHIFT  = 0x10
VK_CTRL   = 0x11
VK_Q      = 0x51


# ---------------------------------------------------------------------------
# 键盘监控线程（独立线程，20ms 轮询）
# ---------------------------------------------------------------------------
def keyboard_monitor():
    """不依赖第三方库，用 Win32 GetAsyncKeyState 检测按键"""
    global ENABLED, EXIT_FLAG

    shift_was_down = False

    while True:
        # ---- Shift 暂停/恢复（上升沿检测） ----
        shift_is_down = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
        if shift_is_down and not shift_was_down:
            with state_lock:
                ENABLED = not ENABLED
                if ENABLED:
                    print("\n 脚本已恢复运行")
                else:
                    print("\n脚本已暂停（鼠标完全由你控制）")
        shift_was_down = shift_is_down

        # ---- Ctrl+Shift+Q 紧急退出 ----
        ctrl  = bool(user32.GetAsyncKeyState(VK_CTRL)  & 0x8000)
        shift = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
        q     = bool(user32.GetAsyncKeyState(VK_Q)     & 0x8000)
        if ctrl and shift and q:
            EXIT_FLAG = True

        time.sleep(0.02)


# ---------------------------------------------------------------------------
# 智能点击 —— 瞬移 → 点击 → 恢复鼠标位置
# ---------------------------------------------------------------------------
def smart_click(x, y):
    """
    瞬移到目标 → 按下 → 停留 → 抬起 → 恢复鼠标位置。
    每个环节都留足时间让游戏响应，总耗时约 70ms，用户几乎无感。
    """
    orig_x, orig_y = pyautogui.position()

    # 1. 瞬移到阳光位置
    pyautogui.moveTo(x, y)
    time.sleep(0.015)          # 等光标落稳

    # 2. 模拟真实点击：按下 → 停留 → 抬起
    pyautogui.mouseDown()
    time.sleep(0.04)           # 停留 40ms，确保游戏接收到按下事件
    pyautogui.mouseUp()
    time.sleep(0.015)          # 等游戏处理完抬起事件，再移走光标

    # 3. 恢复鼠标位置
    pyautogui.moveTo(orig_x, orig_y)


# ---------------------------------------------------------------------------
# 阳光检测与拾取
# ---------------------------------------------------------------------------
def find_and_click_sun():
    """在游戏草坪区域搜索阳光并点击"""
    if not os.path.exists(SUN_FOLDER):
        return False

    sun_images = [
        f for f in os.listdir(SUN_FOLDER)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]
    if not sun_images:
        return False

    for img_file in sun_images:
        img_path = os.path.join(SUN_FOLDER, img_file)

        try:
            # 只在草坪区域搜索，彩色匹配（阳光黄色是关键特征）
            location = pyautogui.locateOnScreen(
                img_path,
                confidence=0.65,
                region=SEARCH_REGION,
            )
            if not location:
                continue

            x, y = pyautogui.center(location)

            # 每次操作前检查是否已暂停
            if not ENABLED or EXIT_FLAG:
                return False

            # 第一次点击
            print(f"☀发现阳光 ({x}, {y})，点击中…")
            smart_click(x, y)
            time.sleep(0.08)

            # 确认阳光是否已消失
            if not pyautogui.locateOnScreen(
                img_path, confidence=0.65, region=SEARCH_REGION
            ):
                print("收集成功")
                return True

            # 阳光还在（可能在下落），再追踪 2 次
            for attempt in range(2):
                if not ENABLED or EXIT_FLAG:
                    return False

                new_loc = pyautogui.locateOnScreen(
                    img_path, confidence=0.65, region=SEARCH_REGION
                )
                if not new_loc:
                    print("收集成功")
                    return True

                nx, ny = pyautogui.center(new_loc)
                print(f"   追踪中… ({nx}, {ny})")
                smart_click(nx, ny)
                time.sleep(0.06)

            return True

        except Exception:
            pass

    return False


# ---------------------------------------------------------------------------
# 主循环
# ---------------------------------------------------------------------------
def main():
    # 启动键盘监控线程
    monitor_thread = threading.Thread(target=keyboard_monitor, daemon=True)
    monitor_thread.start()

    print("=" * 55)
    print("阳光自动拾取脚本（改进版 v3）")
    print("=" * 55)
    print(" 改进内容：")
    print("  1. 独立键盘监听线程 — 暂停/恢复即时响应")
    print("  2. 排除卡片槽区域 — 不会误触植物卡片")
    print("  3. 瞬移点击 — 点击后立即恢复鼠标位置")
    print("  4. 彩色匹配 — 保留阳光黄色特征，识别更准")
    print("  5. 使用 pyautogui.click — 确保游戏正确响应点击")
    print("=" * 55)
    print("🛡 安全控制：")
    print("  - 按 Shift          → 暂停/恢复脚本")
    print("  - 按 Ctrl+Shift+Q   → 紧急退出")
    print("  - 鼠标移到屏幕角落  → 紧急停止（FAILSAFE）")
    print("  - 按 Ctrl+C         → 正常退出")
    print("=" * 55)
    print(f"屏幕分辨率：{screen_width}x{screen_height}")
    print(f"搜索排除：顶部 0 ~ {SEARCH_TOP}px（卡片槽区域）")
    print(f"匹配置信度：0.65（彩色匹配）")
    print("=" * 55)
    print("脚本将在 3 秒后启动…")
    time.sleep(3)
    print(" 脚本运行中…\n")
    print(" 按 Shift 可随时暂停\n")

    try:
        while True:
            if EXIT_FLAG:
                print("\n🛑 紧急退出 (Ctrl+Shift+Q)")
                break

            if not ENABLED:
                time.sleep(0.05)
                continue

            found = find_and_click_sun()
            if found:
                time.sleep(0.3)
            else:
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n用户手动停止 (Ctrl+C)")
    except pyautogui.FailSafeException:
        print("\nFAILSAFE 触发：鼠标移至屏幕角落")
    except Exception as e:
        print(f"\n 发生错误：{e}")
        import traceback
        traceback.print_exc()

    print("脚本已安全停止")


if __name__ == "__main__":
    main()
