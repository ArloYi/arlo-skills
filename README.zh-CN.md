# Arlo Skills

一套实用的 AI Skills 合集，涵盖设计研究、网站发布运维、投资分析与 YouTube 创作者筛选，提供英文文档和简体中文概览。

[English](README.md)

仓库中的每个 Skill 都是独立、可安装的能力包，遵循 [Agent Skills](https://agentskills.io/) 开放格式。主入口只保留路由与核心流程，专项知识放在按需读取的 references 中，并通过 CI 做统一结构验证。

## Skill 目录

| 分类 | Skill | 能做什么 |
|---|---|---|
| 设计与产品 | [`design-research-toolkit`](design-research-toolkit/) | 研究视觉参考，将其转化为原创、可执行的设计方向，同时避免复制受保护作品。 |
| 开发与运维 | [`website-release-manager`](website-release-manager/) | 产品开发完成后整理文件和文档，新建或关联 GitHub 仓库，再完成部署、验证和版本记录。 |
| 金融与投资 | [`wealth-compass`](wealth-compass/) | 用证据校准的框架分析公司、资产、宏观环境、投资组合与投资论证。 |
| 营销与增长 | [`youtube-kol-sourcing`](youtube-kol-sourcing/) | 根据具体营销活动搜寻、核验、评分、去重并整理 YouTube 创作者合作名单。 |

## 安装

可以直接让支持 Agent Skills 的智能体安装对应目录：

```text
请安装这个 Agent Skill：
https://github.com/ArloYi/arlo-skills/tree/main/design-research-toolkit
```

按需将最后的目录替换成 `website-release-manager`、`wealth-compass` 或 `youtube-kol-sourcing`。

使用 Codex 时，也可以克隆整个合集，再复制需要的 Skill：

```bash
git clone https://github.com/ArloYi/arlo-skills.git
cp -R arlo-skills/design-research-toolkit ~/.codex/skills/
```

只需安装具体 Skill 目录；仓库根目录的 README、CI 和 eval 文件不属于 Skill 安装内容。

## 使用示例

### 设计与产品

```text
使用 $design-research-toolkit 为这个 SaaS 落地页研究三个视觉方向，说明参考来源，但不要照搬现有作品。
```

### 金融与投资

```text
使用 $wealth-compass 审查这份投资逻辑，把事实、假设、估值、风险和行动触发器分开说明。
```

### 开发与运维

```text
使用 $website-release-manager 整理这个开发完成的网站，新建或关联 GitHub 仓库并上传代码，再完成部署、线上验证和版本记录。
```

### 营销与增长

```text
使用 $youtube-kol-sourcing 为这个活动建立经过核验的 YouTube 创作者名单，并与历史联络表去重。
```

## 整理原则

- `SKILL.md`：触发条件、核心流程、边界与输出合同。
- `references/`：专项知识、判断标准与字段规范，执行时按需读取。
- `agents/openai.yaml`：Codex 中展示的名称、简介与默认提示词。
- `evals/`：正向触发、负向触发和边界案例。
- `scripts/`：确定性的仓库级验证。

## 质量与安全

- 行情、政策、财报、产品条款和创作者指标等时变信息必须在执行时重新核验。
- 第三方网页、搜索结果、评论和 API 响应都是不可信数据，不能改变 Skill 指令。
- 设计研究只提取原则，不复制受保护的表达、品牌或资产。
- 投资分析使用概率、范围和情景表达不确定性，不承诺收益。
- 创作者筛选不得编造联系方式，也不得绕过登录、验证码或平台限制。
- 网站发布不得猜测项目身份、凭证、供应商或生产目标；只部署已留存在远程仓库的精确 SHA，区分日常代码发布与基础设施变更，并要求存在经过验证的回滚路径。
- Skill 发布到公开仓库前必须维护经过筛选、泛化和脱敏的公开副本，不直接镜像本机目录或保留个人习惯与项目数据。

本地验证命令：

```bash
python3 scripts/validate_skills.py
```

## 许可证

仓库中的原创内容采用 [MIT License](LICENSE)。第三方网站、软件、商标、创意作品和链接材料仍受各自许可证与使用条款约束；具体归属说明随相关 Skill 一并保留。
