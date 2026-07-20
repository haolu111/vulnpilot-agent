# nuclei-templates 项目学习笔记

## 1. 学习目标

本学习笔记面向“基于 RAG 的 Web 漏洞知识库与 PoC 辅助分析系统”项目。学习 `projectdiscovery/nuclei-templates` 的重点不是直接使用模板进行漏洞扫描，而是理解它的 **PoC 模板结构、漏洞知识字段、YAML 规则表达方式**，并进一步将模板解析为适合 RAG 知识库使用的结构化文档。

核心目标可以概括为：

> 看懂一个 nuclei YAML 模板 → 抽取漏洞知识字段 → 转换为标准化 Markdown / JSONL → 写入向量数据库 → 支持漏洞问答、检测逻辑解释和修复建议生成。

---

## 2. nuclei-templates 项目简介

`nuclei-templates` 是 ProjectDiscovery 维护的 Nuclei 扫描器模板库。Nuclei 本身是一个基于 YAML 模板的安全检测工具，而 `nuclei-templates` 则保存了大量社区贡献和官方维护的检测模板。

这些模板用于描述：

- 检测什么漏洞；
- 影响什么产品；
- 请求如何构造；
- 响应如何匹配；
- 漏洞严重程度如何；
- 修复建议是什么；
- 参考链接有哪些。

对于 RAG 知识库来说，`nuclei-templates` 的价值在于它是一种半结构化漏洞知识数据源。它比普通漏洞文章更规整，比纯 PoC 代码更容易解析，也比 CVE 页面更接近“实际检测逻辑”。

---

## 3. 为什么它适合作为 RAG 漏洞知识库数据源

普通 CVE 页面通常包含漏洞描述、评分、影响范围、参考链接，但不一定包含具体检测请求。普通 PoC 代码虽然包含利用或检测逻辑，但结构往往不统一，难以批量解析。

而 nuclei YAML 模板通常同时包含：

| 信息类型 | 对应字段 |
|---|---|
| 漏洞编号 | `id`、`classification.cve-id` |
| 漏洞名称 | `info.name` |
| 危害等级 | `info.severity` |
| 漏洞描述 | `info.description` |
| 漏洞影响 | `info.impact` |
| 修复建议 | `info.remediation` |
| 影响产品 | `info.metadata.vendor`、`info.metadata.product`、`tags` |
| CVSS / CWE | `info.classification` |
| PoC 请求 | `http.raw`、`http.method`、`http.path`、`http.body` |
| 匹配条件 | `matchers` |
| 信息提取规则 | `extractors` |
| 参考链接 | `info.reference` |

因此，它天然适合被解析成如下知识库字段：

```json
{
  "cve_id": "CVE-xxxx-xxxx",
  "name": "漏洞名称",
  "severity": "critical",
  "description": "漏洞描述",
  "affected_product": "影响产品",
  "remediation": "修复建议",
  "poc_request": "PoC 请求",
  "matchers": "匹配条件",
  "references": ["参考链接"]
}
```

---

## 4. 项目目录学习重点

学习时不建议一开始全仓库阅读。应优先关注与 Web 漏洞知识库最相关的目录。

常见目录包括：

```text
http/
dns/
file/
network/
ssl/
cloud/
workflows/
helpers/
```

对你的项目来说，最重要的是 `http/` 目录，尤其是：

| 目录 | 学习重点 |
|---|---|
| `http/cves/` | CVE 漏洞模板，最适合做标准化漏洞知识库 |
| `http/vulnerabilities/` | 通用漏洞类型，如 RCE、SQL 注入、文件读取、认证绕过 |
| `http/exposures/` | 敏感信息泄露、配置文件暴露、调试页面暴露 |
| `http/misconfiguration/` | 错误配置类漏洞 |
| `http/default-logins/` | 默认口令、弱口令检测 |
| `http/takeovers/` | 子域接管类风险 |
| `workflows/` | 多模板联动流程，适合后期学习 |

推荐学习顺序：

1. 先看 `http/cves/`；
2. 再看 `http/vulnerabilities/`；
3. 然后看 `http/exposures/`；
4. 最后看 `workflows/`。

---

## 5. nuclei YAML 模板整体结构

