#!/usr/bin/env python3
"""
电化学检测 GUI 应用程序
支持循环伏安法 (CV) 和差分脉冲伏安法 (DPV) 检测
使用 PySide6 框架
"""

import sys
import os
import queue
import time
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QGroupBox, QFormLayout,
    QDoubleSpinBox, QSpinBox, QProgressBar, QTextEdit, QSplitter,
    QTabWidget, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 导入协议实现
from utils.electrochemical_protocol import ElectrochemicalProtocol, ProtocolState
from utils.dpv_protocol import DPVProtocol


# 配置中文字体
def setup_chinese_font():

    chinese_fonts = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi', 'FangSong', 
                     'STSong', 'STKaiti', 'STFangsong', 'STXihei']
    
    for font in chinese_fonts:
        try:
            plt.rcParams['font.sans-serif'] = [font]
            plt.rcParams['axes.unicode_minus'] = False
            return font
        except:
            continue
    
    print("警告: 未找到合适的中文字体，中文可能无法正常显示")
    return None


class DetectionWorker(QThread):
    """检测工作线程"""
    progress_update = Signal(int, str)  # 进度值, 消息
    data_update = Signal(list)  # 数据更新
    finished = Signal(bool, str)  # 是否成功, 消息
    
    def __init__(self, method, params):
        super().__init__()
        self.method = method  # 'CV' or 'DPV'
        self.params = params
        self.protocol = None
        
    def run(self):
        """执行检测"""
        try:
            # 创建协议实例
            if self.method == 'CV':
                self.protocol = ElectrochemicalProtocol(
                    port=self.params.get('port'),
                    baudrate=self.params.get('baudrate', 115200),
                    simulate=self.params.get('simulate', True)
                )
            else:  # DPV
                self.protocol = DPVProtocol(
                    port=self.params.get('port'),
                    baudrate=self.params.get('baudrate', 115200),
                    simulate=self.params.get('simulate', True)
                )
            
            # 连接设备
            self.progress_update.emit(10, "正在连接设备...")
            if not self.protocol.connect():
                self.finished.emit(False, "设备连接失败")
                return
            
            # 发送参数
            self.progress_update.emit(20, "正在设置参数...")
            if self.method == 'CV':
                success = self.protocol.send_parameter_command(
                    start_v=self.params['start_v'],
                    end_v=self.params['end_v'],
                    scan_dir=self.params['scan_dir'],
                    scan_rate=self.params['scan_rate'],
                    cycles=self.params['cycles'],
                    current_range=self.params['current_range']
                )
            else:  # DPV
                success = self.protocol.send_dpv_command(
                    start_v=self.params['start_v'],
                    end_v=self.params['end_v'],
                    scan_dir=self.params['scan_dir'],
                    pulse_height=self.params['pulse_height'],
                    start_v2=self.params.get('start_v2', self.params['start_v']),
                    cycles=self.params['cycles'],
                    vertex_v=self.params.get('vertex_v', -1),
                    pulse_width=self.params['pulse_width'],
                    pulse_period=self.params['pulse_period'],
                    sample_width=self.params['sample_width'],
                    current_range=self.params['current_range']
                )
            
            if not success:
                self.finished.emit(False, "参数设置失败")
                return
            
            self.progress_update.emit(30, "等待设备确认...")
            
            # 等待确认响应 (#)
            start_time = time.time()
            while self.protocol.state != ProtocolState.PARAMETER_SET and time.time() - start_time < 5:
                try:
                    response = self.protocol.response_queue.get(timeout=0.1)
                    self.protocol._handle_response(response)
                except queue.Empty:
                    continue
            
            if self.protocol.state != ProtocolState.PARAMETER_SET:
                self.finished.emit(False, "参数确认超时")
                return
            
            # 发送开始命令
            self.progress_update.emit(40, "开始检测...")
            if not self.protocol.send_start_command():
                self.finished.emit(False, "启动检测失败")
                return
            
            # 等待开始确认响应 (*)
            start_time = time.time()
            while self.protocol.state != ProtocolState.RECEIVING_DATA and time.time() - start_time < 5:
                try:
                    response = self.protocol.response_queue.get(timeout=0.1)
                    self.protocol._handle_response(response)
                except queue.Empty:
                    continue
            
            if self.protocol.state != ProtocolState.RECEIVING_DATA:
                self.finished.emit(False, "开始命令确认超时")
                return
            
            # 处理响应并更新数据
            self.progress_update.emit(50, "正在采集数据...")
            
            # 启动数据监控
            self._monitor_data()
            
        except Exception as e:
            self.finished.emit(False, f"检测过程出错: {str(e)}")
        finally:
            if self.protocol:
                self.protocol.disconnect()
    
    def _monitor_data(self):
        """监控数据采集"""
        start_time = time.time()
        # 增加超时时间:DPV 120秒, CV 90秒,避免长时间扫描时超时断连
        timeout = 120 if self.method == 'DPV' else 90
        last_update_time = start_time
        data_update_interval = 0.5  # 每0.5秒更新一次UI
        
        while time.time() - start_time < timeout:
            try:
                # 非阻塞式检查队列
                response = self.protocol.response_queue.get(timeout=0.1)
                self.protocol._handle_response(response)
                
                # 定期更新数据显示,避免频繁刷新UI
                current_time = time.time()
                if current_time - last_update_time >= data_update_interval:
                    if len(self.protocol.data_buffer) > 0:
                        self.data_update.emit(self.protocol.data_buffer.copy())
                        # 更新进度
                        elapsed = current_time - start_time
                        progress = min(50 + int((elapsed / timeout) * 45), 95)
                        self.progress_update.emit(progress, f"已采集 {len(self.protocol.data_buffer)} 个数据点...")
                        last_update_time = current_time
                
                # 检查串口连接状态(仅非模拟模式)
                if not self.protocol.simulate and self.protocol.serial_conn:
                    if not self.protocol.serial_conn.is_open:
                        self.finished.emit(False, "串口连接已断开,请检查设备连接")
                        return
                
                # 检查是否完成
                if self.protocol.state == ProtocolState.TEST_COMPLETE:
                    # 最后一次数据更新
                    if len(self.protocol.data_buffer) > 0:
                        self.data_update.emit(self.protocol.data_buffer.copy())
                    self.progress_update.emit(100, "检测完成!")
                    self.finished.emit(True, f"成功采集 {len(self.protocol.data_buffer)} 个数据点")
                    return
                    
            except queue.Empty:
                # 队列为空时也要让出CPU时间
                time.sleep(0.01)
                continue
            except Exception as e:
                self.finished.emit(False, f"数据采集错误: {str(e)}")
                return
        
        self.finished.emit(False, "检测超时")


