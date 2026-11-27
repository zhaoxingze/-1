# SQLite 备份与恢复

`scripts/sqlite_snapshot.py` 通过 Python sqlite3 的在线备份 API 生成单文件快照。快照包含已经提交的 WAL 数据，事务中的未提交行留在源库。工具对结果运行 SQLite 完整性和外键检查，输出 UTC 时间、大小及 SHA-256。目标路径必须为新文件，含现有 SQLite 日志边车文件的同名路径也会被拒绝。

## 创建备份

以下命令接续 [Windows 部署](windows_setup.md) 中的 `$python` 和课堂实例配置。目标目录选择当前用户有权限的受保护位置。

```powershell
$source = Join-Path $env:SMS_INSTANCE_PATH 'student_management.db'
$safe = Join-Path $env:LOCALAPPDATA 'StudentManagementSystem\snapshots'
New-Item -ItemType Directory -Path $safe -Force | Out-Null
$stamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmssfff')
$backup = Join-Path $safe "student-management-$stamp.sqlite"
& $python -X utf8 scripts/sqlite_snapshot.py backup $source $backup
if ($LASTEXITCODE -ne 0) { throw 'Backup failed' }
& $python -X utf8 scripts/sqlite_snapshot.py verify $backup
if ($LASTEXITCODE -ne 0) { throw 'Verification failed' }
```

保管备份及记录的哈希、备份时间和版本。数据库快照含账号哈希与实际业务数据，应存放于受访问控制的目录或加密介质，纳入备份保留策略。源码 ZIP 仅包含脚本与无业务内容的验收记录。

## 恢复到新实例

先在独立实例验证，应用原有工作目录和库继续保留。

```powershell
$restoredInstance = Join-Path $env:TEMP ('sms-restore-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $restoredInstance | Out-Null
$restored = Join-Path $restoredInstance 'student_management.db'
& $python -X utf8 scripts/sqlite_snapshot.py restore $backup $restored
if ($LASTEXITCODE -ne 0) { throw 'Restore failed' }
& $python -X utf8 scripts/sqlite_snapshot.py verify $restored
if ($LASTEXITCODE -ne 0) { throw 'Verification failed' }
$env:APP_ENV = 'demo'
$env:SMS_INSTANCE_PATH = $restoredInstance
$env:DEMO_PORT = '8001'
$env:ACTIVE_SEMESTER = '2026-Fall'
Remove-Item Env:SMS_DATABASE_URI -ErrorAction SilentlyContinue
& $python -X utf8 -m flask --app run db check
& $python -X utf8 run.py
```

在独立端口登录，复核三角色权限和关键记录。验证成功后如需切换日常实例，应先关闭原服务并保留原快照，按实际需要调整实例路径。

## 实际验收

阶段 8 在课堂服务器运行时执行 `backup`，随后执行 `restore` 和 `verify`。在不同实例目录、端口上重新启动，逐表对比数据、登录三种角色、复查越权及课程、成绩、考勤、联系与模拟通知读取。自动化测试还覆盖开启 WAL 的写连接、目标已存在、来源损坏和外键失败时的清理。[恢复证据](../reports/stage8_backup_restore.json) · [自动化定向结果](../reports/stage8_targeted_pytest.txt)
