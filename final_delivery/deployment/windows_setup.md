# Windows 课堂部署

验收环境为 Windows 11 家庭版、Python 3.12.10（64 位）、PowerShell。项目使用本地 Bootstrap 和 SQLite，应用运行无需 Node.js。网络或可用的本地包源仅用于安装依赖。

## 安装并创建独立实例

在解压后的项目目录执行。已有项目虚拟环境时，可把 `$demoRoot` 下的新环境用于单独复现。

```powershell
# 在 PowerShell 进入解压后的 source/学生管理系统源码 目录
py -3.12 --version
$demoRoot = Join-Path $env:TEMP ('sms-classroom-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $demoRoot | Out-Null
py -3.12 -m venv (Join-Path $demoRoot 'venv')
$python = Join-Path $demoRoot 'venv\Scripts\python.exe'
& $python --version
& $python -m pip install -r requirements.txt
& $python -m pip check
```

后续命令调用该 Python 的绝对路径。安装记录使用 Python 3.12.10，`include-system-site-packages=false`，22 个固定依赖全部安装通过。[新环境安装记录](../testing/stage8_fresh_install.txt)

## 迁移及初始化

```powershell
$env:APP_ENV = 'demo'
$env:SMS_INSTANCE_PATH = Join-Path $demoRoot 'instance'
Remove-Item Env:SMS_DATABASE_URI -ErrorAction SilentlyContinue
$env:ACTIVE_SEMESTER = '2026-Fall'
$env:DEMO_PORT = '8000'
& $python -X utf8 -m flask --app run db upgrade
& $python -X utf8 -m flask --app run db check
& $python -X utf8 -m flask --app run seed-roles
& $python -X utf8 -m flask --app run create-admin
& $python -X utf8 -m flask --app run seed-demo
& $python -X utf8 -m flask --app run routes
```

`create-admin` 交互输入用户名和两次密码。重复用户名会拒绝并保留原账号。另两条种子命令可重复运行，第二次新增数为 0。演示记录均为虚构，教师和学生账号由管理员在“用户管理”中创建并绑定已有档案。继续使用已有课堂数据时，将实例变量设为原课堂目录再运行迁移检查。[实测命令](../testing/stage8_deployment_commands.txt) · [数据库结构与角色结果](../testing/stage8_fresh_deployment.json)

## 运行与关闭

```powershell
& $python -X utf8 run.py
```

用浏览器打开 [系统首页](http://127.0.0.1:8000/) 或 [健康检查](http://127.0.0.1:8000/health)，在运行窗口按 Ctrl+C 停止。

| 模式 | 用途 | 配置与行为 |
| --- | --- | --- |
| development | 本机开发 | 默认 `python run.py`，127.0.0.1:5000，保留 Flask 调试配置。数据库默认位于 `instance/student_management.db` |
| testing | 自动化 | `python -m pytest`，测试配置和数据库隔离 |
| demo | 本机课堂演示 | `APP_ENV=demo`，只监听 127.0.0.1，`DEMO_PORT` 默认 8000，允许 1–65535。禁用调试和自动重载，每次启动生成 32 字节随机密钥。默认课堂实例为 `instance/demo` |
| production | HTTPS 部署配置 | 需要稳定的随机环境密钥，开启 Secure Cookie。直接运行 `run.py` 会拒绝此模式，正式部署需要独立 WSGI 服务及 HTTPS 终止层 |

课堂模式使用本机 HTTP，Cookie 为 HttpOnly 与 SameSite=Lax。课堂密钥不写入磁盘，重启后重新登录。运行课堂服务使用上述 `run.py` 入口。正式部署应另行配置 HTTPS、可信主机、凭据管理和访问日志，属于独立部署工作。

## 常见问题

| 现象 | 处理 |
| --- | --- |
| 找不到 `py -3.12` | 安装带 Python Launcher 的 Python 3.12 x64，重新打开 PowerShell，确认版本。 |
| 依赖安装失败 | 使用同一解释器执行 `-m pip install -r requirements.txt`，检查包源配置和网络。 |
| 端口占用 | 修改当前窗口的 `$env:DEMO_PORT`，再启动并使用同一端口访问。 |
| 空库或缺表 | 确认模式、实例路径和数据库 URI 后执行 `db upgrade` 及 `db check`。 |
| 重启后要登录 | 重新登录取得本次启动的会话和 CSRF。 |
| 选课或成绩列表为空 | 检查配置学期和查询范围。已种入的演示选课学期为 2026-Fall。 |

部署时可执行 `& $python -X utf8 -m pytest -q` 检查完整回归。[备份与恢复](backup_restore.md) · [阶段 8 报告](../testing/stage8_report.md)
