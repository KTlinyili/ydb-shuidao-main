# 协作开发指南（3天5人冲刺）

## 一、快速上手（每人第一天做一遍）

### 1. 安装环境

```bash
# 安装 Git（已安装可跳过）
# 下载地址：https://git-scm.com/download/win

# 安装 Python 3.10+
# 安装 Node.js 18+

# 配置 Git 用户名和邮箱（只需一次）
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

### 2. 克隆项目

```bash
git clone https://github.com/KTlinyili/ydb-shuidao-main.git
cd ydb-shuidao-main

# 切换到你的分支
git checkout a    # 或 b / c / d / e
```

### 3. 安装依赖

```bash
# 后端依赖
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 前端依赖
cd web
npm install
cd ..
```

### 4. 配置环境变量

```bash
# 复制配置模板
copy .env.example .env

# 用文本编辑器打开 .env，填入你的 API Key
# 至少配一组 LLM（推荐 Silicon Flow 免费额度）
```

### 5. 启动服务

```bash
# 后端
.venv\Scripts\activate
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000

# 前端（新开一个终端）
cd web
npx vite --host 0.0.0.0 --port 5173
```

浏览器打开 http://localhost:5173 确认能跑。

---

## 二、日常开发流程

### 每次开始改代码前

```bash
# 1. 切到你的分支
git checkout a

# 2. 拉取最新代码
git pull origin a
git merge dev    # 同步dev分支的更新
```

### 改完代码后

```bash
# 1. 提交你的改动
git add -A
git commit -m "描述你改了什么"

# 2. 推送到你的分支
git push origin a
```

### 合并到 dev（由指定的人操作）

```bash
git checkout dev
git pull origin dev
git merge a
git merge b
git merge c
git merge d
git merge e

# 有冲突时解决冲突后：
git add -A
git commit -m "merge all branches"
git push origin dev
```

### 最后合并到 main

```bash
git checkout main
git merge dev
git push origin main
```

---

## 三、分支说明

| 分支 | 用途 | 谁能推 |
|------|------|--------|
| main | 稳定版本，能跑的 | 最后统一合并 |
| dev | 开发集成，每天合并 | 指定一人操作 |
| a | A的开发区 | A |
| b | B的开发区 | B |
| c | C的开发区 | C |
| d | D的开发区 | D |
| e | E的开发区 | E |

---

## 四、防冲突约定

1. 只改自己负责的文件，不要碰别人的文件
2. 每次开始前先 git pull
3. 每天中午和晚上各 push 一次，不要攒着
4. .env 文件不要提交（已在 .gitignore 中排除）

---

## 五、项目结构

```
ydb-shuidao-main/
├── app/                 # 后端代码
│   ├── api/            # API路由
│   ├── core/           # 核心配置
│   ├── models/         # YOLO模型（不入库）
│   └── services/       # 业务逻辑
├── web/                 # 前端代码
│   ├── src/
│   │   ├── pages/      # 页面
│   │   ├── components/ # 组件
│   │   └── api/        # API调用
│   └── vite.config.ts
├── mobile/              # 手机端（Flutter）
├── yolo_train/          # 模型训练
├── .env.example         # 环境变量模板
├── requirements.txt     # Python依赖
└── .gitignore
```

---

## 六、常见问题

### Q: git push 报错 Permission denied？
A: 确认你的GitHub账号有这个仓库的写入权限，找仓库管理员添加你为Collaborator。

### Q: git merge 有冲突怎么办？
A: 打开冲突文件，找到 `<<<<<<<` 和 `>>>>>>>` 标记，选择保留哪段代码，删掉标记符号，然后 git add + git commit。

### Q: 改错了想退回？
A: `git checkout 文件名` 退回单个文件，`git reset --hard HEAD` 退回全部改动。

### Q: 前端启动报错？
A: 删掉 node_modules 重新安装：`rm -rf node_modules && npm install`

### Q: 后端启动报错找不到模块？
A: 确认在 .venv 虚拟环境里：`.venv\Scripts\activate`，然后 `pip install -r requirements.txt`
