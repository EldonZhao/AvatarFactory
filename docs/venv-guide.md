# Virtual Environment Setup Guide

## 🎯 Why Use Virtual Environment?

使用虚拟环境 (venv) 的好处：
- ✅ **隔离依赖** - 不污染系统 Python 环境
- ✅ **版本管理** - 每个项目独立的依赖版本
- ✅ **易于删除** - 直接删除 venv 目录即可
- ✅ **可重现** - 确保在不同机器上环境一致

---

## 🚀 Quick Start

### Windows 用户

#### 方法 1: PowerShell (推荐)

```powershell
# 运行自动化脚本
.\setup_venv.ps1
```

**注意**: 如果遇到 "无法运行脚本" 错误：
```powershell
# 允许运行脚本 (管理员权限)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 方法 2: CMD

```cmd
# 运行批处理脚本
setup_venv.bat
```

#### 方法 3: Git Bash

```bash
# 运行 shell 脚本
bash setup_venv.sh
```

---

### macOS / Linux 用户

```bash
# 给脚本添加执行权限
chmod +x setup_venv.sh

# 运行脚本
./setup_venv.sh
```

---

## 📋 脚本做了什么？

自动化脚本会执行以下步骤：

1. ✅ 检查 Python 版本 (需要 3.10+)
2. ✅ 创建虚拟环境 (venv/)
3. ✅ 激活虚拟环境
4. ✅ 升级 pip 到最新版本
5. ✅ 让你选择安装类型：
   - Full (所有 LLM 提供商)
   - Minimal (仅 Anthropic Claude)
   - Azure OpenAI
   - OpenAI
   - Development (开发环境)
6. ✅ 安装依赖包
7. ✅ 安装 AvatarFactory (可编辑模式)
8. ✅ 检查 .env 配置
9. ✅ 运行验证测试

---

## 🛠️ 手动安装步骤

如果您不想使用自动化脚本，可以手动执行：

### Step 1: 创建虚拟环境

```bash
# Windows
python -m venv venv

# macOS/Linux
python3 -m venv venv
```

### Step 2: 激活虚拟环境

```bash
# Windows CMD
venv\Scripts\activate.bat

# Windows PowerShell
venv\Scripts\Activate.ps1

# Windows Git Bash
source venv/Scripts/activate

# macOS/Linux
source venv/bin/activate
```

激活成功后，命令行前会显示 `(venv)`。

### Step 3: 升级 pip

```bash
python -m pip install --upgrade pip
```

### Step 4: 安装依赖

选择适合您的 requirements 文件：

```bash
# 完整安装 (所有 LLM 提供商)
pip install -r requirements.txt

# 最小安装 (仅 Anthropic Claude)
pip install -r requirements-minimal.txt

# Azure OpenAI
pip install -r requirements-azure.txt

# OpenAI
pip install -r requirements-openai.txt

# 开发环境
pip install -r requirements-dev.txt
```

### Step 5: 安装 AvatarFactory

```bash
pip install -e .
```

### Step 6: 配置环境变量

```bash
# 复制示例配置
cp .env.example .env  # macOS/Linux
copy .env.example .env  # Windows

# 编辑 .env 添加您的 API keys
```

### Step 7: 验证安装

```bash
python verify_install.py
```

---

## 🔄 日常使用

### 激活虚拟环境

每次打开新终端时，需要激活虚拟环境：

```bash
# Windows CMD
venv\Scripts\activate.bat

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows Git Bash / macOS / Linux
source venv/bin/activate
```

### 使用 AvatarFactory

```bash
# 激活 venv 后
(venv) $ avatarfactory chat
(venv) $ avatarfactory create-persona "..."
(venv) $ avatarfactory generate "..."
```

### 退出虚拟环境

```bash
deactivate
```

---

## 📦 更新依赖

### 更新所有包

```bash
# 激活 venv
source venv/bin/activate  # 或其他激活命令