class PlotCanvas(FigureCanvas):
    """matplotlib 绘图画布"""
    
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 获取中文字体
        self.font_prop = self._get_chinese_font()
        
        # 初始化图表
        self.axes.set_xlabel('电位 (V)', fontsize=12, fontproperties=self.font_prop)
        self.axes.set_ylabel('电流 (μA)', fontsize=12, fontproperties=self.font_prop)
        self.axes.set_title('电化学检测数据', fontsize=14, fontweight='bold', fontproperties=self.font_prop)
        self.axes.grid(True, alpha=0.3)
    
    def _get_chinese_font(self):
        """获取中文字体属性"""
        # 尝试使用项目文件夹中的字体
        font_path = os.path.join(os.path.dirname(__file__), 'fusion-pixel-12px-monospaced-zh_hans.ttf')
        if os.path.exists(font_path):
            try:
                return font_manager.FontProperties(fname=font_path)
            except Exception as e:
                print(f"加载自定义字体失败: {e}")
        
        # 备用方案：使用系统中文字体
        chinese_fonts = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi', 'FangSong']
        for font in chinese_fonts:
            try:
                return font_manager.FontProperties(family=font)
            except:
                continue
        
        # 默认字体
        return font_manager.FontProperties()
        
    def plot_data(self, data, method='CV'):
        """绘制数据"""
        self.axes.clear()
        
        if not data or len(data) == 0:
            self.axes.text(0.5, 0.5, '暂无数据', 
                          ha='center', va='center', 
                          transform=self.axes.transAxes,
                          fontsize=16, color='gray',
                          fontproperties=self.font_prop)
            self.draw()
            return
        
        # 提取电位和电流
        voltages = [point[0] for point in data]
        currents = [point[1] for point in data]
        
        # 绘制
        if method == 'CV':
            self.axes.plot(voltages, currents, 'b-', linewidth=1.5, label='CV 曲线')
            self.axes.set_title('循环伏安法 (CV) 检测结果', fontsize=14, fontweight='bold', fontproperties=self.font_prop)
        else:
            self.axes.plot(voltages, currents, 'r-', linewidth=1.5, label='DPV 曲线')
            self.axes.set_title('差分脉冲伏安法 (DPV) 检测结果', fontsize=14, fontweight='bold', fontproperties=self.font_prop)
        
        self.axes.set_xlabel('电位 (V)', fontsize=12, fontproperties=self.font_prop)
        self.axes.set_ylabel('电流 (μA)', fontsize=12, fontproperties=self.font_prop)
        self.axes.grid(True, alpha=0.3)
        
        # 设置图例字体
        legend = self.axes.legend(prop=self.font_prop)
        
        self.fig.tight_layout()
        self.draw()


