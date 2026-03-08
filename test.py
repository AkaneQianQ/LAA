"""
Ferrum 硬件连接与账号TAG截图测试脚本

功能：
1. 连接 Ferrum 硬件设备（KMBox）
2. 等待2秒后按下 ESC 键
3. 截取账号 TAG 区域
4. 保存截图并输出信息
"""

import time
import os
import sys
import cv2
import numpy as np
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.ferrum_controller import FerrumController, FerrumConnectionError
from core.vision_engine import VisionEngine


# 账号TAG截图区域 ROI (from character_detector.py)
ACCOUNT_TAG_ROI = (666, 793, 772, 902)  # (x1, y1, x2, y2)


def phash(image, hash_size=8):
    """
    感知哈希 (pHash) - 用于图像相似度比较

    算法步骤:
    1. 转换为灰度图
    2. 缩放为 32x32
    3. DCT变换取低频部分
    4. 与平均值比较生成二进制哈希

    Args:
        image: BGR图像
        hash_size: 哈希大小 (默认8)

    Returns:
        二进制哈希字符串
    """
    # 转换为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # 缩放为 32x32
    resized = cv2.resize(gray, (32, 32))
    # DCT变换
    dct = cv2.dct(np.float32(resized))
    # 取低频部分
    dct_low = dct[:hash_size, :hash_size]
    # 计算平均值（排除直流分量）
    avg = (dct_low.sum() - dct_low[0, 0]) / (hash_size * hash_size - 1)
    # 生成哈希
    hash_str = ''
    for i in range(hash_size):
        for j in range(hash_size):
            if i == 0 and j == 0:
                continue
            hash_str += '1' if dct_low[i, j] > avg else '0'
    return hash_str


def hamming_distance(hash1, hash2):
    """
    计算两个哈希之间的汉明距离

    Args:
        hash1: 哈希字符串1
        hash2: 哈希字符串2

    Returns:
        汉明距离 (不同位的数量)
    """
    return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))


def main():
    print("=" * 50)
    print("Ferrum 硬件连接与账号TAG截图测试")
    print("=" * 50)
    print()

    ferrum = None
    vision = None

    try:
        # Step 1: 连接 Ferrum 设备
        print("[1/4] 正在连接 Ferrum 硬件设备...")
        print(f"      端口: COM2, 波特率: 115200")

        try:
            ferrum = FerrumController(port="COM2", baudrate=115200, timeout=1.0)
            if ferrum.is_connected():
                print(f"      [OK] Ferrum 设备连接成功!")
                print(f"      [OK] 设备已初始化 (km.init() 执行完成)")
            else:
                print(f"      [FAIL] Ferrum 设备连接失败: 未知状态")
                return
        except FerrumConnectionError as e:
            print(f"      [FAIL] Ferrum 设备连接失败: {e}")
            print(f"\n      请检查:")
            print(f"        - KMBox 设备是否已连接到电脑")
            print(f"        - 设备管理器中是否显示 COM 端口")
            print(f"        - 端口号是否正确 (默认 COM2)")
            return
        except Exception as e:
            print(f"      [FAIL] 连接过程中发生错误: {e}")
            return

        print()

        # Step 2: 等待2秒后按 ESC
        print("[2/4] 等待2秒后按下 ESC 键...")
        print(f"      倒计时: 2秒")
        time.sleep(2)

        print(f"      发送 ESC 按键...")
        ferrum.press("esc")
        print(f"      [OK] ESC 按键已发送")

        print()

        # Step 3: 等待ESC菜单打开并截图
        print("[3/4] 等待 ESC 菜单打开并截取账号TAG...")
        print(f"      等待 1 秒让菜单稳定...")
        time.sleep(1)

        # 初始化 VisionEngine 进行截图
        vision = VisionEngine()
        print(f"      正在截取屏幕...")
        screenshot = vision.get_screenshot(force_fresh=True)
        print(f"      [OK] 屏幕截图完成，尺寸: {screenshot.shape}")

        # Step 4: 截取账号 TAG 区域
        print()
        print("[4/4] 截取并保存账号TAG...")
        x1, y1, x2, y2 = ACCOUNT_TAG_ROI
        tag_screenshot = screenshot[y1:y2, x1:x2]
        print(f"      TAG区域: ({x1}, {y1}, {x2}, {y2})")
        print(f"      TAG尺寸: {tag_screenshot.shape}")

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "data/test_screenshots"
        os.makedirs(output_dir, exist_ok=True)

        # 保存完整截图
        full_path = os.path.join(output_dir, f"full_screen_{timestamp}.png")
        cv2.imwrite(full_path, screenshot)
        print(f"      [OK] 完整截图已保存: {full_path}")

        # 保存 TAG 截图
        tag_path = os.path.join(output_dir, f"account_tag_{timestamp}.png")
        cv2.imwrite(tag_path, tag_screenshot)
        print(f"      [OK] 账号TAG已保存: {tag_path}")

        # 计算 TAG 的感知哈希 (用于账号识别)
        tag_phash = phash(tag_screenshot)
        print(f"      [OK] 账号TAG pHash: {tag_phash[:32]}...")
        print(f"      [INFO] pHash长度: {len(tag_phash)}位")

        print()
        print("=" * 50)
        print("测试完成!")
        print("=" * 50)
        print(f"\n截图文件保存在: {os.path.abspath(output_dir)}")
        print(f"  - 完整截图: {os.path.basename(full_path)}")
        print(f"  - TAG截图: {os.path.basename(tag_path)}")

    except KeyboardInterrupt:
        print("\n\n[!] 用户中断测试")
    except Exception as e:
        print(f"\n[!] 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        if ferrum:
            print("\n[清理] 关闭 Ferrum 设备连接...")
            ferrum.close()
            print("       [OK] 设备已关闭")


if __name__ == "__main__":
    main()
    input("\n按 Enter 键退出...")
