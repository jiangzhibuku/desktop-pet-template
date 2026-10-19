# Desktop Pet - one-click installer for Windows.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -WithRembg -Run
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -CheckOnly

[CmdletBinding()]
param(
    [switch]$WithRembg,
    [switch]$Run,
    [switch]$NoPause,
    [switch]$CheckOnly,
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root

function Write-Step([string]$Text) {
    Write-Host ""
    Write-Host "==> $Text" -ForegroundColor Magenta
}

function Pause-IfNeeded {
    if (-not $NoPause) {
        Write-Host ""
        Read-Host "按回车关闭窗口" | Out-Null
    }
}

function Fail([string]$Text) {
    Write-Host ""
    Write-Host "错误：$Text" -ForegroundColor Red
    Pause-IfNeeded
    exit 1
}

function Find-Python {
    $candidates = @(
        @{ Exe = "py"; Args = @("-3.12") },
        @{ Exe = "py"; Args = @("-3.11") },
        @{ Exe = "py"; Args = @("-3.10") },
        @{ Exe = "python"; Args = @() }
    )
    if ($Python) {
        $candidates = @(@{ Exe = $Python; Args = @() })
    }
    foreach ($candidate in $candidates) {
        $exe = Get-Command $candidate.Exe -ErrorAction SilentlyContinue
        if (-not $exe) { continue }
        $probeArgs = @($candidate.Args) + @(
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        )
        try {
            $version = & $candidate.Exe @probeArgs 2>$null
            if ($LASTEXITCODE -eq 0 -and $version) {
                return @{ Exe = $candidate.Exe; Args = $candidate.Args; Version = "$version".Trim() }
            }
        } catch {
            continue
        }
    }
    return $null
}

try {
    if ($env:OS -ne "Windows_NT") {
        Fail "这个安装脚本只支持 Windows 10/11。"
    }

    Write-Host "Desktop Pet 安装器" -ForegroundColor Magenta
    Write-Host "项目目录：$Root"

    Write-Step "查找 Python 3.10 - 3.12"
    $pythonInfo = Find-Python
    if (-not $pythonInfo) {
        Fail "没有找到 Python。请先安装 Python 3.12（勾选 Add Python to PATH）：https://www.python.org/downloads/"
    }
    $version = [version]$pythonInfo.Version
    if ($version -lt [version]"3.10" -or $version -ge [version]"3.13") {
        Fail "当前 Python 是 $($pythonInfo.Version)，本项目需要 3.10 - 3.12。请安装 3.12 后重试。"
    }
    Write-Host "使用 Python $($pythonInfo.Version)（$($pythonInfo.Exe)）" -ForegroundColor Green

    if ($CheckOnly) {
        Write-Host "检查通过（CheckOnly，不安装依赖）。" -ForegroundColor Green
        exit 0
    }

    Write-Step "准备虚拟环境 .venv"
    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $venvArgs = @($pythonInfo.Args) + @("-m", "venv", ".venv")
        & $pythonInfo.Exe @venvArgs
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) {
            Fail "创建虚拟环境失败。"
        }
        Write-Host "已创建 .venv" -ForegroundColor Green
    } else {
        Write-Host "复用已有 .venv" -ForegroundColor Green
    }

    Write-Step "升级 pip"
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { Fail "升级 pip 失败，请检查网络。" }

    Write-Step "安装运行依赖（Kivy / requests / Pillow / pywin32）"
    & $venvPython -m pip install -r (Join-Path $Root "requirements.txt")
    if ($LASTEXITCODE -ne 0) { Fail "安装依赖失败，请检查网络或代理。" }

    $hasTk = $true
    try {
        & $venvPython -c "import tkinter" 2>$null
        if ($LASTEXITCODE -ne 0) { $hasTk = $false }
    } catch {
        $hasTk = $false
    }
    if (-not $hasTk) {
        Write-Host "警告：当前 Python 缺少 tkinter，聊天输入框可能无法打开。" -ForegroundColor Yellow
        Write-Host "建议用 python.org 的 Windows 安装包重装 Python。" -ForegroundColor Yellow
    }

    $installRembg = $WithRembg
    if (-not $installRembg -and -not $CheckOnly) {
        Write-Host ""
        Write-Host "可选：本地智能抠图 rembg（首次下载约 170MB 模型）" -ForegroundColor Cyan
        $answer = Read-Host "现在安装吗？[y/N]"
        if ($answer -match "^(y|yes|是)$") { $installRembg = $true }
    }
    if ($installRembg) {
        Write-Step "安装 rembg（本地智能抠图）"
        & $venvPython -m pip install "rembg>=2.0" onnxruntime
        if ($LASTEXITCODE -ne 0) {
            Write-Host "rembg 安装失败，不影响基础功能；之后可手动安装。" -ForegroundColor Yellow
        }
    }

    Write-Step "完成"
    Write-Host "启动桌宠：" -ForegroundColor Green
    Write-Host "  .\.venv\Scripts\python.exe run.py" -ForegroundColor Gray
    Write-Host ""
    Write-Host "生成角色：" -ForegroundColor Green
    Write-Host "  .\.venv\Scripts\python.exe create_pet.py --prompt ""白色小猫，戴红围巾""" -ForegroundColor Gray
    Write-Host ""
    Write-Host "聊天需要把 API Key 填到：%APPDATA%\DesktopPet\config.json" -ForegroundColor Gray

    if ($Run) {
        Write-Step "启动桌宠"
        & $venvPython run.py
    } else {
        Pause-IfNeeded
    }
} catch {
    Fail $_.Exception.Message
}
