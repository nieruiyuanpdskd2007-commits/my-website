# Hearthstone Standard Agent

面向炉石传说标准模式决策研究的 V0.1 工程。当前版本的验收目标是：**两套固定 30 张牌组，
由两个 Agent 通过统一的 Observation → Legal Actions → Next State 闭环完整打一局**。

## 现在已经能做什么

- 起手换牌（后手含硬币）；
- 隐藏对手手牌身份，只暴露手牌数量与公共历史；
- 出随从、定向法术、武器、随从攻击、英雄攻击、英雄技能、结束回合；
- 法力、嘲讽、冲锋、护甲、疲劳、爆牌、手牌/场面上限和胜负判定；
- Random、Rule 和 rollout-MCTS 三种 Agent；
- 固定维度状态向量和 Transformer 风格 Entity Token；
- Self-play 轨迹与 JSONL Replay Buffer；
- 炉石盒子/其他 Meta 胜率数据的 CSV/JSON 导入接口；
- 可复现种子、详细对局日志和标准库 `unittest` 测试。
- Windows/macOS 置顶聊天小窗、只读 `Power.log` 监听和隐私最小化的公开事件记录；
- 强制模式策略：练习/好友/复盘可建议，天梯仅记牌与赛后复盘，永不控制鼠标键盘。

## 运行

项目没有第三方运行依赖，Python 3.11+ 即可：

```bash
cd 炉石传说agent
python3 main.py
python3 main.py --agent-a rule --agent-b random --games 10
python3 main.py --agent-a rule --agent-b random --verbose
python3 -m unittest discover -s tests -v
```

## 桌面实时顾问

直接打开完整桌面控制中心：

```bash
python3 desktop_main.py
```

主窗口提供开始监听、停止、打开/关闭顾问小窗、选择模式、浏览日志以及彻底退出。关闭主窗口或点击
“退出软件”都会停止后台监听；顾问小窗可单独关闭，再从主窗口重新打开。

先用内置演示确认小窗可以正常显示：

```bash
python3 -m live.main --mode practice --demo
```

连接只读游戏日志（路径因系统与国服客户端版本而异，建议显式指定）：

```bash
python3 -m live.main \
  --mode practice \
  --log-path "C:\\path\\to\\Hearthstone\\Logs\\Power.log" \
  --player-id 1
```

好友模式将 `practice` 改成 `friendly`。无图形环境可验证推荐逻辑：

```bash
python3 -m live.main --mode practice --demo --console
python3 -m live.main --mode ladder --demo --console
```

安全边界写死在 `ModePolicy` 中：

- `practice` / `friendly` / `replay`：可根据完整公开局面给出动作、目标、理由、备选和风险；
- `ladder`：对局中只显示公开记牌/状态摘要，结束后使用已记录的公开事件复盘；
- `unknown`：默认关闭实时建议；
- 所有模式：不注入游戏进程、不读内存、不显示对手隐藏牌、不点击或拖动卡牌。

目前的日志解析器已经能安全跟随日志、识别实体/公开 Tag/动作块并隐藏对手手牌身份；要让真实
标准卡组获得准确的逐步建议，还需要下一阶段把完整日志状态映射到 RosettaStone 的合法动作与
卡牌 mechanics。`--demo` 展示的是这个接口的端到端交互，并不代表所有线上卡牌已经可执行。

### 打包成 Windows 软件

在 Windows PowerShell 中运行：

```powershell
.\scripts\build_windows.ps1
```

脚本使用 Python 3.12 创建隔离环境、运行测试，再通过 PyInstaller 生成：

```text
dist\HearthstoneStandardAgent.exe
```

双击 EXE 即可像普通软件一样启动，运行时不需要另开命令行。首次公开发布前还应增加应用图标、
代码签名、安装包、自动更新签名校验和 Windows SmartScreen 发布者信誉。

### 注册与登录预留

V0.1 默认是“本地访客”，不会收集或保存密码。主窗口已经保留注册/登录入口，代码通过
`AuthProvider` 隔离认证实现；以后可安全接入正式服务端、邮箱验证、密码哈希、Token 刷新、账号
注销、隐私政策和云端牌组/复盘同步。没有这些服务端安全能力前，按钮只显示说明，不会假装注册成功。

保存自博弈样本并检查训练数据契约：