# 更新
pip install --upgrade -r requirements.txt
```

### 更新特定包

```bash
pip install --upgrade anthropic
pip install --upgrade openai
```

---

## 🗑️ 删除虚拟环境

如果需要重新开始：

```bash
# 1. 退出虚拟环境
deactivate

# 2. 删除 venv 目录
# Windows
rmdir /s venv

# macOS/Linux
rm -rf venv

# 3. 重新运行安装脚本
./setup_venv.sh  # 或 setup_venv.bat/ps1
```

---

## 🐛 故障排除

### 问题 1: "python: command not found"

**Windows:**
```cmd
# 使用完整路径
py -m venv venv
```

**macOS/Linux:**
```bash
# 使用 python3
python3 -m venv venv
```

### 问题 2: "无法激活虚拟环境"

**检查文件是否存在:**
```bash
# Windows
dir venv\Scripts\activate.bat

# macOS/Linux
ls venv/bin/activate
```

**如果不存在，重新创建 venv:**
```bash
rm -rf venv  # 或 rmdir /s venv
python -m venv venv
```

### 问题 3: PowerShell "无法运行脚本"

```powershell
# 临时允许
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# 或永久允许 (当前用户)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 问题 4: "pip install 失败"

```bash
# 升级 pip
python -m pip install --upgrade pip

# 清理缓存
pip cache purge

# 重试
pip install -r requirements.txt
```

### 问题 5: "avatarfactory command not found"

```bash
# 在 venv 中重新安装
pip install -e .

# 或直接运行
python -m avatarfactory.cli chat
```

---

## 💡 最佳实践

### 1. 总是在项目目录中激活 venv

```bash
cd /path/to/AvatarFactory
source venv/bin/activate  # 或其他激活命令
```

### 2. 使用 requirements.txt 管理依赖

```bash
# 导出当前环境
pip freeze > requirements-freeze.txt

# 对比差异
diff requirements.txt requirements-freeze.txt
```

### 3. 定期更新依赖

```bash
# 每月更新一次
pip install --upgrade -r requirements.txt
```

### 4. 不要提交 venv/ 到 Git

`.gitignore` 中已包含：
```
venv/
```

### 5. 在 CI/CD 中使用

```yaml
# GitHub Actions 示例
- name: Setup Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.10'

- name: Create venv and install
  run: |
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
```

---

## 🎓 进阶技巧

### 使用 virtualenvwrapper (macOS/Linux)

```bash
# 安装
pip install virtualenvwrapper

# 配置 (添加到 ~/.bashrc 或 ~/.zshrc)
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

# 使用
mkvirtualenv avatarfactory
workon avatarfactory
deactivate
```

### 使用 conda (如果已安装)

```bash
# 创建环境
conda create -n avatarfactory python=3.10

# 激活
conda activate avatarfactory

# 安装依赖
pip install -r requirements.txt
```

---

## 📚 相关文档

- [Installation Guide](installation.md) - 详细安装说明
- [Quick Reference](quick-reference.md) - 快速命令参考
- [Python venv 官方文档](https://docs.python.org/3/library/venv.html)

---

## ✅ 检查清单

- [ ] Python 3.10+ 已安装
- [ ] 虚拟环境已创建 (`venv/` 目录存在)
- [ ] 虚拟环境已激活 (命令行显示 `(venv)`)
- [ ] 依赖已安装 (`pip list` 显示包)
- [ ] AvatarFactory 已安装 (`avatarfactory --version` 有输出)
- [ ] .env 文件已配置 (API keys 已添加)
- [ ] 验证通过 (`python verify_install.py` 成功)

---

**快速开始命令 (Windows PowerShell):**

```powershell
.\setup_venv.ps1
```

**快速开始命令 (macOS/Linux):**

```bash
./setup_venv.sh
```

开始使用虚拟环境享受 AvatarFactory 吧！🚀
