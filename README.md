# 相机租赁统计系统

这是一个适合学生项目展示的网页版本“相机租赁统计系统”，使用 Python Flask、SQLite、HTML、CSS 和 JavaScript 实现，不依赖复杂前端框架。

## 功能

- 首页：显示总订单数、总收入、未支付订单数、未归还订单数。
- 用户管理：添加、查看、修改、删除用户。
- 相机管理：添加、查看、修改、删除相机，并显示“可租、已租、维修中”状态。
- 租赁订单：选择用户和相机，填写租期，自动计算租赁天数和应付金额，记录实付金额、支付状态、归还状态。
- 统计页面：总收入、按用户统计支付金额、按相机统计租赁次数和收入、按日期范围统计收入、未支付订单、未归还订单。

## 项目结构

```text
相机租赁信息统计/
├─ app.py
├─ init_db.py
├─ seed_data.py
├─ requirements.txt
├─ README.md
├─ camera_rental.db
├─ static/
│  ├─ style.css
│  └─ script.js
└─ templates/
   ├─ base.html
   ├─ index.html
   ├─ users.html
   ├─ cameras.html
   ├─ rentals.html
   └─ stats.html
```

`camera_rental.db` 会在初始化或运行项目时自动生成。

## 数据库表

### users

| 字段 | 说明 |
| --- | --- |
| id | 用户编号 |
| name | 姓名 |
| phone | 电话 |
| note | 备注 |

### cameras

| 字段 | 说明 |
| --- | --- |
| id | 相机编号 |
| brand | 品牌 |
| model | 型号 |
| daily_price | 日租金 |
| status | 状态：可租、已租、维修中 |

### rentals

| 字段 | 说明 |
| --- | --- |
| id | 订单编号 |
| user_id | 用户编号 |
| camera_id | 相机编号 |
| start_date | 开始日期 |
| end_date | 结束日期 |
| rental_days | 租赁天数 |
| daily_price | 下单时日租金 |
| amount_due | 应付金额 |
| amount_paid | 实付金额 |
| payment_status | 支付状态 |
| return_status | 归还状态 |
| created_at | 创建时间 |

## 计算规则

- 租赁天数 = 结束日期 - 开始日期 + 1。
- 应付金额 = 租赁天数 × 日租金。
- 创建或修改未归还订单后，相机状态自动变为“已租”。
- 订单归还后，如果该相机没有其他未归还订单，相机状态自动恢复为“可租”。

## 运行步骤

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 初始化数据库：

```bash
python init_db.py
```

3. 插入测试数据：

```bash
python seed_data.py
```

4. 启动项目：

```bash
python app.py
```

5. 浏览器访问：

```text
http://127.0.0.1:5000
```

## 部署到 Railway

项目已经准备好 Railway 部署文件：

- `requirements.txt`：安装 Flask 和 Gunicorn。
- `Procfile`：告诉平台用 `gunicorn app:app` 启动项目。
- `railway.json`：设置 Railway 的启动命令。
- `app.py`：会读取 Railway 提供的 `PORT` 端口，并自动初始化 SQLite 数据库。

部署步骤：

1. 把整个项目上传到 GitHub 仓库。
2. 打开 Railway，点击 `New Project`。
3. 选择 `Deploy from GitHub repo`。
4. 选择这个项目仓库。
5. 等待 Railway 自动安装依赖并部署。
6. 部署完成后，进入项目服务的 `Settings` 或 `Networking`，点击 `Generate Domain`。
7. 把生成的网址发给别人，对方就可以直接访问。

如果要让 SQLite 数据不因为重新部署而丢失，可以在 Railway 添加 Volume，并设置环境变量：

```text
DATABASE_PATH=/data/camera_rental.db
```

## 测试数据

运行 `python seed_data.py` 后会插入：

- 用户：张三、李四、王五。
- 相机：Canon EOS R6 Mark II、Sony A7M4、Nikon Z6 II、Fujifilm X-T5。
- 订单：包含已支付已归还、未支付未归还等不同状态，方便测试首页和统计页面。

如果数据库中已经有用户数据，脚本不会重复插入测试数据。
