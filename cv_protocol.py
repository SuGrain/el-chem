import serial
import time
import csv
import threading
import queue
import matplotlib.pyplot as plt
from datetime import datetime
from enum import Enum
import argparse
import sys

class ProtocolState(Enum):
    IDLE = 0
    PARAMETER_SET = 1
    WAITING_ACK = 2
    STARTING_TEST = 3
    RECEIVING_DATA = 4
    TEST_COMPLETE = 5
    ERROR = 6

class ElectrochemicalProtocol:
    """电化学设备通信协议实现"""
    
    def __init__(self, port=None, baudrate=115200, simulate=False):
        self.port = port
        self.baudrate = baudrate
        self.simulate = simulate
        self.serial_conn = None
        self.state = ProtocolState.IDLE
        self.data_buffer = []
        self.response_queue = queue.Queue()
        self.stop_flag = threading.Event()
        self.read_thread = None
        
        # 模拟参数
        self.sim_data_index = 0
        self.sim_start_time = None
        
    def connect(self):
        """连接串口设备或启动模拟模式"""
        if self.simulate:
            print("启动模拟模式...")
            self._start_simulation()
            return True
        
        if not self.port:
            print("错误: 未指定串口")
            return False
            
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )
            print(f"已连接到设备: {self.port} @ {self.baudrate}")
            
            # 启动读取线程
            self.read_thread = threading.Thread(target=self._read_serial_data)
            self.read_thread.daemon = True
            self.read_thread.start()
            
            return True
            
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.stop_flag.set()
        
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2)
            
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("设备连接已断开")
    
    def send_parameter_command(self, start_v=-1.0, end_v=1.0, scan_dir=1, 
                             scan_rate=0.2, cycles=2, current_range=50):
        """
        发送参数设置命令
        
        Args:
            start_v: 起始电位 (V)
            end_v: 结束电位 (V)
            scan_dir: 扫描方向 (1=正向, -1=负向)
            scan_rate: 扫描速率 (V/s)
            cycles: 循环次数
            current_range: 电流量程
        """
        # 构建参数命令
        params = [
            start_v,        # 起始电位
            end_v,          # 结束电位
            scan_dir,       # 扫描方向
            scan_rate,      # 扫描速率
            start_v,        # 第二扫描起始点
            cycles,         # 循环次数
            -1,             # 顶点电位
            0, 0, 10, 100,  # 其他参数
            scan_rate,      # 采样间隔
            20, current_range, current_range,  # 电流设置
            2, 0, 1         # 控制参数
        ]
        
        command = "P " + ",".join(map(str, params)) + ","
        
        if self.simulate:
            print(f"模拟发送参数命令: {command}")
            # 模拟响应
            self.response_queue.put("#\r\n")
            self.state = ProtocolState.WAITING_ACK
        elif self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write(command.encode())
            print(f"发送参数命令: {command}")
            self.state = ProtocolState.WAITING_ACK
        else:
            print("错误: 设备未连接")
            return False
            
        return True
    
    def send_start_command(self):
        """发送开始测试命令"""
        if self.simulate:
            print("模拟发送开始命令: S")
            # 模拟响应
            self.response_queue.put("*\r\n")
            self.state = ProtocolState.STARTING_TEST
            self.sim_start_time = time.time()
        elif self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write(b"S")
            print("发送开始命令: S")
            self.state = ProtocolState.STARTING_TEST
        else:
            print("错误: 设备未连接")
            return False
            
        return True
    
    def _read_serial_data(self):
        """串口数据读取线程"""
        while not self.stop_flag.is_set():
            try:
                if self.serial_conn and self.serial_conn.is_open:
                    line = self.serial_conn.readline()
                    if line:
                        response = line.decode().strip()
                        self.response_queue.put(response)
                time.sleep(0.001)  # 避免CPU占用过高
            except Exception as e:
                print(f"读取串口数据错误: {e}")
                break
    
    def _start_simulation(self):
        """启动模拟数据生成"""
        def simulate_data():
            while not self.stop_flag.is_set():
                if self.state == ProtocolState.RECEIVING_DATA and self.sim_start_time:
                    # 生成模拟CV数据
                    elapsed = time.time() - self.sim_start_time
                    
                    if elapsed < 20:  # 模拟20秒的测试
                        # 生成循环伏安数据
                        voltage = -1.0 + 2.0 * (elapsed / 10.0) % 2.0
                        if (elapsed / 10.0) % 2.0 > 1.0:
                            voltage = 1.0 - (voltage + 1.0)
                        
                        # 模拟电流响应 (简单的氧化还原峰)
                        current = 2.0 + 0.5 * (voltage ** 2) + 0.1 * abs(voltage - 0.2) * 10
                        current += (hash(str(elapsed)) % 100 - 50) / 1000.0  # 添加噪声
                        
                        data_line = f"{voltage:.4f},{current:.4f},\r\n"
                        self.response_queue.put(data_line)
                        time.sleep(0.062)  # 约16Hz
                    else:
                        # 结束数据传输
                        self.response_queue.put("@\r\n")
                        break
                else:
                    time.sleep(0.1)
        
        sim_thread = threading.Thread(target=simulate_data)
        sim_thread.daemon = True
        sim_thread.start()
    
    def process_responses(self, timeout=30):
        """处理设备响应"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.response_queue.get(timeout=0.1)
                self._handle_response(response)
                
                if self.state == ProtocolState.TEST_COMPLETE:
                    break
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"处理响应错误: {e}")
                self.state = ProtocolState.ERROR
                break
        
        if self.state != ProtocolState.TEST_COMPLETE:
            print("警告: 测试未正常完成")
    
    def _handle_response(self, response):
        """处理单个响应"""
        response = response.replace('\r\n', '').replace('\r', '').replace('\n', '')
        
        if response == "#":
            print("✓ 收到确认响应")
            if self.state == ProtocolState.WAITING_ACK:
                self.state = ProtocolState.PARAMETER_SET
                
        elif response == "*":
            print("✓ 开始接收数据")
            if self.state == ProtocolState.STARTING_TEST:
                self.state = ProtocolState.RECEIVING_DATA
                self.data_buffer = []
                
        elif response == "@":
            print("✓ 数据接收完成")
            if self.state == ProtocolState.RECEIVING_DATA:
                self.state = ProtocolState.TEST_COMPLETE
                
        elif "," in response:
            # 数据点: 电位,电流
            if self.state == ProtocolState.RECEIVING_DATA:
                try:
                    parts = response.split(",")
                    if len(parts) >= 2:
                        voltage = float(parts[0])
                        current = float(parts[1])
                        self.data_buffer.append((voltage, current))
                        
                        # 每10个点显示一次进度
                        if len(self.data_buffer) % 10 == 0:
                            print(f"📊 已接收 {len(self.data_buffer)} 个数据点 "
                                  f"(最新: V={voltage:.4f}V, I={current:.4f}μA)")
                            
                except ValueError as e:
                    print(f"无效数据格式: {response} - {e}")
        elif response:
            print(f"未知响应: {response}")
    
    def save_data(self, filename=None):
        """保存测试数据"""
        if not self.data_buffer:
            print("❌ 没有数据可保存")
            return None
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cv_data_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['电位(V)', '电流(μA)'])
                for voltage, current in self.data_buffer:
                    writer.writerow([voltage, current])
            
            print(f"✓ 数据已保存到: {filename}")
            print(f"✓ 共保存 {len(self.data_buffer)} 个数据点")
            return filename
            
        except Exception as e:
            print(f"❌ 保存数据失败: {e}")
            return None
    
    def plot_data(self, save_plot=True):
        """绘制CV曲线"""
        if not self.data_buffer:
            print("❌ 没有数据可绘制")
            return
        
        try:
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False
            
            voltages = [v for v, i in self.data_buffer]
            currents = [i for v, i in self.data_buffer]
            
            plt.figure(figsize=(10, 6))
            plt.plot(voltages, currents, 'b-', linewidth=1.5)
            plt.xlabel('Potential (V)')
            plt.ylabel('Current (μA)')
            plt.title('Cyclic Voltammetry Curve')
            plt.grid(True, alpha=0.3)
            
            # 添加数据点信息
            plt.text(0.02, 0.98, f'Data points: {len(self.data_buffer)}', 
                    transform=plt.gca().transAxes, 
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            if save_plot:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_filename = f"cv_curve_{timestamp}.png"
                plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
                print(f"✓ 图形已保存到: {plot_filename}")
            
            plt.show()
            
        except Exception as e:
            print(f"❌ 绘图失败: {e}")

def run_cv_test(port=None, simulate=False, start_v=-1.0, end_v=1.0, 
                scan_rate=0.2, cycles=2, current_range=50):
    """运行完整的CV测试"""
    
    print("🔬 电化学设备通信协议测试")
    print("=" * 50)
    
    # 创建协议实例
    protocol = ElectrochemicalProtocol(port=port, simulate=simulate)
    
    try:
        # 1. 连接设备
        print("\n📡 步骤1: 连接设备...")
        if not protocol.connect():
            return False
        
        # 2. 发送参数设置
        print(f"\n⚙️ 步骤2: 设置测试参数...")
        print(f"   起始电位: {start_v}V")
        print(f"   结束电位: {end_v}V")
        print(f"   扫描速率: {scan_rate}V/s")
        print(f"   循环次数: {cycles}")
        print(f"   电流量程: {current_range}μA")
        
        if not protocol.send_parameter_command(start_v, end_v, 1, scan_rate, cycles, current_range):
            return False
        
        # 3. 等待参数确认
        print("\n⏳ 步骤3: 等待参数确认...")
        start_time = time.time()
        while protocol.state != ProtocolState.PARAMETER_SET and time.time() - start_time < 5:
            try:
                response = protocol.response_queue.get(timeout=0.1)
                protocol._handle_response(response)
            except queue.Empty:
                continue
        
        if protocol.state != ProtocolState.PARAMETER_SET:
            print("❌ 参数设置失败")
            return False
        
        # 4. 发送开始命令
        print("\n🚀 步骤4: 开始测试...")
        if not protocol.send_start_command():
            return False
        
        # 5. 处理测试数据
        print("\n📊 步骤5: 接收测试数据...")
        protocol.process_responses(timeout=60)
        
        if protocol.state != ProtocolState.TEST_COMPLETE:
            print("❌ 测试未正常完成")
            return False
        
        # 6. 保存和显示结果
        print(f"\n💾 步骤6: 保存结果...")
        filename = protocol.save_data()
        
        if filename:
            print(f"\n📈 步骤7: 绘制曲线...")
            protocol.plot_data()
        
        print("\n✅ 测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        return False
        
    finally:
        protocol.disconnect()

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
        current_range=args.current_range
    )
    
    if not success:
        print("❌ 测试失败")
        sys.exit(1)

if __name__ == "__main__":
    main()