一个典型 nuclei 模板大致如下：

```yaml
id: CVE-xxxx-xxxx

info:
  name: Example Product - Vulnerability Name
  author: author-name
  severity: critical
  description: |
    漏洞描述。
  impact: |
    漏洞影响。
  remediation: |
    修复建议。
  reference:
    - https://example.com/advisory
  classification:
    cve-id: CVE-xxxx-xxxx
    cwe-id: CWE-xxx
    cvss-score: 9.8
    cvss-metrics: CVSS:3.1/...
  metadata:
    verified: true
    vendor: example
    product: example-product
  tags: cve,rce,example

http:
  - method: GET
    path:
      - "{{BaseURL}}/vulnerable/path"

    matchers:
      - type: word
        words:
          - "vulnerable"
        part: body
```

可以把模板分成两大部分：

1. **漏洞知识部分**：`id` 和 `info`；
2. **检测逻辑部分**：`http`、`matchers`、`extractors`。

---

## 6. `id` 字段

示例：

```yaml
id: CVE-2026-0545
```

`id` 是模板唯一标识。

它的作用包括：

- 唯一定位模板；
- 作为知识库主键；
- 用于结果去重；
- 用于关联同一个漏洞的不同文档块。

注意：`id` 不一定总是 CVE 编号。有些模板可能写成：

```yaml
id: wordpress-plugin-example-sqli
```

因此，解析脚本中不要直接把 `id` 当作 CVE 编号，而应优先读取：

```yaml
info.classification.cve-id
```

推荐解析逻辑：

```python
template_id = data.get("id")
cve_id = info.get("classification", {}).get("cve-id")

if not cve_id:
    # 再尝试从 id 或 name 中用正则提取 CVE 编号
    pass
```

---

## 7. `info` 信息块

`info` 是模板中最重要的漏洞知识部分，通常包括：

```yaml
info:
  name:
  author:
  severity:
  description:
  impact:
  remediation:
  reference:
  classification:
  metadata:
  tags:
```

### 7.1 `info.name`

示例：

```yaml
name: MLflow Job API - Authentication Bypass
```

可以拆解为：

| 部分 | 含义 |
|---|---|
| MLflow | 影响产品 |
| Job API | 影响组件 |
| Authentication Bypass | 漏洞类型 |

在知识库中可映射为：

```json
{
  "name": "MLflow Job API - Authentication Bypass",
  "affected_product": "MLflow",
  "affected_component": "Job API",
  "vuln_type": "Authentication Bypass"
}
```

### 7.2 `info.author`

示例：

```yaml
author: DhiyaneshDk
```

这是模板作者，不一定是漏洞发现者。

可映射为：

```json
{
  "template_author": "DhiyaneshDk"
}
```

### 7.3 `info.severity`

示例：

```yaml
severity: critical
```

常见取值：

| 原始值 | 中文含义 |
|---|---|
| `critical` | 严重 |
| `high` | 高危 |
| `medium` | 中危 |
| `low` | 低危 |
| `info` | 信息 |

建议脚本中做中英文映射：

```python
severity_map = {
    "critical": "严重",
    "high": "高危",
    "medium": "中危",
    "low": "低危",
    "info": "信息"
}
```

### 7.4 `info.description`

这是漏洞描述字段。

它通常说明：

- 漏洞成因；
- 受影响接口；
- 利用条件；
- 攻击者能力；
- 可能后果。

示例：

```yaml
description: |
  MLflow latest version contains an authentication bypass caused by unprotected FastAPI job endpoints...
```

可抽取为：

```json
{
  "description": "...",
  "root_cause": "FastAPI job endpoints are unprotected",
  "attack_precondition": ["basic-auth enabled", "job execution enabled"],
  "affected_endpoint": "/ajax-api/3.0/jobs/*"
}
```

### 7.5 `info.impact`

这是漏洞影响字段。

常见内容包括：

- 远程代码执行；
- 权限绕过；
- 数据泄露；
- 拒绝服务；
- 文件读取；
- 未授权访问。

注意区分：

```text
模板检测到了认证绕过
```

和：

```text
漏洞可能进一步导致 RCE
```

不能把“潜在影响”直接写成“模板已经验证 RCE”。

### 7.6 `info.remediation`