```bash
python3 main.py --games 20 --replay data/replays/v01.jsonl
python3 -m training.train data/replays/v01.jsonl
```

MCTS 是验证搜索管线的慢速基线；它目前能看到模拟器完整克隆状态，不是最终用于隐藏信息的
IS-MCTS：

```bash
python3 main.py --agent-a mcts --agent-b rule --mcts-simulations 24
```

## 炉石盒子数据怎么接入

可以参考，而且价值很高，但应保持职责分离：

1. 卡牌 ID、费用、身材、文本属于**知识/规则层**；文本并不能自动变成完整可执行规则，仍需为
   RosettaStone 或本模拟器编写 mechanics adapter。
2. 套牌胜率、对局胜率、起手留牌率属于**统计先验层**；可用于挑选训练牌组、起手策略、
   opponent model、模仿学习采样权重和离线评测。
3. 聚合胜率不应直接当作某一步动作的标签；它受分段、补丁、样本量、玩家水平和幸存者偏差影响。

把你有权使用的盒子数据整理成 `data/meta/README.md` 所述 CSV/JSON 后：

```bash
python3 main.py \
  --agent-a meta-rule \
  --agent-b rule \
  --meta-stats data/meta/example.csv \
  --deck-id-a demo_mage
```

项目不抓取私有接口，也不绕过登录/反爬限制。优先使用盒子自身的导出、本地个人战绩，或获得授权的
数据文件；卡牌静态定义则建议同步 HearthstoneJSON/游戏 CardDefs。

## 重要边界

`data/cards.json` 是为了验证工程闭环而内置的**小型机制演示卡池**，不是对当前线上标准卡池的
完整复刻；牌名与数值也不应作为实时天梯依据。当前不会声称支持所有发现、抉择、交易、地标、
泰坦、星舰、复杂光环/亡语/战吼等机制。

要升级到真正 Standard，应将模拟器后端替换为或接入 RosettaStone，并逐张补齐当前标准系列的
可执行规则；`HearthstoneEnv`、Agent、编码器、Replay Buffer 和评测层可以保持不变。

## 自动更新

网站仓库根目录的 `.github/workflows/update-hearthstone-agent-data.yml` 每周二、周五自动运行，也支持手动触发：

1. 从 HearthstoneJSON 的 `latest/zhCN` 下载可收藏卡牌；
2. 在内存中检查数据类型、必填字段、重复 ID 和异常卡牌数量；
3. 生成确定性 gzip 快照、SHA-256、卡牌/系列数和更新时间 manifest；
4. 若配置了仓库 Secret `BOX_META_URL`，同步你有权使用的盒子/Meta 标准模式 CSV；
5. 运行完整回归测试，全部通过后才提交数据变化；任一步失败都不会覆盖上一版。

核心规则和模型代码不会“自我改写”。线上标准轮换也不会按日期猜测：`data/standard_sets.json`
是显式安全门；自动同步发现新系列时会设置 `rotation_review_required`，确认官方轮换后再把系列 ID
加入配置。这个边界能防止新冒险/竞技场/狂野系列被误标为标准。

本地手动刷新：

```bash
python3 scripts/update_data.py
python3 scripts/update_data.py --box-file /path/to/authorized-standard-export.csv
```

## 目录

```text
炉石传说agent/
├── data/                 # 演示卡牌、固定牌组、盒子数据 schema
├── env/                  # 模拟器、合法动作、Observation、编码器
├── agents/               # Random / Rule / MetaRule / MCTS
├── live/                 # 只读日志、公开状态、模式策略与桌面小窗
├── models/               # card vocabulary 与 PolicyValue 接口
├── search/               # rollout search；后续替换为 IS-MCTS
├── training/             # self-play、replay buffer、训练契约
├── evaluation/           # 多局评测
├── tests/
└── main.py
```

## 推荐迭代顺序

- V0.1（当前）：完整游戏闭环、Rule > Random 的可重复评测；
- V0.2：真实标准卡定义同步 + RosettaStone backend adapter + 两套真实固定牌组；
- V0.3：导入对局动作日志做 imitation learning，不只使用总体胜率；
- V0.5：Entity Transformer + Policy/Value + self-play + information-set search；
- V1.0：多职业/多套牌、按补丁切片的 Meta/Opponent Model。