class ElectrochemicalGUI(QMainWindow):
    """电化学检测主界面"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("电化学检测系统")
        self.setGeometry(100, 100, 1400, 800)
        
        # 数据存储
        self.current_data = []
        self.detection_worker = None
        
        # 初始化界面
        self.init_ui()
        
        # 初始化完成后刷新串口列表
        QTimer.singleShot(100, self.initial_refresh_ports)
        
    def init_ui(self):
        """初始化用户界面"""
        # 主容器
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧控制面板
        left_panel = self.create_control_panel()
        splitter.addWidget(left_panel)
        
        # 右侧显示面板
        right_panel = self.create_display_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割比例
        splitter.setSizes([400, 1000])
        
        main_layout.addWidget(splitter)
        
    def create_control_panel(self):
        """创建左侧控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 标题
        title = QLabel("检测参数设置")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 检测方法选择
        method_group = QGroupBox("检测方法")
        method_layout = QVBoxLayout()
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(['循环伏安法 (CV)', '差分脉冲伏安法 (DPV)'])
        self.method_combo.currentIndexChanged.connect(self.on_method_changed)
        method_layout.addWidget(self.method_combo)
        
        method_group.setLayout(method_layout)
        layout.addWidget(method_group)
        
        # 参数设置 (使用标签页)
        self.param_tabs = QTabWidget()
        
        # CV 参数
        self.cv_params_widget = self.create_cv_params()
        self.param_tabs.addTab(self.cv_params_widget, "CV 参数")
        
        # DPV 参数
        self.dpv_params_widget = self.create_dpv_params()
        self.param_tabs.addTab(self.dpv_params_widget, "DPV 参数")
        
        layout.addWidget(self.param_tabs)
        
        # 连接设置
        conn_group = QGroupBox("连接设置")
        conn_layout = QFormLayout()
        
        self.simulate_combo = QComboBox()
        self.simulate_combo.addItems(['模拟模式', '真实设备'])
        self.simulate_combo.currentIndexChanged.connect(self.on_mode_changed)
        conn_layout.addRow("运行模式:", self.simulate_combo)
        
        # 串口选择
        port_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        port_layout.addWidget(self.port_combo)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.setMaximumWidth(60)
        refresh_btn.clicked.connect(self.refresh_ports)
        port_layout.addWidget(refresh_btn)
        
        conn_layout.addRow("串口:", port_layout)
        
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # 不在这里调用 refresh_ports,等待界面完全初始化后再调用
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始检测")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px; padding: 10px;")
        self.start_btn.clicked.connect(self.start_detection)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-size: 14px; padding: 10px;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_detection)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        
        # 保存按钮
        self.save_btn = QPushButton("保存数据")
        self.save_btn.setStyleSheet("background-color: #2196F3; color: white; font-size: 14px; padding: 10px;")
        self.save_btn.clicked.connect(self.save_data)
        self.save_btn.setEnabled(False)
        layout.addWidget(self.save_btn)
        
        # 添加弹性空间
        layout.addStretch()
        
        return panel
    
    def create_cv_params(self):
        """创建 CV 参数设置界面"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        self.cv_start_v = QDoubleSpinBox()
        self.cv_start_v.setRange(-10.0, 10.0)
        self.cv_start_v.setValue(-1.0)
        self.cv_start_v.setSingleStep(0.1)
        self.cv_start_v.setSuffix(" V")
        layout.addRow("起始电位:", self.cv_start_v)
        
        self.cv_end_v = QDoubleSpinBox()
        self.cv_end_v.setRange(-10.0, 10.0)
        self.cv_end_v.setValue(1.0)
        self.cv_end_v.setSingleStep(0.1)
        self.cv_end_v.setSuffix(" V")
        layout.addRow("结束电位:", self.cv_end_v)
        
        self.cv_scan_rate = QDoubleSpinBox()
        self.cv_scan_rate.setRange(0.01, 10.0)
        self.cv_scan_rate.setValue(0.2)
        self.cv_scan_rate.setSingleStep(0.05)
        self.cv_scan_rate.setSuffix(" V/s")
        layout.addRow("扫描速率:", self.cv_scan_rate)
        
        self.cv_cycles = QSpinBox()
        self.cv_cycles.setRange(1, 10)
        self.cv_cycles.setValue(2)
        layout.addRow("循环次数:", self.cv_cycles)
        
        self.cv_scan_dir = QComboBox()
        self.cv_scan_dir.addItems(['正向 (1)', '负向 (-1)'])
        layout.addRow("扫描方向:", self.cv_scan_dir)
        
        self.cv_current_range = QSpinBox()
        self.cv_current_range.setRange(1, 1000)
        self.cv_current_range.setValue(50)
        self.cv_current_range.setSuffix(" μA")
        layout.addRow("电流量程:", self.cv_current_range)
        
        return widget
    
    def create_dpv_params(self):
        """创建 DPV 参数设置界面"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        self.dpv_start_v = QDoubleSpinBox()
        self.dpv_start_v.setRange(-10.0, 10.0)
        self.dpv_start_v.setValue(-1.0)
        self.dpv_start_v.setSingleStep(0.1)
        self.dpv_start_v.setSuffix(" V")
        layout.addRow("起始电位:", self.dpv_start_v)
        
        self.dpv_end_v = QDoubleSpinBox()
        self.dpv_end_v.setRange(-10.0, 10.0)
        self.dpv_end_v.setValue(1.0)
        self.dpv_end_v.setSingleStep(0.1)
        self.dpv_end_v.setSuffix(" V")
        layout.addRow("结束电位:", self.dpv_end_v)
        
        self.dpv_pulse_height = QDoubleSpinBox()
        self.dpv_pulse_height.setRange(0.01, 1.0)
        self.dpv_pulse_height.setValue(0.1)
        self.dpv_pulse_height.setSingleStep(0.01)
        self.dpv_pulse_height.setSuffix(" V")
        layout.addRow("脉冲幅度:", self.dpv_pulse_height)
        
        self.dpv_pulse_width = QSpinBox()
        self.dpv_pulse_width.setRange(1, 100)
        self.dpv_pulse_width.setValue(10)
        self.dpv_pulse_width.setSuffix(" ms")
        layout.addRow("脉冲宽度:", self.dpv_pulse_width)
        
        self.dpv_pulse_period = QSpinBox()
        self.dpv_pulse_period.setRange(1, 200)
        self.dpv_pulse_period.setValue(10)
        self.dpv_pulse_period.setSuffix(" ms")
        layout.addRow("脉冲周期:", self.dpv_pulse_period)
        
        self.dpv_sample_width = QSpinBox()
        self.dpv_sample_width.setRange(1, 100)
        self.dpv_sample_width.setValue(20)
        self.dpv_sample_width.setSuffix(" ms")
        layout.addRow("采样窗口:", self.dpv_sample_width)
        
        self.dpv_cycles = QSpinBox()
        self.dpv_cycles.setRange(1, 10)
        self.dpv_cycles.setValue(2)
        layout.addRow("循环次数:", self.dpv_cycles)
        
        self.dpv_scan_dir = QComboBox()
        self.dpv_scan_dir.addItems(['正向 (1)', '负向 (-1)'])
        layout.addRow("扫描方向:", self.dpv_scan_dir)
        
        self.dpv_current_range = QSpinBox()
        self.dpv_current_range.setRange(1, 1000)
        self.dpv_current_range.setValue(50)
        self.dpv_current_range.setSuffix(" μA")
        layout.addRow("电流量程:", self.dpv_current_range)
        
        return widget
    
    def create_display_panel(self):
        """创建右侧显示面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 进度显示区
        progress_group = QGroupBox("检测进度")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12px; color: #666;")
        progress_layout.addWidget(self.status_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # 日志显示区
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("background-color: #f5f5f5; font-family: Consolas; color: black;")
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # 图表显示区
        chart_group = QGroupBox("数据可视化")
        chart_layout = QVBoxLayout()
        
        self.canvas = PlotCanvas(self, width=8, height=5, dpi=100)
        chart_layout.addWidget(self.canvas)
        
        chart_group.setLayout(chart_layout)
        layout.addWidget(chart_group)
        
        return panel
    
    def on_method_changed(self, index):
        """检测方法改变时切换参数标签页"""
        self.param_tabs.setCurrentIndex(index)
    
    def on_mode_changed(self, index):
        """运行模式改变时启用/禁用串口选择"""
        is_real_device = (index == 1)
        self.port_combo.setEnabled(is_real_device)
    
    def initial_refresh_ports(self):
        """初始化时刷新串口列表(不记录日志)"""
        self.port_combo.clear()
        
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            
            if ports:
                for port in ports:
                    display_text = f"{port.device} - {port.description}"
                    self.port_combo.addItem(display_text, port.device)
            else:
                self.port_combo.addItem("未找到串口", None)
        except ImportError:
            self.port_combo.addItem("需要安装 pyserial", None)
        except Exception as e:
            self.port_combo.addItem("获取串口失败", None)
        
        # 初始状态下禁用串口选择(模拟模式)
        self.port_combo.setEnabled(self.simulate_combo.currentIndex() == 1)
    
    def refresh_ports(self):
        """刷新可用串口列表"""
        self.port_combo.clear()
        
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            
            if ports:
                for port in ports:
                    # 显示端口号和描述
                    display_text = f"{port.device} - {port.description}"
                    self.port_combo.addItem(display_text, port.device)
                self.log_message(f"找到 {len(ports)} 个串口")
            else:
                self.port_combo.addItem("未找到串口", None)
                self.log_message("未找到可用串口")
        except ImportError:
            self.port_combo.addItem("需要安装 pyserial", None)
            self.log_message("错误: 未安装 pyserial 库")
        except Exception as e:
            self.port_combo.addItem("获取串口失败", None)
            self.log_message(f"获取串口列表失败: {str(e)}")
        
        # 更新串口选择状态
        self.port_combo.setEnabled(self.simulate_combo.currentIndex() == 1)
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def start_detection(self):
        """开始检测"""
        # 获取检测方法
        method = 'CV' if self.method_combo.currentIndex() == 0 else 'DPV'
        
        # 检查串口配置
        is_simulate = self.simulate_combo.currentIndex() == 0
        port = None
        
        if not is_simulate:
            # 真实设备模式,需要选择串口
            if self.port_combo.count() == 0 or self.port_combo.currentData() is None:
                QMessageBox.warning(self, "错误", "请先选择有效的串口!")
                return
            port = self.port_combo.currentData()
            self.log_message(f"使用串口: {port}")
        
        # 获取参数
        params = {
            'port': port,
            'simulate': is_simulate,
            'baudrate': 115200
        }
        
        if method == 'CV':
            params.update({
                'start_v': self.cv_start_v.value(),
                'end_v': self.cv_end_v.value(),
                'scan_rate': self.cv_scan_rate.value(),
                'cycles': self.cv_cycles.value(),
                'scan_dir': 1 if self.cv_scan_dir.currentIndex() == 0 else -1,
                'current_range': self.cv_current_range.value()
            })
        else:  # DPV
            params.update({
                'start_v': self.dpv_start_v.value(),
                'end_v': self.dpv_end_v.value(),
                'pulse_height': self.dpv_pulse_height.value(),
                'pulse_width': self.dpv_pulse_width.value(),
                'pulse_period': self.dpv_pulse_period.value(),
                'sample_width': self.dpv_sample_width.value(),
                'cycles': self.dpv_cycles.value(),
                'scan_dir': 1 if self.dpv_scan_dir.currentIndex() == 0 else -1,
                'current_range': self.dpv_current_range.value()
            })
        
        # 重置界面
        self.current_data = []
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self.canvas.plot_data([], method)
        
        # 禁用开始按钮
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        
        # 记录日志
        self.log_message(f"开始 {method} 检测")
        self.log_message(f"参数: {params}")
        
        # 创建并启动工作线程
        self.detection_worker = DetectionWorker(method, params)
        self.detection_worker.progress_update.connect(self.on_progress_update)
        self.detection_worker.data_update.connect(self.on_data_update)
        self.detection_worker.finished.connect(self.on_detection_finished)
        self.detection_worker.start()
    
    def stop_detection(self):
        """停止检测"""
        if self.detection_worker and self.detection_worker.isRunning():
            self.detection_worker.terminate()
            self.detection_worker.wait()
            self.log_message("检测已手动停止")
            self.on_detection_finished(False, "用户取消")
    
    def on_progress_update(self, value, message):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        self.log_message(message)
    
    def on_data_update(self, data):
        """更新数据显示"""
        self.current_data = data
        method = 'CV' if self.method_combo.currentIndex() == 0 else 'DPV'
        self.canvas.plot_data(data, method)
    
    def on_detection_finished(self, success, message):
        """检测完成"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            self.log_message(f"✓ {message}")
            self.save_btn.setEnabled(True)
            QMessageBox.information(self, "检测完成", message)
        else:
            self.log_message(f"✗ {message}")
            QMessageBox.warning(self, "检测失败", message)
    
    def save_data(self):
        """保存数据到文件"""
        if not self.current_data:
            QMessageBox.warning(self, "警告", "没有可保存的数据")
            return
        
        # 文件对话框
        method = 'cv' if self.method_combo.currentIndex() == 0 else 'dpv'
        default_filename = f"{method}_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存数据",
            default_filename,
            "CSV 文件 (*.csv);;所有文件 (*.*)"
        )
        
        if filename:
            try:
                import csv
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['电位 (V)', '电流 (μA)'])
                    for voltage, current in self.current_data:
                        writer.writerow([voltage, current])
                
                self.log_message(f"数据已保存到: {filename}")
                QMessageBox.information(self, "保存成功", f"数据已保存到:\n{filename}")
            except Exception as e:
                self.log_message(f"保存失败: {str(e)}")
                QMessageBox.critical(self, "保存失败", str(e))


def main():
    """主函数"""
    # 设置中文字体
    font_name = setup_chinese_font()
    if font_name:
        print(f"已加载中文字体: {font_name}")
    
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建主窗口
    window = ElectrochemicalGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
