---

软件工程实验四：面向对象的系统建模 B

UML 状态图建模 + Python 状态机实现，共三道题（B1 ~ B3）。

## 目录结构（实验四新增）

```
├── diagrams/                    # B1~B3 状态图（SVG 源文件 + PNG 插图）
├── src/
│   ├── statekit.py              # 状态机骨架（转移表驱动）
│   ├── B1_thermostat.py         # 恒温水箱
│   ├── B2_control_panel.py      # SafeHome 控制面板
│   └── B3_string_extractor.py   # 源文件字符串提取
└── tools/                       # 状态图生成脚本（fb1~fb3.py + render_sm.sh）
```

## 运行

```bash
python src/B1_thermostat.py
python src/B2_control_panel.py
python src/B3_string_extractor.py
```

三个脚本均只依赖标准库，运行时会打印每一次状态转移的轨迹。

## 题目与实现对应关系

| 题号 | 建模内容                       | 关键状态图要素                    | 实现文件                     |
| -- | -------------------------- | -------------------------- | ------------------------ |
| B1 | 恒温水箱（20℃~100℃）             | 复合状态、定时事件、守卫条件、转移上的动作      | `B1_thermostat.py`       |
| B2 | SafeHome 控制面板 ControlPanel | 选择伪状态、自环、扩展状态（错误次数 / 锁定计时） | `B2_control_panel.py`    |
| B3 | 源文件字符串提取                   | 三状态解析、转义状态的判定优先级           | `B3_string_extractor.py` |

## 代码与模型的对应说明

- **状态**：每个圆角框对应一个 `Enum` 成员，值即中文状态名，打印轨迹时直接可读。
- **转移**：图中的每条线写成 `Transition(src, event, dst, guard, action)` 一行，表中顺序即匹配优先级。
- **守卫**：`guard` 函数返回 `bool`，例如 B1 的 `need_heat`（水温 < 20℃ 且有水）、B2 的 `wrong_and_lock`（第 3 次错误）。
- **动作**：`action` 函数只改对象属性（继电器、缓冲区、计数器），不改变状态。
- **复合状态**：B1 的"恒温烧水过程"把 23:00 断电、07:00 上电、水箱烧坏三条转移收敛到复合状态边界，扁平化需要 6 条，复合后只需 3 条。
- **选择伪状态**：B2 的密码校验用三条互斥守卫的转移表达，避免造一个只停留一瞬的"校验"状态。

## 重新生成状态图

```bash
bash tools/render_sm.sh
```

---

# Markdown 版本（便于 Gitee 在线阅读 / 博客发布）

| 文件                             | 内容                             |
| ------------------------------ | ------------------------------ |
| `software-engineering-lab4.md` | 实验四报告（状态图建模 B，3 图 5 表 + 4 段代码） |
| `README.md`                    | 本文件：目录结构、运行方式、题目与实现对应关系        |

该 md 由 `tools/docx2md.py` 从 docx 自动转换，图片引用为仓库内相对路径（`diagrams/*.png`），  
在 Gitee / VS Code / Typora 中可直接预览。若修改了 docx，重新执行：

```bash
python tools/docx2md.py
```