这是修复建议字段。

示例：

```yaml
remediation: |
  Update to the latest version with fixed authentication enforcement on job endpoints.
```

如果模板有该字段，应优先使用原始修复建议。如果没有，可以生成保守的通用建议，例如：

```text
建议升级至官方修复版本；如暂无法升级，应限制相关接口公网访问，增加身份认证和访问控制，并参考官方安全公告进行修复。
```

建议在知识库中增加：

```json
{
  "remediation_source": "template"
}
```

或：

```json
{
  "remediation_source": "generated_generic"
}
```

避免混淆官方建议和系统生成建议。

### 7.7 `info.reference`

这是参考链接列表。

常见来源：

- NVD；
- GitHub Advisory；
- 厂商公告；
- 安全研究员博客；
- huntr；
- Exploit-DB；
- GitHub commit / issue。

应保存为数组：

```json
{
  "references": [
    "https://nvd.nist.gov/vuln/detail/CVE-xxxx-xxxx",
    "https://github.com/example/project"
  ]
}
```

### 7.8 `info.classification`

这是标准漏洞分类信息。

常见字段：

```yaml
classification:
  cve-id: CVE-xxxx-xxxx
  cwe-id: CWE-306
  cvss-score: 9.1
  cvss-metrics: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N
  epss-score: 0.10825
  epss-percentile: 0.93498
```

字段含义：

| 字段 | 含义 |
|---|---|
| `cve-id` | CVE 编号 |
| `cwe-id` | CWE 弱点类型 |
| `cvss-score` | CVSS 分数 |
| `cvss-metrics` | CVSS 向量 |
| `epss-score` | 漏洞被利用概率预测 |
| `epss-percentile` | EPSS 分位 |

CVSS 向量示例：

```text
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N
```

含义：

| 指标 | 含义 |
|---|---|
| `AV:N` | 网络可达 |
| `AC:L` | 攻击复杂度低 |
| `PR:N` | 不需要权限 |
| `UI:N` | 不需要用户交互 |
| `S:U` | 影响范围不变 |
| `C:H` | 机密性影响高 |
| `I:H` | 完整性影响高 |
| `A:N` | 可用性影响无 |

### 7.9 `info.metadata`

这是辅助元数据。

示例：

```yaml
metadata:
  verified: true
  max-request: 1
  vendor: mlflow
  product: mlflow
  shodan-query: title:"MLflow"
  fofa-query: title="MLflow"
```

字段含义：

| 字段 | 含义 |
|---|---|
| `verified` | 模板是否经过验证 |
| `max-request` | 最大请求数 |
| `vendor` | 厂商 |
| `product` | 产品 |
| `shodan-query` | Shodan 资产指纹 |
| `fofa-query` | FOFA 资产指纹 |

对于你的系统，`vendor` 和 `product` 非常重要，应进入 metadata 用于过滤检索。

### 7.10 `info.tags`

示例：

```yaml
tags: cve,cve2026,mlflow,auth-bypass
```

标签通常包含：

- 是否 CVE；
- 年份；
- 产品名；
- 漏洞类型；
- 技术栈；
- 风险类型。

解析时建议转成列表：

```python
tags = info.get("tags", "")
if isinstance(tags, str):
    tags = [t.strip() for t in tags.split(",")]
```

---

## 8. HTTP 请求部分

HTTP 模板通常有两种写法：

### 8.1 结构化写法

```yaml
http:
  - method: GET
    path:
      - "{{BaseURL}}/example"

    headers:
      User-Agent: nuclei

    body: |
      test=data
```

### 8.2 raw 原始请求写法

```yaml
http:
  - raw:
      - |
        POST /ajax-api/3.0/jobs/ HTTP/1.1
        Host: {{Hostname}}
        Content-Type: application/json

        {"job_name":"run_task","params":{"command":"id"}}
```

raw 请求需要进一步拆解：

| 部分 | 示例 |
|---|---|
| 方法 | `POST` |
| 路径 | `/ajax-api/3.0/jobs/` |
| 协议版本 | `HTTP/1.1` |
| 请求头 | `Host`、`Content-Type` |
| 请求体 | JSON body |

对 RAG 知识库来说，应抽取成：

