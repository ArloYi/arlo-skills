# 项目发布档案

每个项目可保存 `.codex/release-profile.json`，用于让后续更新直接复用已经确认的信息。由 Codex 自动发现和维护，不要求用户手工填写。

## 核心信息

```json
{
  "schema_version": 2,
  "site": {
    "id": "example-site",
    "production_url": "https://site.invalid/"
  },
  "repository": {
    "remote": "origin",
    "branch": "main",
    "url": "https://github.com/owner/repository.git"
  },
  "release": {
    "version_scheme": "vYYYY.MM.DD.N",
    "timezone": "UTC",
    "log_file": "docs/RELEASES.md"
  },
  "checks": {
    "commands": [["<project-check-command>"]]
  },
  "deployment": {
    "provider": "<provider>",
    "method": "<verified-method>",
    "target": "<non-secret-target-name>",
    "ready": false
  },
  "verification": {
    "urls": [{"url": "https://site.invalid/", "status": 200}]
  }
}
```

首次接入可以逐步补齐。只有 GitHub、部署目标、执行方法、线上验证和恢复方式均已验证，才把 `deployment.ready` 设为 `true`。

## 可选信息

- `artifacts`：需要生成独立发布包时记录来源和目标。
- `verification.release_manifest_path`：网站公开版本标记时使用。
- `rollback`：项目具有明确回滚能力时记录策略和稳定版本。
- `production`：保存最近成功上线的版本、SHA、时间和回滚点。
- `approvals`：保存用户已经批准的常规操作范围。

## 规则

- 真实项目名、域名和部署目标只存在对应项目档案中，不进入 Skill。
- 不保存密码、私钥、Token、AccessKey 或环境变量值。
- 部署凭证仅引用外部 Secret、CLI profile 或 SSH alias 名称。
- 检查命令使用参数数组；发布文件使用安全相对路径。
- GitHub 保存源代码；构建产物是否提交由项目规则和部署方式决定。
- 旧档案继续兼容，不为统一格式强制迁移。

本机注册表只负责把网站名称或别名映射到项目根目录，不提交到任何项目仓库。
