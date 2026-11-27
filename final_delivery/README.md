# 学生综合信息管理系统课程设计提交

验证日期 2026-11-19。提交包保存可编辑的 Word、可运行源码以及真实浏览器演示，可分别查看。

| 材料 | 入口 |
| --- | --- |
| 课程设计报告 | [Word 报告](report/软件工程课程设计报告_学生综合信息管理系统.docx)、[证据清单](report/evidence_inventory.md) |
| 完整源码 | [源码 README](source/学生管理系统源码/README.md)、[依赖清单](source/学生管理系统源码/requirements.txt) |
| UML 与验收截图 | [UML 索引](uml/README.md)、[阶段 8 截图](screenshots/) |
| 系统演示 | [MP4 成片](video/系统演示.mp4)、[脚本](video/视频演示脚本.md)、[录制清单](video/视频录制清单.md) |
| 本地部署 | [Windows 安装](deployment/windows_setup.md)、[SQLite 备份恢复](deployment/backup_restore.md) |
| 质量核验 | [阶段 9 总结](testing/stage9_report.md)、[阶段 8 验收](testing/stage8_report.md)、[测试矩阵](testing/stage8_test_matrix.md)、[安全审查](testing/stage8_security_review.md)、[文件摘要](manifest.json) |

Word 为正式提交版，共 27 页。封面的姓名、学号、指导教师及提交日期留给提交人填写。编辑后如分页有变，右击目录并选择“更新整个目录”。视频为 5 分 42 秒，实际操作使用虚构课堂数据，附普通话合成旁白。

将 ZIP 解压到自己选择的目录，从 PowerShell 进入 `final_delivery/source/学生管理系统源码`，再执行 Windows 部署文档中的命令。项目使用 Python 3.12.10，课堂模式通过环境变量选择独立实例，首次管理员由操作者初始化。