```json
{
  "poc_request": {
    "protocol": "http",
    "method": "POST",
    "path": "/ajax-api/3.0/jobs/",
    "headers": {
      "Host": "{{Hostname}}",
      "Content-Type": "application/json"
    },
    "body": "{\"job_name\":\"run_task\",\"params\":{\"command\":\"id\"}}"
  }
}
```

---

## 9. Nuclei 变量

模板中经常出现变量，例如：

| 变量 | 含义 |
|---|---|
| `{{BaseURL}}` | 目标基础 URL |
| `{{Hostname}}` | 目标主机名 |
| `{{Host}}` | 目标 Host |
| `{{Port}}` | 目标端口 |
| `{{RootURL}}` | 根 URL |

在解析为知识库时，一般不需要替换这些变量，只需要保留原文，并在文档中说明这是运行时变量。

例如：

```text
`{{BaseURL}}` 是 nuclei 运行时替换变量，表示目标基础 URL。
```

---

## 10. matchers 匹配条件

`matchers` 是 nuclei 模板的核心，它决定“什么情况下认为漏洞存在”。

常见类型：

| 类型 | 作用 |
|---|---|
| `status` | 匹配 HTTP 状态码 |
| `word` | 匹配响应中的关键词 |
| `regex` | 用正则匹配响应内容 |
| `dsl` | 使用表达式组合复杂条件 |
| `binary` | 匹配二进制内容 |
| `size` | 匹配响应大小 |
| `xpath` | 匹配 XML/HTML 结构 |

### 10.1 `status` 示例

```yaml
matchers:
  - type: status
    status:
      - 200
```

含义：

```text
当响应状态码为 200 时匹配。
```

### 10.2 `word` 示例

```yaml
matchers:
  - type: word
    words:
      - "admin"
    part: body
```

含义：

```text
当响应体中包含 admin 字符串时匹配。
```

### 10.3 `regex` 示例

```yaml
matchers:
  - type: regex
    regex:
      - "version: ([0-9.]+)"
```

含义：

```text
当响应内容满足正则表达式时匹配。
```

### 10.4 `dsl` 示例

```yaml
matchers:
  - type: dsl
    dsl:
      - 'contains_all(body, "\"job_id\":", "\"job_name\":")'
      - 'contains(content_type, "application/json")'
      - 'status_code == 200'
    condition: and
```

含义：

```text
响应体同时包含 job_id 和 job_name；
响应类型包含 application/json；
HTTP 状态码为 200；
三个条件必须同时满足。
```

### 10.5 `condition`

`condition` 控制多个匹配条件之间的关系。

| 值 | 含义 |
|---|---|
| `and` | 所有条件都满足 |
| `or` | 任一条件满足即可 |

---

## 11. extractors 提取器

`extractors` 用于从响应中提取信息。

示例：

```yaml
extractors:
  - type: regex
    regex:
      - "version: ([0-9.]+)"
```

它通常用于：

- 提取版本号；
- 提取 token；
- 提取用户名；
- 提取路径；
- 提取响应中的关键信息。

对 RAG 知识库来说，extractors 可以转化为：

```json
{
  "extractors": [
    {
      "type": "regex",
      "purpose": "extract version information",
      "regex": "version: ([0-9.]+)"
    }
  ]
}
```

---

## 12. 以 CVE-2026-0545 为例的模板分析

示例模板：

```yaml
id: CVE-2026-0545

info:
  name: MLflow Job API - Authentication Bypass
  author: DhiyaneshDk
  severity: critical
  description: |
    MLflow latest version contains an authentication bypass caused by unprotected FastAPI job endpoints under /ajax-api/3.0/jobs/* when basic-auth is enabled, letting unauthenticated network clients submit and manage jobs, exploit requires job execution enabled and allowlisted job functions.
  impact: |
    Unauthenticated attackers can execute jobs remotely, potentially leading to remote code execution, denial of service, or data exposure.
  remediation: |
    Update to the latest version with fixed authentication enforcement on job endpoints.
  classification:
    cvss-score: 9.1
    cve-id: CVE-2026-0545
    cwe-id: CWE-306
  metadata:
    verified: true
    max-request: 1
    vendor: mlflow
    product: mlflow
  tags: cve,cve2026,mlflow,auth-bypass

http:
  - raw:
      - |
        POST /ajax-api/3.0/jobs/ HTTP/1.1
        Host: {{Hostname}}
        Content-Type: application/json

        {"job_name":"run_task","params":{"command":"id"}}

    matchers:
      - type: dsl
        dsl:
          - 'contains_all(body, "\"job_id\":", "\"job_name\":")'
          - 'contains(content_type, "application/json")'
          - 'status_code == 200'
        condition: and
```

