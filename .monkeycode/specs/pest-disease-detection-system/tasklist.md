{
  "project": "pest-disease-detection-system",
  "name": "病虫害检测系统",
  "tasks": [
    {
      "id": "T01",
      "title": "项目初始化与基础架构搭建",
      "description": "初始化前后端项目结构，配置开发环境、Docker Compose、数据库迁移",
      "priority": "high",
      "status": "completed",
      "dependencies": [],
      "subtasks": [
        {
          "id": "T01-1",
          "title": "后端项目初始化",
          "detail": "初始化FastAPI项目，配置目录结构(app/api, app/services, app/models, app/core)，配置SQLAlchemy异步引擎、Alembic迁移、Pydantic配置",
          "estimated_hours": 4,
          "status": "completed"
        },
        {
          "id": "T01-2",
          "title": "前端项目初始化",
          "detail": "使用Vite+Vue3+TypeScript创建项目，安装Element Plus、ECharts、Vue Router、Pinia、Axios，配置目录结构(src/views, src/components, src/api, src/stores)",
          "estimated_hours": 4,
          "status": "completed"
        },
        {
          "id": "T01-3",
          "title": "宝塔+GitHub部署配置",
          "detail": "配置宝塔面板+Nginx+PM2部署方案；GitHub Actions CI/CD工作流自动部署；Nginx反向代理配置；MySQL+阿里云OSS存储",
          "estimated_hours": 3,
          "status": "completed"
        },
        {
          "id": "T01-4",
          "title": "数据库表设计与迁移",
          "detail": "使用SQLAlchemy定义所有表模型(users, detections, tracking_tasks, tracking_updates, model_registry, notifications, knowledge_base, video_frames, api_keys, operation_logs)；MySQL数据库迁移脚本；阿里云OSS文件存储服务",
          "estimated_hours": 6,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T02",
      "title": "用户注册与认证模块",
      "description": "实现用户注册、登录、JWT认证、权限控制",
      "priority": "high",
      "dependencies": ["T01"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T02-1",
          "title": "后端认证API",
          "detail": "实现/auth/register, /auth/login, /auth/logout, PUT /auth/profile接口；JWT Token签发与验证；登录失败计数与账户锁定；bcrypt密码哈希",
          "estimated_hours": 6,
          "status": "completed"
        },
        {
          "id": "T02-2",
          "title": "前端认证页面",
          "detail": "实现登录页面、注册页面、个人设置页面；Axios请求拦截器自动附加Token；路由守卫鉴权；Token刷新逻辑",
          "estimated_hours": 5,
          "status": "completed"
        },
        {
          "id": "T02-3",
          "title": "RBAC权限控制",
          "detail": "实现user/admin角色权限；API中间件权限校验；管理后台访问控制",
          "estimated_hours": 3,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T03",
      "title": "检测路由与模型推理服务",
      "description": "实现云端AI优先+本地YOLO增强的两级检测路由，搭建模型推理服务",
      "priority": "high",
      "dependencies": ["T01"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T03-1",
          "title": "模型推理服务搭建",
          "detail": "搭建独立FastAPI推理服务；YOLO模型动态加载与卸载；GPU加速推理(TensorRT/ONNX Runtime)；/predict和/models/{id}/load接口；模型注册表CRUD",
          "estimated_hours": 8,
          "status": "completed"
        },
        {
          "id": "T03-2",
          "title": "云端AI Agent集成",
          "detail": "集成DeepSeek API；设计病虫害识别Prompt模板；解析AI返回JSON结构；错误处理与重试机制；API调用限流",
          "estimated_hours": 6,
          "status": "completed"
        },
        {
          "id": "T03-3",
          "title": "检测路由服务",
          "detail": "实现DetectionRouter：先调用云端AI分析->匹配本地模型注册表->有匹配则调本地YOLO精确检测->无匹配则返回AI结果；结果标注来源(source字段)",
          "estimated_hours": 6,
          "status": "completed"
        },
        {
          "id": "T03-4",
          "title": "模型注册表管理",
          "detail": "实现model_registry表的CRUD；管理员页面管理模型列表、上传新模型、灰度发布、版本回滚；模型自动注册到检测路由",
          "estimated_hours": 5,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T04",
      "title": "图像检测功能",
      "description": "实现用户上传图片进行病虫害检测的完整流程",
      "priority": "high",
      "dependencies": ["T03"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T04-1",
          "title": "后端图像检测API",
          "detail": "实现POST /detection/image接口；文件上传验证(格式/大小Magic Number)；图像预处理(尺寸调整)；调用检测路由服务；保存检测记录到数据库和OSS；关联环境数据",
          "estimated_hours": 6,
          "status": "completed"
        },
        {
          "id": "T04-2",
          "title": "前端图像检测页面",
          "detail": "实现图片上传组件(拖拽+点击)；检测进度展示；结果展示(边界框标注、病虫害信息卡片、来源标签)；确认保存按钮",
          "estimated_hours": 6,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T05",
      "title": "视频检测功能",
      "description": "实现用户上传视频进行病虫害检测，支持帧采样和全检测跟踪",
      "priority": "high",
      "dependencies": ["T03"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T05-1",
          "title": "后端视频检测API",
          "detail": "实现POST /detection/video接口；视频预处理和关键帧采样(每秒2-3帧)；后台线程异步处理；ByteTracker多目标跟踪；WebSocket进度推送(socket_manager.emit_nowait)；视频检测报告生成(时间轴标注)",
          "estimated_hours": 10,
          "status": "completed"
        },
        {
          "id": "T05-2",
          "title": "前端视频检测页面",
          "detail": "实现视频上传组件；实时进度条；视频检测结果回放(video.js + 时间轴标注)；检测报告展示；检测详情(按类别聚合)、时间轴展示",
          "estimated_hours": 8,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T06",
      "title": "摄像头实时检测功能",
      "description": "实现通过浏览器摄像头进行实时病虫害检测",
      "priority": "high",
      "dependencies": ["T03"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T06-1",
          "title": "后端摄像头检测WebSocket",
          "detail": "实现WS /detection/camera接口；接收前端视频帧；调用检测路由服务；返回标注结果和检测结果JSON；会话管理(开始/停止/保存)",
          "estimated_hours": 8,
          "status": "completed"
        },
        {
          "id": "T06-2",
          "title": "前端摄像头检测页面",
          "detail": "调用getUserMedia获取摄像头视频流；Canvas逐帧截取和绘制；WebSocket双向通信；实时画面叠加检测标注；开始/停止控制；关键截图保存",
          "estimated_hours": 8,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T07",
      "title": "环境数据采集模块",
      "description": "实现检测时自动采集天气、地址、温度等环境数据",
      "priority": "medium",
      "dependencies": ["T01"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T07-1",
          "title": "后端环境数据服务",
          "detail": "集成地图API逆地理编码(高德/百度)；集成天气API获取实时天气(和风天气)；EnvironmentService并行获取地址和天气；手动补充环境数据接口；接口异常处理与降级",
          "estimated_hours": 5,
          "status": "completed"
        },
        {
          "id": "T07-2",
          "title": "前端环境数据集成",
          "detail": "检测页面集成浏览器Geolocation API；环境数据展示卡片；手动输入地址降级方案",
          "estimated_hours": 3,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T08",
      "title": "虫害跟踪模块",
      "description": "实现虫害检测后的持续跟踪和状态管理",
      "priority": "medium",
      "dependencies": ["T04"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T08-1",
          "title": "后端跟踪服务",
          "detail": "实现tracking_tasks和tracking_updates的CRUD；创建跟踪任务(关联检测记录和地理位置)；更新跟踪记录；解决/归档跟踪任务；活跃任务数量限制(100条)",
          "estimated_hours": 5,
          "status": "completed"
        },
        {
          "id": "T08-2",
          "title": "前端跟踪页面",
          "detail": "地图页面(Leaflet)标注虫害位置和状态；跟踪任务列表(筛选/排序)；跟踪详情页(时间线+图片+状态变更)；从检测记录发起跟踪",
          "estimated_hours": 7,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T09",
      "title": "可视化统计模块",
      "description": "实现病虫害检测数据的可视化统计展示",
      "priority": "medium",
      "dependencies": ["T04"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T09-1",
          "title": "后端统计API",
          "detail": "实现GET /detection/stats接口；检测次数趋势统计(按日/周/月)；病虫害类型分布统计；地区分布统计；时间范围筛选；Redis缓存热点统计数据",
          "estimated_hours": 5,
          "status": "completed"
        },
        {
          "id": "T09-2",
          "title": "前端统计页面",
          "detail": "ECharts检测趋势折线图；病虫害类型饼图/柱状图；地区分布热力图(地图叠加)；时间范围选择器；图表交互(点击数据点查看详情)",
          "estimated_hours": 6,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T10",
      "title": "病害知识库模块",
      "description": "实现病害知识库的存储、搜索和展示",
      "status": "completed",
      "subtasks": [
        {
          "id": "T10-1",
          "title": "后端知识库服务",
          "detail": "knowledge_base表CRUD；ChromaDB向量嵌入存储；关键词搜索+语义搜索混合检索；最近更新条目接口；无结果时推荐相近条目；多语言内容支持",
          "status": "completed"
        },
        {
          "id": "T10-2",
          "title": "前端知识库页面",
          "detail": "知识库搜索页面(搜索框+结果列表)；条目详情页(症状/条件/防治/案例)；最近更新展示；搜索无结果推荐",
          "status": "completed"
        }
      ]
    },
    {
      "id": "T11",
      "title": "用户病害问答Agent",
      "description": "实现基于RAG的病虫害智能问答",
      "status": "completed",
      "subtasks": [
        {
          "id": "T11-1",
          "title": "后端问答Agent服务",
          "detail": "实现QnAAgent：意图分类(病虫害相关/无关) -> ChromaDB向量检索(知识库) -> RAG Prompt构建 -> DeepSeek LLM生成回答 -> 来源标注；对话历史管理；反馈记录",
          "status": "completed"
        },
        {
          "id": "T11-2",
          "title": "前端问答页面",
          "detail": "聊天式问答界面；消息气泡(区分用户和AI)；来源标注展示；超出范围提示；反馈按钮(有用/无用)；对话历史列表",
          "status": "completed"
        }
      ]
    },
    {
      "id": "T12",
      "title": "智能体自动审查与警告推送",
      "description": "实现检测结果自动审查、风险评估、警告生成和推送",
      "priority": "high",
      "dependencies": ["T04", "T10"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T12-1",
          "title": "后端审查智能体",
          "detail": "实现ReviewAgent：审查触发条件判断(置信度>80%或severity=high) -> 构建审查上下文(检测结果+环境数据+地区历史+知识库) -> LLM风险评估 -> 误报判断 -> 警告信息生成 -> 区域预警检测(同地区3天内>=3例) -> 推送通知",
          "estimated_hours": 10,
          "status": "completed"
        },
        {
          "id": "T12-2",
          "title": "后端通知推送服务",
          "detail": "实现NotificationService：站内WebSocket实时推送；Web Push通知(Service Worker)；通知数据库存储；区域批量推送；未读计数管理",
          "estimated_hours": 6,
          "status": "completed"
        },
        {
          "id": "T12-3",
          "title": "前端通知组件",
          "detail": "导航栏未读消息角标；消息中心页面(分类展示：警告/系统/智能体推送)；通知详情查看；标记已读/全部已读；Web Push权限申请",
          "estimated_hours": 5,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T13",
      "title": "管理员后台",
      "description": "实现管理员数据查看、统计分析、模型管理、系统监控等功能",
      "priority": "medium",
      "dependencies": ["T02", "T09"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T13-1",
          "title": "管理仪表板",
          "detail": "实现GET /admin/dashboard接口；概览数据(用户总数/检测总数/活跃用户/预警数)；全局统计图表；数据导出(CSV/Excel)",
          "estimated_hours": 5,
          "status": "completed"
        },
        {
          "id": "T13-2",
          "title": "用户数据管理",
          "detail": "实现GET /admin/users接口；用户列表及检测记录；按时间/地区/病虫害类型筛选；敏感信息脱敏展示",
          "estimated_hours": 4,
          "status": "completed"
        },
        {
          "id": "T13-3",
          "title": "模型管理页面",
          "detail": "模型列表展示(名称/版本/支持的病虫害/指标)；上传新模型；灰度发布配置；版本切换与回滚；模型指标对比",
          "estimated_hours": 6,
          "status": "completed"
        },
        {
          "id": "T13-4",
          "title": "知识库管理页面",
          "detail": "知识条目CRUD；多语言内容编辑；向量嵌入更新；批量导入",
          "estimated_hours": 4,
          "status": "completed"
        },
        {
          "id": "T13-5",
          "title": "系统监控与日志",
          "detail": "服务状态展示(API响应时间/错误率/资源使用率)；操作日志查询(时间/用户/操作类型筛选)；异常告警推送；错误率超5%自动告警",
          "estimated_hours": 6,
          "status": "completed"
        },
        {
          "id": "T13-6",
          "title": "前端管理后台页面",
          "detail": "管理仪表板(ECharts)；用户管理列表；模型管理页面；知识库管理页面；监控面板；日志查看页面；数据导出功能",
          "estimated_hours": 12,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T14",
      "title": "检测历史记录管理",
      "description": "实现用户检测历史的查看、筛选和管理",
      "priority": "medium",
      "dependencies": ["T04"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T14-1",
          "title": "后端历史记录API",
          "detail": "实现GET /detection/history接口；分页查询(默认20条/页)；多条件筛选(时间范围/病虫害类型/检测方式/严重等级)；记录详情接口；查询性能优化(索引+缓存)",
          "estimated_hours": 4,
          "status": "completed"
        },
        {
          "id": "T14-2",
          "title": "前端历史记录页面",
          "detail": "记录列表(时间倒序+分页加载)；筛选条件面板；记录详情弹窗(图片/视频+结果+环境数据+跟踪状态)；无限滚动加载",
          "estimated_hours": 5,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T16",
      "title": "数据安全与隐私保护",
      "description": "实现数据加密、脱敏、异常检测等安全功能",
      "priority": "high",
      "dependencies": ["T02"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T16-1",
          "title": "安全基础设施",
          "detail": "Nginx配置HTTPS(SSL证书)；CORS配置；文件上传安全校验(Magic Number)；速率限制(Redis+中间件)；SQL注入防护(SQLAlchemy参数化查询)",
          "estimated_hours": 5,
          "status": "completed"
        },
        {
          "id": "T16-2",
          "title": "数据脱敏与异常检测",
          "detail": "管理员查看用户数据时脱敏手机号/邮箱；异常访问行为检测(同一IP短时间大量请求)；账户删除7天内清除所有数据；安全日志记录",
          "estimated_hours": 4,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T17",
      "title": "数据导入导出",
      "description": "实现用户检测数据的导入导出功能",
      "priority": "low",
      "dependencies": ["T14"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T17-1",
          "title": "后端导入导出服务",
          "detail": "导出功能：生成JSON/CSV文件(检测记录+环境数据+统计摘要)；异步生成大文件；下载链接24小时过期清理；导入功能：解析模板格式文件；错误行跳过+错误报告生成",
          "estimated_hours": 6,
          "status": "completed"
        },
        {
          "id": "T17-2",
          "title": "前端导入导出页面",
          "detail": "导出按钮+格式选择+时间范围选择；导入上传组件+模板下载；导入结果报告展示；下载链接",
          "estimated_hours": 4,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T18",
      "title": "API接口与第三方集成",
      "description": "实现公开API接口供第三方系统集成",
      "priority": "medium",
      "dependencies": ["T04"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T18-1",
          "title": "API密钥管理",
          "detail": "API密钥生成(哈希存储)；密钥CRUD；密钥过期管理；独立速率限制(按密钥配置)",
          "estimated_hours": 4,
          "status": "completed"
        },
        {
          "id": "T18-2",
          "title": "公开API接口",
          "detail": "API密钥认证中间件；/api/v1/detection/image公开接口(与网页端一致结果)；429速率限制响应；401密钥无效响应；API文档(Swagger/OpenAPI)",
          "estimated_hours": 5,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T19",
      "title": "前端整体布局与响应式",
      "description": "实现响应式布局框架，适配桌面端和移动端",
      "priority": "medium",
      "dependencies": ["T01"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T19-1",
          "title": "布局框架搭建",
          "detail": "实现主布局(顶栏+侧栏+内容区)；响应式断点(桌面/平板/手机)；侧栏折叠；面包屑导航；首页概览",
          "estimated_hours": 5,
          "status": "completed"
        },
        {
          "id": "T19-2",
          "title": "移动端适配",
          "detail": "核心功能移动端可用(检测/查看记录/接收通知)；触摸操作优化；移动端导航(底部Tab栏)",
          "estimated_hours": 5,
          "status": "completed"
        }
      ]
    },
    {
      "id": "T20",
      "title": "集成测试与部署",
      "description": "系统集成测试、性能测试和生产部署",
      "priority": "high",
      "dependencies": ["T02", "T03", "T04", "T05", "T06", "T07", "T08", "T09", "T10", "T11", "T12", "T13"],
      "status": "completed",
      "subtasks": [
        {
          "id": "T20-1",
          "title": "后端单元测试与集成测试",
          "detail": "pytest单元测试(服务层)；API接口集成测试；检测路由测试(云端AI/本地模型/降级)；智能体审查测试；覆盖率>80%",
          "estimated_hours": 10,
          "status": "completed"
        },
        {
          "id": "T20-2",
          "title": "前端E2E测试",
          "detail": "Cypress/Playwright端到端测试；核心流程测试(注册/登录/检测/查看结果)；响应式测试",
          "estimated_hours": 6,
          "status": "completed"
        },
        {
          "id": "T20-3",
          "title": "性能测试",
          "detail": "图像检测响应时间测试(<5秒)；并发检测压力测试；数据库查询性能测试；WebSocket并发连接测试",
          "estimated_hours": 6,
          "status": "completed"
        },
        {
          "id": "T20-4",
          "title": "生产部署",
          "detail": "Docker镜像构建与优化；Nginx生产配置(HTTPS/反向代理/静态资源)；环境变量管理；数据库备份策略；日志收集与监控告警",
          "estimated_hours": 8,
          "status": "completed"
        }
      ]
    }
  ],
  "total_estimated_hours": 290,
  "phases": [
    {
      "name": "Phase 1 - 基础架构",
      "tasks": ["T01", "T02", "T19"],
      "goal": "完成项目骨架搭建、用户认证和前端布局"
    },
    {
      "name": "Phase 2 - 核心检测",
      "tasks": ["T03", "T04", "T05", "T06"],
      "goal": "完成检测路由、图像/视频/摄像头三大检测功能"
    },
    {
      "name": "Phase 3 - 数据与智能",
      "tasks": ["T07", "T08", "T09", "T10", "T11", "T12"],
      "goal": "完成环境数据、跟踪、统计、知识库、问答Agent和智能体审查"
    },
    {
      "name": "Phase 4 - 管理与扩展",
      "tasks": ["T13", "T14", "T16", "T17", "T18"],
      "goal": "完成管理后台、历史记录、国际化、安全、导入导出、API集成"
    },
    {
      "name": "Phase 5 - 测试与部署",
      "tasks": ["T20"],
      "goal": "完成测试和生产部署"
    }
  ]
}
