# GPU モニタリングツール

ラマがロードされたままの状態を確認・管理するためのツールセットです。

## 📁 ファイル一覧

### 1. `nvidia-smi-viewer.bat`
- **用途**: GPU状態の基本確認
- **機能**: 
  - GPU情報表示
  - メモリ使用量確認
  - 実行中プロセス表示

### 2. `gpu_monitor.py`
- **用途**: リアルタイムGPU監視
- **機能**:
  - 5秒間隔での自動更新
  - メモリ使用率のビジュアル表示
  - プロセス監視

### 3. `gpu-clear-memory.bat`
- **用途**: GPUメモリの強制クリア
- **機能**:
  - Pythonプロセスの強制終了
  - GPU使用プロセスの終了
  - メモリ解放

### 4. `docker_tools.py` (更新)
- **用途**: Dockerコンテナ + GPU監視ツール
- **新機能**:
  - `nvidia_smi_status()`: GPU状態取得
  - `nvidia_smi_memory_usage()`: メモリ使用量詳細
  - `nvidia_smi_processes()`: プロセス一覧
  - `nvidia_smi_kill_process()`: プロセス終了
  - `nvidia_smi_clear_memory()`: メモリクリア

## 🚀 使用方法

### 基本確認
```bash
# GPU状態を確認
nvidia-smi-viewer.bat

# リアルタイム監視
python gpu_monitor.py

# メモリクリア
gpu-clear-memory.bat
```

### Pythonから使用
```python
from docker_tools import nvidia_smi_status, nvidia_smi_clear_memory

# GPU状態確認
status = nvidia_smi_status()
print(status)

# メモリクリア
result = nvidia_smi_clear_memory()
print(result)
```

## 🔧 トラブルシューティング

### 1. nvidia-smiが見つからない
- NVIDIAドライバーがインストールされているか確認
- パスが通っているか確認

### 2. GPUメモリが解放されない
- `gpu-clear-memory.bat`を管理者権限で実行
- 手動でプロセスを確認して終了

### 3. リアルタイム監視が重い
- `gpu_monitor.py`の更新間隔を調整（`time.sleep(5)`を変更）

## 📊 出力例

### nvidia-smi-viewer.bat
```
========================================
NVIDIA-SMI Status Viewer
========================================

========================================
GPU Status
========================================
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.98                 Driver Version: 535.98                    |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA GeForce RTX 4090  On   | 00000000:01:00.0  On |                  N/A |
|  0%   45C    P8    25W /  450W|    0MiB /  24576MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

### gpu_monitor.py
```
================================================================================
🖥️  GPU Status Monitor - 2025-01-19T13:00:00
================================================================================

🎮 GPU 0: NVIDIA GeForce RTX 4090
   💾 Memory: 0MB / 24576MB (0.0%)
   ⚡ Utilization: 0%
   🌡️  Temperature: 45°C
   📊 [░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 0.0%
```

## ⚠️ 注意事項

1. **管理者権限**: 一部の機能は管理者権限が必要です
2. **プロセス終了**: メモリクリア機能は実行中のプロセスを強制終了します
3. **データ損失**: 作業中のデータがある場合は事前に保存してください

## 🔄 更新履歴

- 2025-01-19: 初回作成
  - 基本監視ツール追加
  - リアルタイム監視機能追加
  - メモリクリア機能追加
  - Dockerツール統合 