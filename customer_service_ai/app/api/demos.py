"""示例问答 API — 展示调度组件助手能力"""
from fastapi import APIRouter

router = APIRouter(prefix="/demos", tags=["示例问答"])

_DEMOS = [
    {
        "title": "创建作业计划",
        "question": "如何创建一个 Common 类型的作业计划？",
        "answer": """### 作业计划创建

**请求方式：** POST
**接口地址：** `/v1/jobplan/saveCommonJobPlan`

**请求参数：**

| 参数名 | 必填 | 类型 | 说明 |
|--------|------|------|------|
| jobPlanName | Y | String | 作业计划名 |
| jobType | Y | Enum | COMMON / K8S / SHELL |
| priority | Y | Integer | 优先级 1~4 |
| jobScheduleDTO | Y | JobScheduleDTO | 调度规划配置 |
| jobProgramDTO | Y | JobProgramDTO | 程序包配置 |
| remark | N | String | 备注 |

**请求示例：**
```json
{
  "jobPlanName": "每日数据同步",
  "jobType": "COMMON",
  "priority": 2,
  "jobScheduleDTO": {
    "scheduleMode": "CRON",
    "cron": "0 0 2 * * ?"
  },
  "jobProgramDTO": {
    "envType": "JAVA",
    "cmd": "java -jar sync.jar",
    "parameter": [{"name": "--date", "value": "{yyyyMMdd}", "type": "SYSTEM"}],
    "runTimeOut": 3600,
    "retries": 3
  }
}
```

**返回示例：**
```json
{
  "code": "200",
  "msg": "作业计划创建成功",
  "data": 10001
}
```"""
    },
    {
        "title": "查询作业计划",
        "question": "查询作业计划列表的接口是什么？",
        "answer": """### 作业计划列表查询

**请求方式：** POST
**接口地址：** `/v1/jobplan/list`

**请求参数：**

| 参数名 | 必填 | 类型 | 说明 |
|--------|------|------|------|
| page | Y | Integer | 页码，从 1 开始 |
| size | Y | Integer | 每页条数 |
| jobPlanName | N | String | 作业计划名称（模糊查询） |
| jobType | N | Enum | 作业类型筛选 |

**返回参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| code | String | 状态码 |
| data.total | Long | 总条数 |
| data.records | List | 作业计划列表 |

**请求示例：**
```json
{
  "page": 1,
  "size": 20,
  "jobPlanName": "数据同步"
}
```"""
    },
    {
        "title": "通用状态码",
        "question": "接口返回的通用状态码有哪些？",
        "answer": """### 通用状态码说明

所有接口统一返回以下 JSON 结构：
```json
{
  "code": "状态码",
  "data": "返回数据",
  "msg": "返回信息"
}
```

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 00000 | 系统级成功 |
| 40000 | 参数校验失败 |
| 50000 | 执行失败 |
| 50002 | 上线失败 |
| 50003 | 下线失败 |
| 1001 | 名称重复 |
| 1002 | 操作不合法 / 创建或更新失败 |
| 1003 | 作业计划已上线，禁止编辑 |
| 1004 | 查询失败，ID 不存在 |

> 如需查看某个接口的具体返回示例，可以直接问我该接口的详细说明。"""
    },
    {
        "title": "Shell 脚本作业",
        "question": "如何创建 Shell 脚本作业？",
        "answer": """### Shell 脚本作业创建

**请求方式：** POST
**接口地址：** `/v1/jobplan/saveShellJobPlan`

**说明：** 创建 Shell 类型的作业计划，运行自定义 Shell 脚本。

**请求参数与 Common 作业类似，主要差异：**
- `jobType`: 固定为 `SHELL`
- `jobProgramDTO.envType`: 固定为 `SHELL`
- `jobProgramDTO.cmd`: Shell 脚本内容或命令

**请求示例：**
```json
{
  "jobPlanName": "日志清理",
  "jobType": "SHELL",
  "priority": 1,
  "jobScheduleDTO": {
    "scheduleMode": "CRON",
    "cron": "0 0 3 * * ?"
  },
  "jobProgramDTO": {
    "envType": "SHELL",
    "cmd": "find /logs -mtime +7 -name '*.log' -exec rm {} \\;",
    "parameter": [],
    "runTimeOut": 1800,
    "retries": 2
  }
}
```"""
    },
    {
        "title": "调度模式说明",
        "question": "作业调度模式有哪些？怎么配置？",
        "answer": """### 调度模式说明

`jobScheduleDTO.scheduleMode` 支持以下四种模式：

| 模式 | 说明 | 必配参数 |
|------|------|---------|
| ONCE | 单次执行 | startTime |
| INTERVAL | 固定间隔执行 | startTime + interval |
| CRON | Cron 表达式 | cron |
| TRIGGER | 触发式执行（由外部触发） | 无需额外配置 |

**各模式示例：**

**ONCE — 单次执行：**
```json
{"scheduleMode": "ONCE", "startTime": "2026-06-20 10:00:00"}
```

**INTERVAL — 每隔 30 分钟执行：**
```json
{"scheduleMode": "INTERVAL", "startTime": "2026-06-20 10:00:00", "interval": 30}
```

**CRON — 每天凌晨 2 点执行：**
```json
{"scheduleMode": "CRON", "cron": "0 0 2 * * ?"}
```

**TRIGGER — 触发式：**
```json
{"scheduleMode": "TRIGGER"}
```"""
    },
    {
        "title": "历史指标重跑",
        "question": "历史指标如果需要重跑，是什么步骤？",
        "answer": """### 历史指标重跑步骤

**接口地址：** `POST /v1/metrics/rerun`

**触发条件：** 当历史指标数据异常、遗漏或需要修正时，可通过此接口发起重跑。

**步骤说明：**

1. **查询重跑范围** — 确认需要重跑的指标、时间区间（起始日期 ~ 结束日期）
2. **调用重跑接口** — 提交重跑请求，系统将重新计算指定范围内的指标数据
3. **监控运行状态** — 通过重跑任务 ID 查询执行进度
4. **结果校验** — 重跑完成后，核对指标数据是否正确

**请求参数：**

| 参数名 | 必填 | 类型 | 说明 |
|--------|------|------|------|
| metricCodes | Y | List<String> | 需要重跑的指标编码列表 |
| startDate | Y | String | 重跑起始日期，格式 `yyyy-MM-dd` |
| endDate | Y | String | 重跑结束日期，格式 `yyyy-MM-dd` |
| reason | N | String | 重跑原因说明 |

**请求示例：**
```json
{
  "metricCodes": ["JOB_SUCCESS_RATE", "JOB_FAILURE_COUNT"],
  "startDate": "2026-01-01",
  "endDate": "2026-06-01",
  "reason": "数据修正：上游数据源迁移后重跑"
}
```

> 注意：重跑属于耗时操作，期间不会影响现有指标的查询服务。"""
    },
]


@router.get("/")
async def list_demos():
    """获取示例问答列表"""
    return _DEMOS
