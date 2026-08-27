# 炉石盒子 / Meta 数据导入

本项目不会抓取盒子的私有接口。请把你有权使用的数据导出或整理为 UTF-8 CSV/JSON，
再通过 `BoxMetaStats.load(path)` 载入。

CSV 字段：

```text
snapshot_date,mode,rank_band,deck_id,deck_name,hero_class,games,win_rate,opponent_class,matchup_win_rate,card_id,mulligan_keep_rate,drawn_win_rate
```

同一文件可以同时放：

- 套牌总体行：填写套牌、对局数和 `win_rate`，将 `card_id` 留空；
- 职业对局行：额外填写 `opponent_class` 和 `matchup_win_rate`；
- 单卡行：填写 `card_id`、`mulligan_keep_rate`、`drawn_win_rate`。

百分比可以写 `53.2%`、`53.2` 或 `0.532`。训练时务必同时保存日期、模式、分段和样本量，
避免把狂野数据、旧补丁数据或小样本噪声混进标准模式。
