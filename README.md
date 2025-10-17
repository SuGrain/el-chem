# el-chem - 电化学检测软件

一个功能完善的电化学检测应用程序，支持循环伏安法 (CV) 和差分脉冲伏安法 (DPV) 电化学检测方法。

## 项目简介

el-chem 是一个基于 Python 开发的电化学检测软件，提供图形用户界面（GUI）和命令行工具（CLI）两种使用方式。该软件通过串口与电化学设备通信，支持实时数据采集、可视化和分析。

### 主要特性

- ✅ **双检测方法支持**
  - 循环伏安法 (Cyclic Voltammetry, CV)
  - 差分脉冲伏安法 (Differential Pulse Voltammetry, DPV)

- ✅ **图形用户界面**
  - 基于 PySide6 开发的现代化界面
  - 实时数据可视化（matplotlib）
  - 参数配置和测试控制
  - 数据导出功能

- ✅ **命令行工具**
  - CV 协议测试工具
  - DPV 协议测试工具
  - 串口日志分析工具
  - 批处理和自动化支持

- ✅ **通信协议**
  - 完整的串口通信协议实现
  - 实时数据流传输
  - 状态机管理
  - 模拟模式（无需真实硬件）

- ✅ **中文界面**
  - 完整的中文用户界面
  - 中文文档支持

## 系统要求

- Python 3.8 或更高版本
- Windows / Linux / macOS
- 串口通信硬件（或使用模拟模式）

## 安装

### 1. 克隆项目

```bash
git clone https://github.com/SuGrain/el-chem.git
cd el-chem
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 依赖包说明

- **PySide6**: Qt 图形界面框架
- **matplotlib**: 数据可视化
- **pyserial**: 串口通信
- **numpy**: 数值计算

## 使用说明

### GUI 应用程序

#### Windows 系统

双击运行 `run_gui.bat` 或在命令行执行：

```bash
python electrochemical_gui.py
```

#### Linux/macOS 系统

```bash
python3 electrochemical_gui.py
```

#### GUI 功能说明

1. **连接设备**
   - 选择串口号
   - 选择波特率（默认 115200）
   - 点击"连接"按钮

2. **选择检测方法**
   - CV（循环伏安法）
   - DPV（差分脉冲伏安法）

3. **配置参数**
   - 起始电位、结束电位
   - 扫描速率
   - 循环次数
   - 电流量程
   - DPV 特有参数：脉冲幅度、脉冲宽度等

4. **开始检测**
   - 点击"开始检测"按钮
   - 实时查看数据和图形
   - 等待检测完成

5. **保存数据**
   - 导出 CSV 数据文件
   - 保存图形为图片

### CLI 命令行工具

#### CV 协议测试工具

```bash
python tools/cv_protocol_cli.py [选项]
```

**常用参数：**
- `-p, --port`: 串口号（如 COM3 或 /dev/ttyUSB0）
- `-b, --baudrate`: 波特率（默认 115200）
- `-s, --simulate`: 使用模拟模式
- `--start-v`: 起始电位（V）
- `--end-v`: 结束电位（V）
- `--scan-rate`: 扫描速率（V/s）
- `--cycles`: 循环次数
- `--current-range`: 电流量程（μA）

**示例：**

```bash
# 使用模拟模式运行 CV 测试
python tools/cv_protocol_cli.py -s

# 连接真实设备运行 CV 测试
python tools/cv_protocol_cli.py -p COM3 --start-v -1.0 --end-v 1.0 --scan-rate 0.1 --cycles 3
```

#### DPV 协议测试工具

```bash
python tools/dpv_protocol_cli.py [选项]
```

**常用参数：**
- `-p, --port`: 串口号
- `-s, --simulate`: 使用模拟模式
- `--start-v`: 起始电位（V）
- `--end-v`: 结束电位（V）
- `--pulse-height`: 脉冲幅度（V）
- `--pulse-width`: 脉冲宽度（ms）
- `--pulse-period`: 脉冲周期（ms）
- `--cycles`: 循环次数
- `--save-data`: 保存数据到 CSV
- `--save-plot`: 保存图形到文件

**示例：**

```bash
# 使用模拟模式运行 DPV 测试
python tools/dpv_protocol_cli.py -s

