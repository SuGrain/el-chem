#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""DPV 协议测试程序命令行工具"""

import argparse
import sys
import os

# 添加父目录到路径，以便导入 utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import DPVProtocol, run_dpv_test


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='差分脉冲伏安法 (DPV) 测试程序')
    parser.add_argument('-p', '--port', help='串口号 (如: COM3 或 /dev/ttyUSB0)')
    parser.add_argument('-b', '--baudrate', type=int, default=115200, help='波特率 (默认: 115200)')
    parser.add_argument('-s', '--simulate', action='store_true', help='使用模拟模式')
    parser.add_argument('--start-v', type=float, default=-1.0, help='起始电位 (V)')
    parser.add_argument('--end-v', type=float, default=1.0, help='结束电位 (V)')
    parser.add_argument('--pulse-height', type=float, default=0.1, help='脉冲幅度 (V)')
    parser.add_argument('--pulse-width', type=int, default=10, help='脉冲宽度 (ms)')
    parser.add_argument('--pulse-period', type=int, default=10, help='脉冲周期 (ms)')
    parser.add_argument('--sample-width', type=int, default=20, help='采样窗口宽度 (ms)')
    parser.add_argument('--cycles', type=int, default=2, help='循环次数')
    parser.add_argument('--current-range', type=int, default=50, help='电流量程 (μA)')
    parser.add_argument('--save-data', action='store_true', default=True, help='保存数据到CSV文件 (默认: 是)')
    parser.add_argument('--no-save', action='store_false', dest='save_data', help='不保存数据')
    parser.add_argument('--save-plot', action='store_true', default=True, help='保存图形到文件 (默认: 是)')
    parser.add_argument('--no-plot', action='store_false', dest='save_plot', help='不保存图形')
    
    args = parser.parse_args()
    
    # 参数验证
    if not args.simulate and not args.port:
        print("❌ 错误: 请指定串口 (-p) 或使用模拟模式 (-s)")
        print("示例:")
        print("  python dpv_protocol_cli.py -s                    # 模拟模式")
        print("  python dpv_protocol_cli.py -p COM3               # Windows串口")
        print("  python dpv_protocol_cli.py -p /dev/ttyUSB0       # Linux串口")
        return
    
    # 运行测试
    success = run_dpv_test(
        port=args.port,
        simulate=args.simulate,
        start_v=args.start_v,
        end_v=args.end_v,
        pulse_height=args.pulse_height,
        pulse_width=args.pulse_width,
        pulse_period=args.pulse_period,
        sample_width=args.sample_width,
        cycles=args.cycles,
        current_range=args.current_range,
        save_data=args.save_data,
        save_plot=args.save_plot
    )
    
    if not success:
        print("❌ 测试失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
