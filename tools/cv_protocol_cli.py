import argparse
import sys
import os

# 添加父目录到路径，以便导入 utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import ElectrochemicalProtocol, run_cv_test

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='电化学设备通信协议测试程序')
    parser.add_argument('-p', '--port', help='串口号 (如: COM3 或 /dev/ttyUSB0)')
    parser.add_argument('-b', '--baudrate', type=int, default=115200, help='波特率 (默认: 115200)')
    parser.add_argument('-s', '--simulate', action='store_true', help='使用模拟模式')
    parser.add_argument('--start-v', type=float, default=-1.0, help='起始电位 (V)')
    parser.add_argument('--end-v', type=float, default=1.0, help='结束电位 (V)')
    parser.add_argument('--scan-rate', type=float, default=0.2, help='扫描速率 (V/s)')
    parser.add_argument('--cycles', type=int, default=1, help='循环次数')
    parser.add_argument('--current-range', type=int, default=100, help='电流量程 (μA)')
    parser.add_argument('--save-data', action='store_true', default=True, help='保存数据到CSV文件 (默认: 是)')
    parser.add_argument('--no-save', action='store_false', dest='save_data', help='不保存数据')
    parser.add_argument('--save-plot', action='store_true', default=True, help='保存图形到文件 (默认: 是)')
    parser.add_argument('--no-plot', action='store_false', dest='save_plot', help='不保存图形')
    
    args = parser.parse_args()
    
    # 参数验证
    if not args.simulate and not args.port:
        print("❌ 错误: 请指定串口 (-p) 或使用模拟模式 (-s)")
        print("示例:")
        print("  python cv_protocol.py -s                    # 模拟模式")
        print("  python cv_protocol.py -p COM3               # Windows串口")
        print("  python cv_protocol.py -p /dev/ttyUSB0       # Linux串口")
        return
    
    # 运行测试
    success = run_cv_test(
        port=args.port,
        simulate=args.simulate,
        start_v=args.start_v,
        end_v=args.end_v,
        scan_rate=args.scan_rate,
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
