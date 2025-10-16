#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""串口 HEX 日志分析工具"""

import os
import csv
from pathlib import Path


def parse_hex_log(log_file):
    """
    解析串口 HEX 日志文件
    
    Args:
        log_file: 日志文件路径
        
    Returns:
        (发送数据, 接收数据) 元组
    """
    with open(log_file, 'r') as f:
        lines = f.readlines()
    
    data_to_send = []
    data_to_recv = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        parts = line.split()
        if len(parts) >= 3:
            direction = parts[1]  # VIRT->REAL 或 REAL->VIRT
            hex_value = parts[2]
            
            try:
                char = chr(int(hex_value, 16))
                if direction == "VIRT->REAL":
                    data_to_send.append(char)
                else:
                    data_to_recv.append(char)
            except:
                pass
    
    return ''.join(data_to_send), ''.join(data_to_recv)


def analyze_dpv_protocol(send_data, recv_data):
    """
    分析 DPV 通信协议
    
    Args:
        send_data: 发送的数据字符串
        recv_data: 接收的数据字符串
        
    Returns:
        分析结果字典
    """
    result = {
        'command': None,
        'parameters': [],
        'responses': [],
        'data_points': [],
        'statistics': {}
    }
    
    # 解析发送命令
    if send_data:
        cmd_line = send_data.split('\r\n')[0]
        result['command'] = cmd_line
        
        # 提取参数
        if cmd_line.startswith('P'):
            params = cmd_line[2:].split(',')
            result['parameters'] = [p.strip() for p in params if p.strip()]
    
    # 解析响应
    if recv_data:
        lines = recv_data.split('\r\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line in ['#', '*', '@']:
                result['responses'].append(line)
            elif ',' in line:
                try:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        voltage = float(parts[0])
                        current = float(parts[1])
                        result['data_points'].append({
                            'voltage': voltage,
                            'current': current
                        })
                except:
                    pass
    
    # 统计数据
    if result['data_points']:
        currents = [p['current'] for p in result['data_points']]
        voltages = [p['voltage'] for p in result['data_points']]
        
        result['statistics'] = {
            'total_points': len(result['data_points']),
            'voltage_min': min(voltages),
            'voltage_max': max(voltages),
            'current_min': min(currents),
            'current_max': max(currents),
            'current_mean': sum(currents) / len(currents),
            'sampling_rate': f"≈ {len(result['data_points']) / 5.0:.1f} Hz" if len(result['data_points']) > 0 else "N/A"
        }
    
    return result


def save_analysis_report(analysis_result, output_file):
    """
    保存分析报告
    
    Args:
        analysis_result: 分析结果字典
        output_file: 输出文件路径
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("DPV 协议分析报告\n")
        f.write("=" * 70 + "\n\n")
        
        # 命令信息
        f.write("【发送命令】\n")
        f.write(f"命令: {analysis_result['command']}\n\n")
        
        # 参数信息
        if analysis_result['parameters']:
            f.write("【参数列表】\n")
            param_names = [
                '起始电位 (V)', '结束电位 (V)', '扫描方向', '脉冲幅度 (V)',
                '第二扫描起始点', '循环次数', '顶点电位', '保留参数8',
                '保留参数9', '保留参数10', '保留参数11', '脉冲宽度 (ms)',
                '脉冲周期 (ms)', '采样窗口 (ms)', '电流量程 (μA)', '控制参数16',
                '控制参数17', '控制参数18', '结束标记'
            ]
            
            for i, param in enumerate(analysis_result['parameters']):
                if i < len(param_names):
                    f.write(f"  位置 {i:2d}: {param_names[i]:20s} = {param}\n")
            f.write("\n")
        
        # 响应信息
        if analysis_result['responses']:
            f.write("【设备响应】\n")
            for i, resp in enumerate(analysis_result['responses']):
                if resp == '#':
                    f.write(f"  {i+1}. # - 参数确认\n")
                elif resp == '*':
                    f.write(f"  {i+1}. * - 开始扫描\n")
                elif resp == '@':
                    f.write(f"  {i+1}. @ - 扫描完成\n")
            f.write("\n")
        
        # 数据统计
        if analysis_result['statistics']:
            f.write("【数据统计】\n")
            stats = analysis_result['statistics']
            f.write(f"  总数据点数: {stats.get('total_points', 0)}\n")
            f.write(f"  电位范围: {stats.get('voltage_min', 'N/A')} ~ {stats.get('voltage_max', 'N/A')} V\n")
            f.write(f"  电流范围: {stats.get('current_min', 'N/A')} ~ {stats.get('current_max', 'N/A')} μA\n")
            f.write(f"  平均电流: {stats.get('current_mean', 'N/A'):.4f} μA\n")
            f.write(f"  采样频率: {stats.get('sampling_rate', 'N/A')}\n")
            f.write("\n")
        
        # 数据样本
        if analysis_result['data_points']:
            f.write("【数据样本】(前 10 条)\n")
            f.write("  电位 (V)    |  电流 (μA)\n")
            f.write("  " + "-" * 25 + "\n")
            
            for i, point in enumerate(analysis_result['data_points'][:10]):
                f.write(f"  {point['voltage']:8.4f}   |  {point['current']:8.2f}\n")
            
            if len(analysis_result['data_points']) > 10:
                f.write(f"  ... (共 {len(analysis_result['data_points'])} 条数据)\n")


def save_data_to_csv(analysis_result, output_file):
    """
    将数据保存为 CSV 文件
    
    Args:
        analysis_result: 分析结果字典
        output_file: 输出文件路径
    """
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['电位(V)', '电流(μA)'])
        
        for point in analysis_result['data_points']:
            writer.writerow([point['voltage'], point['current']])


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python analyze_serial_log.py <hex_log_file> [output_dir]")
        print("\n示例:")
        print("  python analyze_serial_log.py serial_log.hex")
        print("  python analyze_serial_log.py serial_log.hex ./analysis")
        sys.exit(1)
    
    log_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    
    if not os.path.exists(log_file):
        print(f"错误: 文件不存在 - {log_file}")
        sys.exit(1)
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📖 正在分析日志文件: {log_file}")
    
    # 解析日志
    send_data, recv_data = parse_hex_log(log_file)
    print(f"   发送数据长度: {len(send_data)} 字节")
    print(f"   接收数据长度: {len(recv_data)} 字节")
    
    # 分析协议
    print("\n📊 分析 DPV 协议...")
    analysis = analyze_dpv_protocol(send_data, recv_data)
    
    # 保存报告
    report_file = os.path.join(output_dir, "analysis_report.txt")
    save_analysis_report(analysis, report_file)
    print(f"   ✓ 报告已保存: {report_file}")
    
    # 保存数据
    if analysis['data_points']:
        csv_file = os.path.join(output_dir, "dpv_data.csv")
        save_data_to_csv(analysis, csv_file)
        print(f"   ✓ 数据已保存: {csv_file}")
    
    # 显示摘要
    print("\n" + "=" * 70)
    print("分析摘要")
    print("=" * 70)
    print(f"命令: {analysis['command']}")
    print(f"参数数量: {len(analysis['parameters'])}")
    print(f"设备响应: {', '.join(analysis['responses'])}")
    print(f"数据点数: {analysis['statistics'].get('total_points', 0)}")
    
    if analysis['statistics'].get('total_points', 0) > 0:
        stats = analysis['statistics']
        print(f"\n电位范围: {stats['voltage_min']:.4f} ~ {stats['voltage_max']:.4f} V")
        print(f"电流范围: {stats['current_min']:.2f} ~ {stats['current_max']:.2f} μA")
        print(f"平均电流: {stats['current_mean']:.4f} μA")
        print(f"采样频率: {stats['sampling_rate']}")


if __name__ == "__main__":
    main()