### 12.1 漏洞基本信息

| 字段 | 内容 |
|---|---|
| CVE 编号 | `CVE-2026-0545` |
| 漏洞名称 | `MLflow Job API - Authentication Bypass` |
| 影响产品 | `MLflow` |
| 影响组件 | `Job API` |
| 漏洞类型 | 认证绕过 |
| 危害等级 | 严重 |
| CVSS 分数 | 9.1 |
| CWE | CWE-306，关键功能缺失认证 |

### 12.2 漏洞成因

该漏洞由 MLflow 的 FastAPI Job API 端点未正确执行认证控制导致。受影响路径是：

```text
/ajax-api/3.0/jobs/*
```

当 basic-auth 已启用时，这些 Job API 端点仍可能被未认证客户端访问，导致攻击者可以提交和管理 jobs。

### 12.3 利用前提

根据模板描述，漏洞成立需要满足：

1. 目标使用 MLflow；
2. basic-auth 已启用；
3. job execution 已启用；
4. 存在 allowlisted job functions；
5. 攻击者可以网络访问目标服务。

### 12.4 漏洞影响

未认证攻击者可以远程提交 jobs。根据 allowlisted job functions 的能力，可能进一步造成：

- 远程代码执行；
- 拒绝服务；
- 数据泄露；
- 非授权任务提交；
- 任务滥用。

### 12.5 PoC 请求

模板发送的请求是：

```http
POST /ajax-api/3.0/jobs/ HTTP/1.1
Host: {{Hostname}}
Content-Type: application/json

{"job_name":"run_task","params":{"command":"id"}}
```

它的含义是：

- 请求方法：`POST`；
- 请求路径：`/ajax-api/3.0/jobs/`；
- 请求类型：JSON；
- 请求体中尝试创建名为 `run_task` 的 job；
- 参数中包含 `command: id`。

注意：这个模板主要验证“未认证 job 创建是否成功”，并没有直接匹配 `id` 命令输出。因此不能简单说该模板直接验证了命令执行成功。

更准确的说法是：

> 如果该请求在未认证情况下成功返回 job 创建信息，则说明目标 Job API 可能存在认证绕过风险。

### 12.6 匹配条件

模板要求同时满足三个条件：

```yaml
- 'contains_all(body, "\"job_id\":", "\"job_name\":")'
- 'contains(content_type, "application/json")'
- 'status_code == 200'
```

可翻译为：

1. 响应体同时包含 `"job_id":` 和 `"job_name":`；
2. 响应类型包含 `application/json`；
3. HTTP 状态码为 `200`。

三个条件之间是：

```yaml
condition: and
```

也就是说，必须全部满足才认为命中。

### 12.7 检测逻辑自然语言解释

该模板向目标 MLflow 服务的 `/ajax-api/3.0/jobs/` 接口发送一个未携带认证信息的 POST 请求。如果目标返回 HTTP 200，响应类型为 JSON，并且响应体中包含 `job_id` 与 `job_name` 字段，则说明目标可能允许未认证用户创建 job，从而存在 CVE-2026-0545 认证绕过漏洞。

---

## 13. 从 YAML 转换为 RAG 文档的推荐格式

不要把 YAML 原文直接整体塞入向量库。更推荐先转换为标准化 Markdown。

示例：

