"""差分脉冲伏安法 (DPV) 通信协议实现"""

import serial
import time
import csv
import threading
import queue
import matplotlib.pyplot as plt
from datetime import datetime

# 导入统一的协议状态枚举
from utils.electrochemical_protocol import ProtocolState


class DPVProtocol:
    """差分脉冲伏安法 (DPV) 协议实现"""
    
    def __init__(self, port=None, baudrate=115200, simulate=False):
        """
        初始化 DPV 协议实例
        
        Args:
            port: 串口号 (如: COM3 或 /dev/ttyUSB0)
            baudrate: 波特率 (默认: 115200)
            simulate: 是否使用模拟模式 (默认: False)
        """
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
        self.sim_start_time = None
        
    def connect(self):
        """连接串口设备或启动模拟模式"""
        if self.simulate:
            print("启动 DPV 模拟模式...")
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
                timeout=5,  # 增加读超时到5秒,避免长时间等待时断连
                write_timeout=2  # 添加写超时,防止写阻塞
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
    
    def send_dpv_command(self, start_v=-1.0, end_v=1.0, scan_dir=1,
                        pulse_height=0.1, start_v2=-1.0, cycles=2,
                        vertex_v=-1, pulse_width=10, pulse_period=10,
                        sample_width=20, current_range=50):
        """
        发送 DPV 参数设置命令
        
        Args:
            start_v: 起始电位 (V)
            end_v: 结束电位 (V)
            scan_dir: 扫描方向 (1=正向, -1=负向)
            pulse_height: 脉冲幅度 (V)
            start_v2: 第二扫描起始点 (V)
            cycles: 循环次数
            vertex_v: 顶点电位 (-1为自动)
            pulse_width: 脉冲宽度 (ms)
            pulse_period: 脉冲周期 (ms)
            sample_width: 采样窗口宽度 (ms)
            current_range: 电流量程 (μA)
        """
        # 构建 DPV 参数命令
        params = [
            start_v,        # 起始电位
            end_v,          # 结束电位
            scan_dir,       # 扫描方向
            pulse_height,   # 脉冲幅度
            start_v2,       # 第二扫描起始点
            cycles,         # 循环次数
            vertex_v,       # 顶点电位
            0, 0, 10, 100,  # 保留参数
            pulse_width,    # 脉冲宽度
            pulse_period,   # 脉冲周期
            sample_width,   # 采样窗口宽度
            current_range,  # 电流量程
            2, 1, 1         # 控制参数
        ]
        
        command = "P " + ",".join(map(str, params)) + ",D"
        
        if self.simulate:
            print(f"模拟发送 DPV 参数命令: {command}")
            self.response_queue.put("#\r\n")
            self.state = ProtocolState.WAITING_ACK
        elif self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write(command.encode())
            print(f"发送 DPV 参数命令: {command}")
            self.state = ProtocolState.WAITING_ACK
        else:
            print("错误: 设备未连接")
            return False
            
        return True
    
    def send_start_command(self):
        """发送开始测试命令"""
        if self.simulate:
            print("模拟发送开始命令: D")
            self.response_queue.put("*\r\n")
            self.state = ProtocolState.STARTING_TEST
            self.sim_start_time = time.time()
        elif self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write(b"D")
            print("发送开始命令: D")
            self.state = ProtocolState.STARTING_TEST
        else:
            print("错误: 设备未连接")
            return False
            
        return True
    
    def _read_serial_data(self):
        """串口数据读取线程"""
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while not self.stop_flag.is_set():
            try:
                if self.serial_conn and self.serial_conn.is_open:
                    line = self.serial_conn.readline()
                    if line:
                        response = line.decode().strip()
                        self.response_queue.put(response)
                        consecutive_errors = 0  # 成功读取后重置错误计数
                    # 即使没有数据也不算错误,可能只是设备暂时没发送
                else:
                    print("串口未打开或已断开")
                    break
                    
                time.sleep(0.001)  # 避免CPU占用过高
                
            except serial.SerialException as e:
                consecutive_errors += 1
                print(f"串口异常 ({consecutive_errors}/{max_consecutive_errors}): {e}")
                if consecutive_errors >= max_consecutive_errors:
                    print("连续串口错误过多,停止读取")
                    break
                time.sleep(0.5)  # 串口错误后等待一段时间
                
            except UnicodeDecodeError as e:
                # 解码错误不致命,跳过这条数据
                print(f"数据解码错误: {e}")
                consecutive_errors = 0
                
            except Exception as e:
                consecutive_errors += 1
                print(f"读取串口数据错误 ({consecutive_errors}/{max_consecutive_errors}): {e}")
                if consecutive_errors >= max_consecutive_errors:
                    print("连续错误过多,停止读取")
                    break
                time.sleep(0.5)
    
    def _start_simulation(self):
        """启动模拟数据生成"""
        def simulate_data():
            while not self.stop_flag.is_set():
                if self.state == ProtocolState.RECEIVING_DATA and self.sim_start_time:
                    elapsed = time.time() - self.sim_start_time
                    
                    # 生成约 5 秒的模拟 DPV 数据 (50 Hz)
                    if elapsed < 5.0:
                        # 线性扫描从 -1V 到 1V
                        voltage = -1.0 + 2.0 * (elapsed / 5.0)
                        
                        # 模拟差分脉冲响应 (高斯峰)
                        peak_center = 0.3  # 峰值中心电位
                        peak_width = 0.2
                        peak_height = 2.0
                        
                        current = peak_height * __import__('math').exp(
                            -((voltage - peak_center) ** 2) / (2 * peak_width ** 2)
                        )
                        # 添加噪声
                        current += (hash(str(elapsed)) % 100 - 50) / 1000.0
                        
                        data_line = f"{voltage:.4f},{current:.2f},\r\n"
                        self.response_queue.put(data_line)
                        time.sleep(0.02)  # 50 Hz
                    else:
                        self.response_queue.put("@\r\n")
                        break
                else:
                    time.sleep(0.1)
        
        sim_thread = threading.Thread(target=simulate_data)
        sim_thread.daemon = True
        sim_thread.start()
    
    def process_responses(self, timeout=60):
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
            print("✓ 收到参数确认响应")
            if self.state == ProtocolState.WAITING_ACK:
                self.state = ProtocolState.PARAMETER_SET
                
        elif response == "*":
            print("✓ DPV 扫描开始，开始接收数据")
            if self.state == ProtocolState.STARTING_TEST:
                self.state = ProtocolState.RECEIVING_DATA
                self.data_buffer = []
                
        elif response == "@":
            print("✓ DPV 扫描完成，数据接收结束")
            if self.state == ProtocolState.RECEIVING_DATA:
                self.state = ProtocolState.TEST_COMPLETE
                
        elif response == "$":
            print("✓ DPV 扫描完成信号")
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
                        
                        # 每 20 个点显示一次进度
                        if len(self.data_buffer) % 20 == 0:
                            print(f"📊 已接收 {len(self.data_buffer)} 个数据点 "
                                  f"(最新: V={voltage:.4f}V, I={current:.2f}μA)")
                            
                except ValueError as e:
                    print(f"无效数据格式: {response} - {e}")
        elif response:
            print(f"⚠️  未知响应: {response}")
    
    def save_data(self, filename=None):
        """
        保存测试数据到 CSV 文件
        
        Args:
            filename: 保存文件名 (默认: dpv_data_YYYYMMDD_HHMMSS.csv)
            
        Returns:
            保存的文件名或 None (如果失败)
        """
        if not self.data_buffer:
            print("❌ 没有数据可保存")
            return None
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dpv_data_{timestamp}.csv"
        
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
        """
        绘制 DPV 曲线
        
        Args:
            save_plot: 是否保存图形到文件 (默认: True)
        """
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
            plt.title('Differential Pulse Voltammetry (DPV) Curve')
            plt.grid(True, alpha=0.3)
            
            # 添加数据点信息
            plt.text(0.02, 0.98, f'Data points: {len(self.data_buffer)}', 
                    transform=plt.gca().transAxes, 
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            if save_plot:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_filename = f"dpv_curve_{timestamp}.png"
                plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
                print(f"✓ 图形已保存到: {plot_filename}")
            
            plt.show()
            
        except Exception as e:
            print(f"❌ 绘图失败: {e}")


def run_dpv_test(port=None, simulate=False, start_v=-1.0, end_v=1.0,
                pulse_height=0.1, cycles=2, pulse_width=10, pulse_period=10,
                sample_width=20, current_range=50, save_data=True, save_plot=True):
    """
    运行完整的 DPV 测试
    
    Args:
        port: 串口号
        simulate: 是否使用模拟模式
        start_v: 起始电位 (V)
        end_v: 结束电位 (V)
        pulse_height: 脉冲幅度 (V)
        cycles: 循环次数
        pulse_width: 脉冲宽度 (ms)
        pulse_period: 脉冲周期 (ms)
        sample_width: 采样窗口宽度 (ms)
        current_range: 电流量程 (μA)
        save_data: 是否保存数据到 CSV (默认: True)
        save_plot: 是否保存图形到文件 (默认: True)
        
    Returns:
        测试是否成功 (True/False)
    """
    
    print("🔬 差分脉冲伏安法 (DPV) 测试")
    print("=" * 50)
    
    # 创建协议实例
    protocol = DPVProtocol(port=port, simulate=simulate)
    
    try:
        # 1. 连接设备
        print("\n📡 步骤1: 连接设备...")
        if not protocol.connect():
            return False
        
        # 2. 发送参数设置
        print(f"\n⚙️ 步骤2: 设置 DPV 参数...")
        print(f"   起始电位: {start_v}V")
        print(f"   结束电位: {end_v}V")
        print(f"   脉冲幅度: {pulse_height}V")
        print(f"   脉冲宽度: {pulse_width}ms")
        print(f"   脉冲周期: {pulse_period}ms")
        print(f"   循环次数: {cycles}")
        print(f"   电流量程: {current_range}μA")
        
        if not protocol.send_dpv_command(start_v, end_v, 1, pulse_height,
                                        start_v, cycles, -1, pulse_width,
                                        pulse_period, sample_width, current_range):
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
        print("\n🚀 步骤4: 开始 DPV 扫描...")
        if not protocol.send_start_command():
            return False
        
        # 5. 处理测试数据
        print("\n📊 步骤5: 接收测试数据...")
        protocol.process_responses(timeout=60)
        
        if protocol.state != ProtocolState.TEST_COMPLETE:
            print("❌ DPV 测试未正常完成")
            return False
        
        # 6. 保存和显示结果
        if save_data:
            print(f"\n💾 步骤6: 保存结果...")
            filename = protocol.save_data()
            
            if filename and save_plot:
                print(f"\n📈 步骤7: 绘制曲线...")
                protocol.plot_data(save_plot=True)
        else:
            if save_plot:
                print(f"\n📈 步骤6: 绘制曲线...")
                protocol.plot_data(save_plot=False)
        
        print("\n✅ DPV 测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        return False
        
    finally:
        protocol.disconnect()
