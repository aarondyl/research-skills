# 我的 Codex Skills

个人可复用技能的云端备份与版本记录。

## 技能

- [paper-pdf-zh-mirror](skills/paper-pdf-zh-mirror/SKILL.md)：将英文科研论文转换成保留原始图片、公式、分页与学术字体层级的中文镜像 PDF。

## 更新备份

在已登录 GitHub、安装 Git 的 Windows 电脑上，从仓库目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File ./sync-skills.ps1 -Push
```

默认从当前用户 `.codex/skills` 复制自建技能，排除 `.system`、隐藏目录、缓存、密钥配置和生成的 PDF/图片。只执行脚本不加 `-Push` 时仅更新本地文件；加上 `-Push` 才提交并上传。没有配置后台或定时同步。

脚本不删除备份中已有的文件。重命名或删除技能后，应在仓库中明确处理对应旧文件。技能内若需要图片素材，可审查后单独加入版本控制。第三方插件与系统自带技能不在默认备份范围。

也可以指定来源：

```powershell
./sync-skills.ps1 -SkillsPath 'C:/path/to/custom-skills' -Push
```

## 恢复到另一台电脑

克隆私有仓库后，将 `skills` 下所需技能目录复制到该电脑的 `~/.codex/skills/`。已有同名技能时先比较差异，避免覆盖本地修改。重开会话后可用 `$paper-pdf-zh-mirror` 调用。

此仓库保存技能说明、脚本和验证记录，不包含原始论文 PDF、输出 PDF、系统字体或 API 密钥。论文转换依赖和限制见技能内文档。