# 连接真实设备运行 DPV 测试（不保存文件）
python tools/dpv_protocol_cli.py -p COM3 --no-save --no-plot
```

#### 串口日志分析工具

```bash
python tools/analyze_serial_log.py <日志文件路径>
```

用于分析和调试串口通信日志。

## 项目结构

```
el-chem/
├── electrochemical_gui.py      # GUI 主程序
├── run_gui.bat                 # Windows 启动脚本
├── requirements.txt            # Python 依赖包列表
├── utils/                      # 核心功能模块
│   ├── electrochemical_protocol.py  # CV 协议实现
│   └── dpv_protocol.py         # DPV 协议实现
├── tools/                      # CLI 命令行工具
│   ├── cv_protocol_cli.py      # CV 命令行工具
│   ├── dpv_protocol_cli.py     # DPV 命令行工具
│   └── analyze_serial_log.py  # 日志分析工具
├── docs/                       # 文档目录
│   ├── PROTOCOL_DOCUMENTATION.md     # CV 协议文档
│   ├── DPV_PROTOCOL_DOCUMENTATION.md # DPV 协议文档
│   └── CLI_USAGE_GUIDE.md           # CLI 使用指南
└── logs/                       # 日志文件目录（运行时生成）
```

## 技术文档

详细的技术文档请参考 `docs/` 目录：

- **[CV 协议文档](docs/PROTOCOL_DOCUMENTATION.md)** - 循环伏安法通信协议详细说明
- **[DPV 协议文档](docs/DPV_PROTOCOL_DOCUMENTATION.md)** - 差分脉冲伏安法通信协议详细说明
- **[CLI 使用指南](docs/CLI_USAGE_GUIDE.md)** - 命令行工具详细使用说明

### 通信协议概述

#### 物理层参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 接口 | RS232/USB | 串口通信 |
| 波特率 | 115200 | 默认波特率 |
| 数据位 | 8 | 标准配置 |
| 校验位 | 无 | 无奇偶校验 |
| 停止位 | 1 | 1个停止位 |

#### 协议特性

- 实时数据流传输
- 基于状态机的通信管理
- 支持参数配置和测试控制
- 完整的错误处理机制
- 模拟模式支持（便于开发和测试）

## 开发指南

### 代码结构

- **electrochemical_gui.py**: 图形界面主程序，包含 Qt 界面实现和绘图功能
- **utils/electrochemical_protocol.py**: CV 协议核心实现，包含通信协议、状态管理
- **utils/dpv_protocol.py**: DPV 协议核心实现
- **tools/**: 命令行工具集合

### 扩展开发

如需添加新的电化学检测方法：

1. 在 `utils/` 目录创建新的协议实现类
2. 继承基础协议类并实现特定的命令格式
3. 在 GUI 中添加对应的选项卡和参数配置
4. 创建对应的 CLI 工具（可选）

## 常见问题

### 1. 串口连接失败

- 检查串口号是否正确
- 确认设备已正确连接
- 检查串口权限（Linux 系统）
- 尝试使用模拟模式测试软件功能

### 2. 中文字体显示问题

软件会自动寻找系统中可用的中文字体。如果中文显示异常，请确保系统已安装中文字体。

### 3. 导入模块错误

确保已正确安装所有依赖包：

```bash
pip install -r requirements.txt
```

### 4. Linux 系统串口权限

```bash
sudo usermod -a -G dialout $USER
# 注销后重新登录生效
```

## 模拟模式

软件提供模拟模式，无需真实硬件即可测试功能：

- 自动生成模拟数据
- 符合真实设备的数据格式
- 适用于软件开发和功能验证

在 GUI 中可通过"模拟模式"选项启用，CLI 中使用 `-s` 或 `--simulate` 参数。

## 数据格式

### CSV 数据文件格式

检测完成后可导出 CSV 格式的数据文件，包含以下列：

- **Voltage (V)**: 电位值
- **Current (μA)**: 电流值
- **Cycle**: 循环编号（如有多个循环）

### 图形文件

支持导出 PNG 格式的图形文件，包含完整的坐标轴标签和图例。

## 许可证

本项目遵循开源许可证。具体许可证信息请查看项目仓库。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进本项目。

## 联系方式

- GitHub: https://github.com/SuGrain/el-chem
- 项目 Issues: https://github.com/SuGrain/el-chem/issues

## 更新日志

查看项目的 [Releases](https://github.com/SuGrain/el-chem/releases) 页面获取版本更新信息。

---

**注意**: 使用本软件进行电化学实验时，请遵守相关安全规范，正确操作设备。