```markdown
# CVE-2026-0545 - MLflow Job API Authentication Bypass

## 基本信息
- 漏洞名称：MLflow Job API - Authentication Bypass
- CVE编号：CVE-2026-0545
- CWE编号：CWE-306
- 危害等级：严重（critical）
- CVSS分数：9.1
- 影响产品：MLflow
- 影响组件：Job API
- 受影响接口：/ajax-api/3.0/jobs/*
- 漏洞类型：认证绕过
- 标签：cve, cve2026, mlflow, auth-bypass

## 漏洞描述
MLflow 的 FastAPI Job API 在 basic-auth 启用时，`/ajax-api/3.0/jobs/*` 下的接口没有正确受到认证和授权保护。攻击者在未认证的情况下，如果能够访问目标服务，且目标启用了 job execution 并配置了 allowlisted job functions，则可能提交和管理 jobs。

## 影响
未认证攻击者可以远程提交 jobs，可能进一步导致远程代码执行、拒绝服务或数据泄露。是否能进一步造成 RCE，取决于 allowlisted job functions 是否包含 shell 执行、文件系统修改等高风险操作。

## PoC 请求
请求方法：POST  
请求路径：/ajax-api/3.0/jobs/  
请求头：Content-Type: application/json  
请求体：{"job_name":"run_task","params":{"command":"id"}}

## 匹配条件
当响应同时满足以下条件时，认为目标可能存在该漏洞：
1. HTTP 状态码为 200；
2. 响应类型包含 application/json；
3. 响应体同时包含 `"job_id":` 和 `"job_name":`。

## 修复建议
升级 MLflow 到修复了 Job API 认证检查的最新版本。若暂时无法升级，应禁用 job execution，限制 `/ajax-api/3.0/jobs/*` 的网络访问，并审查 allowlisted job functions，避免允许高风险操作。

## 参考链接
- https://huntr.com/bounties/...
- https://nvd.nist.gov/vuln/detail/CVE-2026-0545
- https://github.com/mlflow/mlflow
```

---

## 14. 推荐的知识库 JSON Schema

后续解析脚本建议统一输出如下 schema：

```json
{
  "template_id": "",
  "cve_id": "",
  "cwe_id": "",
  "name": "",
  "severity": "",
  "severity_zh": "",
  "cvss_score": null,
  "cvss_metrics": "",
  "epss_score": null,
  "epss_percentile": null,
  "description": "",
  "impact": "",
  "remediation": "",
  "vendor": "",
  "product": "",
  "affected_component": "",
  "affected_endpoint": "",
  "vuln_type": "",
  "tags": [],
  "references": [],
  "verified": null,
  "max_request": null,
  "poc_request": {
    "protocol": "",
    "method": "",
    "path": "",
    "headers": {},
    "body": "",
    "raw": ""
  },
  "matchers": [],
  "extractors": [],
  "asset_fingerprint": {
    "shodan_query": "",
    "fofa_query": ""
  },
  "source_file": ""
}
```

---

## 15. RAG 入库策略

### 15.1 初级策略：一个模板一个 Document

```text
一个 YAML 模板 → 一个 Markdown 文档 → 一个 Document
```

优点：

- 实现简单；
- 便于调试；
- 适合初版 demo。

缺点：

- 文档可能过长；
- 检索粒度不够细；
- 用户问修复建议时可能检索到 PoC 请求部分。

### 15.2 推荐策略：一个模板拆成多个 Document

建议拆为：

```text
Document 1：基本信息 + 漏洞描述
Document 2：影响产品 + 利用前提
Document 3：PoC 请求
Document 4：匹配条件
Document 5：修复建议 + 参考链接
```

每个 Document 共享 metadata：

```json
{
  "cve_id": "CVE-2026-0545",
  "severity": "critical",
  "product": "mlflow",
  "vuln_type": "auth-bypass",
  "source_file": "http/cves/2026/CVE-2026-0545.yaml"
}
```

这样用户问不同问题时可以更精准检索：

| 用户问题 | 最相关文档块 |
|---|---|
| 这个漏洞是什么？ | 基本信息 + 漏洞描述 |
| 如何检测？ | PoC 请求 + 匹配条件 |
| 如何修复？ | 修复建议 |
| 影响哪个产品？ | 基本信息 + 影响产品 |
| 为什么判断命中？ | 匹配条件 |

---

## 16. Metadata 设计建议

向量数据库中的 metadata 不要太少。建议至少保留：

```json
{
  "template_id": "CVE-2026-0545",
  "cve_id": "CVE-2026-0545",
  "severity": "critical",
  "severity_zh": "严重",
  "vendor": "mlflow",
  "product": "mlflow",
  "vuln_type": "auth-bypass",
  "cwe_id": "CWE-306",
  "cvss_score": 9.1,
  "tags": "cve,cve2026,mlflow,auth-bypass",
  "protocol": "http",
  "source_file": "..."
}
```

这样可以支持：

```text
查询所有 high/critical 漏洞
查询某个产品的漏洞
查询某类漏洞，如 RCE、SQL 注入、认证绕过
查询某个 CVE
查询某个 CWE 类型
```

---

## 17. YAML 解析脚本思路

### 17.1 遍历模板文件

```python
from pathlib import Path

template_dir = Path("nuclei-templates")

yaml_files = list(template_dir.rglob("*.yaml")) + list(template_dir.rglob("*.yml"))
```

### 17.2 读取 YAML

```python
import yaml

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
```

### 17.3 解析基础字段

```python
def parse_info(data):
    info = data.get("info", {})
    classification = info.get("classification", {})
    metadata = info.get("metadata", {})

    tags = info.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    return {
        "template_id": data.get("id"),
        "name": info.get("name"),
        "author": info.get("author"),
        "severity": info.get("severity"),
        "description": info.get("description"),
        "impact": info.get("impact"),
        "remediation": info.get("remediation"),
        "references": info.get("reference", []),
        "cve_id": classification.get("cve-id"),
        "cwe_id": classification.get("cwe-id"),
        "cvss_score": classification.get("cvss-score"),
        "cvss_metrics": classification.get("cvss-metrics"),
        "epss_score": classification.get("epss-score"),
        "epss_percentile": classification.get("epss-percentile"),
        "vendor": metadata.get("vendor"),
        "product": metadata.get("product"),
        "verified": metadata.get("verified"),
        "max_request": metadata.get("max-request"),
        "shodan_query": metadata.get("shodan-query"),
        "fofa_query": metadata.get("fofa-query"),
        "tags": tags
    }
```

### 17.4 解析 HTTP raw 请求

```python
import re

def parse_raw_http(raw_text):
    lines = raw_text.strip().splitlines()
    first_line = lines[0]

    method = None
    path = None
    headers = {}
    body_lines = []
    in_body = False

    m = re.match(r"([A-Z]+)\s+(\S+)\s+HTTP/\d(?:\.\d)?", first_line)
    if m:
        method = m.group(1)
        path = m.group(2)

    for line in lines[1:]:
        if line.strip() == "":
            in_body = True
            continue

        if not in_body and ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()
        elif in_body:
            body_lines.append(line)

    return {
        "method": method,
        "path": path,
        "headers": headers,
        "body": "\n".join(body_lines),
        "raw": raw_text
    }
```

### 17.5 解析 matchers

```python
def parse_matchers(http_block):
    matchers = http_block.get("matchers", [])
    result = []

    for matcher in matchers:
        result.append({
            "type": matcher.get("type"),
            "condition": matcher.get("condition"),
            "part": matcher.get("part"),
            "words": matcher.get("words"),
            "regex": matcher.get("regex"),
            "status": matcher.get("status"),
            "dsl": matcher.get("dsl")
        })

    return result
```

---

## 18. 生成 Markdown 文档

```python
def to_markdown(item):
    return f"""# {item.get("cve_id") or item.get("template_id")} - {item.get("name")}

## 基本信息
- 模板ID：{item.get("template_id")}
- CVE编号：{item.get("cve_id")}
- CWE编号：{item.get("cwe_id")}
- 漏洞名称：{item.get("name")}
- 危害等级：{item.get("severity")}
- CVSS分数：{item.get("cvss_score")}
- 厂商：{item.get("vendor")}
- 产品：{item.get("product")}
- 标签：{", ".join(item.get("tags", []))}

## 漏洞描述
{item.get("description") or "模板未提供明确漏洞描述。"}

## 漏洞影响
{item.get("impact") or "模板未提供明确影响说明。"}

## PoC请求
{item.get("poc_request")}

## 匹配条件
{item.get("matchers")}

## 修复建议
{item.get("remediation") or "建议升级至官方修复版本，并根据厂商公告进行加固。"}

## 参考链接
{item.get("references")}
"""
```

---

## 19. 学习路线安排

### 第 1 阶段：了解项目结构

时间：1–2 天

任务：

- 克隆 `nuclei-templates`；
- 浏览 README；
- 查看 `http/cves/`、`http/vulnerabilities/`；
- 随机选择 10 个 CVE 模板阅读。

目标：

- 知道 nuclei 模板是什么；
- 知道模板目录如何组织；
- 知道 YAML 模板基本长什么样。

### 第 2 阶段：精读模板字段

时间：2–3 天

任务：

- 总结 `id`、`info`、`classification`、`metadata`、`tags`；
- 总结 `http`、`raw`、`matchers`、`extractors`；
- 每个字段找 2–3 个真实模板例子。

目标：

- 看到一个模板后，能解释它检测什么漏洞、请求是什么、如何判断命中。

### 第 3 阶段：手动转换文档

时间：2 天

任务：

- 选 5 个 CVE 模板；
- 手动整理为 Markdown 漏洞知识文档；
- 形成统一文档模板。

目标：

- 明确 YAML 到 RAG 文档的转换规则。

### 第 4 阶段：编写解析脚本

时间：3–4 天

任务：

- 批量读取 YAML；
- 抽取基础字段；
- 解析 HTTP 请求；
- 解析 matchers；
- 输出 JSONL；
- 输出 Markdown 文档。

目标：

- 完成 `nuclei_yaml_parser.py` 初版。

### 第 5 阶段：接入 RAG 知识库

时间：3–4 天

任务：

- 将 Markdown 文档切块；
- 将 metadata 写入 ChromaDB；
- 支持按 CVE、产品、危害等级、漏洞类型过滤；
- 设计漏洞问答 prompt。

目标：

- 实现“基于 nuclei-templates 的 Web 漏洞知识库问答 demo”。

---

## 20. 后续系统可以支持的问题

接入 RAG 后，系统应支持如下问题：

```text
CVE-2026-0545 是什么漏洞？
这个漏洞影响什么产品？
这个漏洞危害等级是多少？
这个漏洞的利用条件是什么？
这个模板如何检测漏洞？
为什么响应中包含 job_id 和 job_name 就说明可能存在漏洞？
这个漏洞如何修复？
有哪些 MLflow 的严重漏洞？
有哪些认证绕过漏洞？
列出所有 critical 级别的 Web 漏洞。
```

---

## 21. 面试 / 汇报时的总结话术

可以这样介绍：

> nuclei-templates 是 ProjectDiscovery 维护的 Nuclei 模板库，其中每个模板都是一个 YAML 格式的漏洞检测规则。模板不仅包含 PoC 请求，还包含漏洞名称、CVE 编号、危害等级、漏洞描述、影响产品、修复建议、匹配条件和参考链接。因此，它可以作为 Web 漏洞知识库的半结构化数据源。  
>
> 在我的系统中，我计划**将 nuclei YAML 模板解析成标准化 JSON 和 Markdown 文档。**`id` 和 `classification.cve-id` 映射为漏洞编号，`info.name` 映射为漏洞名称，`info.severity` 映射为危害等级，`info.description` 和 `info.impact` 映射为漏洞描述和影响，`metadata.vendor/product` 映射为影响产品，`http.raw` 或 `http.method/path/body` 映射为 PoC 请求，`matchers` 映射为检测依据，`reference` 映射为参考链接。  
>
> 之后，这些 **Markdown 文档会被切块并写入向量数据库**，同时保留 CVE、产品、危害等级、漏洞类型等 metadata。这样用户就可以通过自然语言查询漏洞原理、利用条件、检测逻辑和修复建议，从而形成一个面向 Web 漏洞知识的 RAG 辅助分析系统。

---

## 22. 一句话总结

`nuclei-templates` 的核心学习价值不是“会不会运行扫描”，而是理解它如何用 YAML 把漏洞知识和检测逻辑结构化表达。对于你的 RAG 项目来说，它正好可以作为漏洞知识库的数据格式样例：将 YAML 模板解析为结构化字段和 Markdown 文档，再结合 metadata 过滤与向量检索，就可以构建面向 CVE、漏洞类型、PoC 请求、匹配条件和修复建议的 Web 漏洞知识库。
