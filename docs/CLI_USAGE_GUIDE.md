# CLI 工具使用说明

## DPV 协议测试工具 (dpv_protocol_cli.py)

### 基本用法

```bash
python dpv_protocol_cli.py [选项]
```

### 可用选项

#### 连接选项

- `-p, --port PORT` - 指定串口号 (如: COM3, /dev/ttyUSB0)
- `-b, --baudrate RATE` - 波特率 (默认: 115200)
- `-s, --simulate` - 使用模拟模式（无需真实设备）

#### DPV 参数选项

- `--start-v V` - 起始电位 (V) (默认: -1.0)
- `--end-v V` - 结束电位 (V) (默认: 1.0)
- `--pulse-height V` - 脉冲幅度 (V) (默认: 0.1)
- `--pulse-width MS` - 脉冲宽度 (ms) (默认: 10)
- `--pulse-period MS` - 脉冲周期 (ms) (默认: 10)
- `--sample-width MS` - 采样窗口宽度 (ms) (默认: 20)
- `--cycles N` - 循环次数 (默认: 2)
- `--current-range μA` - 电流量程 (μA) (默认: 50)

#### 保存选项

- `--save-data` - 保存数据到 CSV 文件 (默认: 是)
- `--no-save` - 不保存数据
- `--save-plot` - 保存图形到文件 (默认: 是)
- `--no-plot` - 不保存图形

### 使用示例

#### 示例 1: 模拟模式（默认参数）

```bash
python dpv_protocol_cli.py -s
```

输出：保存 CSV 和 PNG 文件

#### 示例 2: 模拟模式（不保存文件）

```bash
python dpv_protocol_cli.py -s --no-save --no-plot
```

输出：仅显示测试过程，不保存任何文件

#### 示例 3: 真实设备（自定义参数）

```bash
python dpv_protocol_cli.py -p COM9 --pulse-height 0.1 --cycles 1
```

输出：保存 CSV 和 PNG 文件

#### 示例 4: 真实设备（仅保存数据，不绘图）

```bash
python dpv_protocol_cli.py -p COM3 --save-data --no-plot
```

输出：仅保存 CSV 文件，不生成图形

#### 示例 5: 真实设备（仅绘图，不保存数据）

```bash
python dpv_protocol_cli.py -p COM3 --no-save --save-plot
```

输出：显示图形但不保存任何数据

#### 示例 6: 自定义所有参数

```bash
python dpv_protocol_cli.py -p COM9 \
  --start-v -0.5 \
  --end-v 0.5 \
  --pulse-height 0.05 \
  --pulse-width 5 \
  --pulse-period 20 \
  --cycles 1 \
  --current-range 100 \
  --save-data \
  --save-plot
```

---

## CV 协议测试工具 (cv_protocol_cli.py)

### 基本用法

```bash
python cv_protocol_cli.py [选项]
```

### 可用选项

#### 连接选项

- `-p, --port PORT` - 指定串口号 (如: COM3, /dev/ttyUSB0)
- `-b, --baudrate RATE` - 波特率 (默认: 115200)
- `-s, --simulate` - 使用模拟模式

#### CV 参数选项

- `--start-v V` - 起始电位 (V) (默认: -1.0)
- `--end-v V` - 结束电位 (V) (默认: 1.0)
- `--scan-rate V/s` - 扫描速率 (V/s) (默认: 0.2)
- `--cycles N` - 循环次数 (默认: 1)
- `--current-range μA` - 电流量程 (μA) (默认: 100)

#### 保存选项

- `--save-data` - 保存数据到 CSV 文件 (默认: 是)
- `--no-save` - 不保存数据
- `--save-plot` - 保存图形到文件 (默认: 是)
- `--no-plot` - 不保存图形

### 使用示例

#### 示例 1: 模拟模式

```bash
python cv_protocol_cli.py -s
```

#### 示例 2: 模拟模式（不保存）

```bash
python cv_protocol_cli.py -s --no-save
```

#### 示例 3: 真实设备

```bash
python cv_protocol_cli.py -p COM3 --scan-rate 0.1 --cycles 2
```

#### 示例 4: 仅测试不保存

```bash
python cv_protocol_cli.py -p COM3 --no-save --no-plot
```

---

## 日志分析工具 (analyze_serial_log.py)

### 基本用法

```bash
python analyze_serial_log.py <hex_log_file> [output_dir]
```

### 使用示例

#### 示例 1: 分析日志（输出到当前目录）

```bash
python analyze_serial_log.py serial_log.hex
```

输出文件：
- `analysis_report.txt` - 详细分析报告
- `dpv_data.csv` - 提取的数据

#### 示例 2: 分析日志（输出到指定目录）

```bash
python analyze_serial_log.py serial_log.hex ./results
```

输出文件：
- `./results/analysis_report.txt`
- `./results/dpv_data.csv`

---

## 生成的文件说明

### CSV 数据文件

文件名格式：`dpv_data_YYYYMMDD_HHMMSS.csv` 或 `cv_data_YYYYMMDD_HHMMSS.csv`

内容示例：
```csv
电位(V),电流(μA)
-1.0055,0.24
-0.9958,0.08
-0.9861,0.16
```

### PNG 图形文件

文件名格式：`dpv_curve_YYYYMMDD_HHMMSS.png` 或 `cv_curve_YYYYMMDD_HHMMSS.png`

包含：
- 电位 vs 电流曲线图
- 数据点统计信息
- 高分辨率输出 (300 DPI)

### 分析报告文件

文件名：`analysis_report.txt`

包含：
- 发送命令详情
- 参数列表
- 设备响应
- 数据统计信息
- 数据样本

---

## 常见场景

### 场景 1: 快速测试（只看数据不保存）

```bash
python dpv_protocol_cli.py -s --no-save
```

### 场景 2: 数据收集（保存数据用于后处理）

```bash
python dpv_protocol_cli.py -p COM3 --no-plot --save-data
```

### 场景 3: 可视化验证（查看图形不需要数据文件）

```bash
python dpv_protocol_cli.py -p COM3 --no-save --save-plot
```

### 场景 4: 完整记录（保存所有输出）

```bash
python dpv_protocol_cli.py -p COM3 --save-data --save-plot
```

### 场景 5: 分析旧日志

```bash
python analyze_serial_log.py old_test_log.hex ./analysis
```

---

## 文件保存规则

| 条件 | 数据文件 | 图形文件 |
|------|--------|--------|
| `--save-data` | ✓ | - |
| `--save-plot` | - | ✓ |
| `--save-data --save-plot` | ✓ | ✓ |
| `--no-save --no-plot` | ✗ | ✗ |
| `--no-save --save-plot` | ✗ | ✓ |
| `--save-data --no-plot` | ✓ | ✗ |

---

**最后更新：** 2025年10月17日
