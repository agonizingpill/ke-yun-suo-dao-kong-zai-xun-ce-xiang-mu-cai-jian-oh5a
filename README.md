# 云峡索道 · 空载巡测影子面板

为模拟空载巡测团队编制镜头回看影子面板。RFE 仅选择可选的媒体回看项目，目录锁定项在登记和签发时都照常保留。

云峡例检班的四名模拟调度员为云脊七号保留早晚两班的视频观察记录。以前使用两个手工作业板整理视频，班次记录会互相覆盖，常用镜头留存过多，试行发现的问题没有独立回执。工作台从记录岗的项目明细和人工复看标签出发，提供可按日期留组验证的自选项清单，再由班长审核早、晚两个样本并签发。登记记录、训练候选和已签发版本长期可追溯。

这个应用仅演示媒体和管理流程。目录的 K-11 至 K-13 是虚构训练数据。没有连接实际设备、行车控制、法定目录或启停判断。

| 演示账号 | 角色 | 页面和典型动作 |
|---|---|---|
| duan | technician / 空载记录 | 检查项目目录、登记班次、排队拟合、提交试行回执 |
| ning | supervisor / 复核班长 | 审核和退回试行回执，双班审核后签发并替换影子面板 |
| qin | viewer / 台账查阅 | 查目录、人工标签、排名和双班证据 |

统一演示密码为 `CabinTrial2026!`。

## 两班剧本

1. 11 月 18 日 18:20，记录岗选中车型 Y7，查看自 11 月 1 日开始的 36 笔双班记录。
2. 18:25，复查 Y7-01-A 的人工复看标签，把 11 月 18 日设为训练截止日。
3. 18:30，申报自选项预算 2。工作台保留 3 个训练目录锁定项，再从 6 个可选画面指标内挑 2 个。
4. 11 月 19 日 06:20，早班以 Y7-TRIAL-1 打开并行回看，提交回执。班长通过早报，但此时签发仍被拒。
5. 11 月 20 日 18:10，晚班递交 Y7-TRIAL-2。班长因缺少同步核对说明退回。
6. 18:20，晚班补交，将原录像编号和同步说明入回执，班长再次复核。
7. 18:30，班长确认仅用于影子版并签发。旧版 RP-DEMO-Y7 归档，登记表仍要求填写所有锁定项。

## RFE 和状态规则

历史记录含六个可选媒体项。每折训练数据用 StandardScaler，再以加权 LinearSVC 系数强度做 RFE；每次移除一个变量。GroupKFold 三折按日期分组，防止同日两班分到训练和留出两侧。输出留组 balanced accuracy、逐项排名、样本数、种子 1080、输入 SHA256。缺少六天完整记录、早晚班或两类标签会退回。候选的留组分数比全自选项基线低超过 0.15 时亦退回。分类标签来自人工对录像是否需要复看的标记。

新版本进入试行后，早晚班回执须来自同车型且日期晚于训练截止日，覆盖全部保留项。每班只允许一个待审或已审回执；班长退回时原回执可补交。签发时同事务锁车型和面板、检查锁定项和两班复核、归档旧影子版。签发不会改动班次登记要求。

## 运行

```sh
cp .env.example .env
docker compose config --quiet
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
# 结束演示后移除本项目的容器和数据卷
docker compose down -v --remove-orphans
```

页面 `http://127.0.0.1:18304/`。后端接口文档 `http://127.0.0.1:19304/docs`。

| 组件 | 技术和职责 |
|---|---|
| frontend | HTML、CSS、原生 ES modules 和 Nginx /api 代理 |
| backend | Python 3.12、FastAPI、SQLAlchemy、JWT、审计和业务校验 |
| worker | Python、scikit-learn，使用 Redis 通知，DB 中保留待处理候选 |
| db | PostgreSQL 16，业务关系、唯一约束和事务 |
| redis | Redis 7，消息通知及 AOF |

环境文件定义端口 `FRONTEND_PORT`、`BACKEND_PORT`、`DB_PORT`，数据库 `DB_NAME`、`DB_USER`、`DB_PASSWORD`，签发密钥 `JWT_SECRET` 及演示开关 `SEED_DEMO`。数据库仅绑定 127.0.0.1:17804，Redis 仅供容器内部访问。本地 Python 开发可配置 `DATABASE_URL`、`REDIS_URL`，安装 `backend/requirements.txt`，在 backend 运行 `uvicorn lab.app:app --reload` 和 `python -m lab.worker`。界面代码在 `frontend/src`，后端各业务模型与操作在 `backend/lab`，演示数据在 `backend/scripts`。

班次、面板版本及回执状态见 `backend/lab/constants.py`，由 `run_schema.py`、`run_routes.py`、`panel_service.py`、`trial_service.py` 使用。前端对应标签在 `frontend/src/types.js`，在 `components/board.js`、`pages/runs.js`、`pages/panels.js` 和 `pages/trials.js` 显示。当前项目随工作区交付，无独立开源许可证。
