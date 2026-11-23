# -*- coding: utf-8 -*-
"""B3 源文件字符串提取 —— 状态图对应的 Python 实现。

状态图要点（见图 B3）：
    普通文本 --读到双引号 / 清空缓冲区--> 字符串内
    普通文本 --其他字符--> 普通文本（自环，忽略）
    字符串内 --读到反斜杠--> 转义
    字符串内 --其他字符 / 追加--> 字符串内（自环）
    字符串内 --读到双引号 / 输出缓冲区--> 普通文本
    转义 --任意字符 / 追加该字符（去掉转义符）--> 字符串内

注意：转移判定顺序必须是"反斜杠 → 双引号 → 其他字符"，否则 \\" 会被
误判成字符串结束。
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List

from statekit import StateMachine, Transition


class CharState(Enum):
    TEXT = "普通文本"
    IN_STRING = "字符串内"
    ESCAPE = "转义"


class UnterminatedString(ValueError):
    """文件结束时字符串仍未闭合。"""


def _is_quote(sm, ctx):
    return ctx["char"] == '"'


def _is_backslash(sm, ctx):
    return ctx["char"] == "\\"


def _is_other(sm, ctx):
    return ctx["char"] not in ('"', "\\")


class StringExtractor(StateMachine):
    """从源代码文本中提取所有双引号字符串。"""

    def __init__(self, verbose: bool = False) -> None:
        self.buffer = ""
        self.results: List[str] = []
        super().__init__("StringExtractor", CharState.TEXT, [
            Transition(CharState.TEXT, "CHAR", CharState.IN_STRING,
                       action=self._begin, guard=_is_quote,
                       label="读到双引号 / 清空缓冲区"),
            Transition(CharState.TEXT, "CHAR", CharState.TEXT,
                       guard=_is_other, label="其他字符 / 忽略"),
            Transition(CharState.IN_STRING, "CHAR", CharState.ESCAPE,
                       guard=_is_backslash, label="读到反斜杠"),
            Transition(CharState.IN_STRING, "CHAR", CharState.TEXT,
                       action=self._finish, guard=_is_quote,
                       label="读到双引号 / 输出缓冲区"),
            Transition(CharState.IN_STRING, "CHAR", CharState.IN_STRING,
                       action=self._append, guard=_is_other,
                       label="其他字符 / 追加"),
            Transition(CharState.ESCAPE, "CHAR", CharState.IN_STRING,
                       action=self._append, label="任意字符 / 追加该字符"),
        ])
        self.verbose = verbose

    # ---------- 动作 ----------
    def _begin(self, sm, ctx):
        self.buffer = ""

    def _append(self, sm, ctx):
        self.buffer += ctx["char"]

    def _finish(self, sm, ctx):
        self.results.append(self.buffer)
        self.buffer = ""

    # ---------- 对外接口 ----------
    def feed(self, text: str) -> None:
        for ch in text:
            self.send("CHAR", char=ch)

    def close(self) -> List[str]:
        """文件读取结束：字符串未闭合则报错。"""
        if self.state is not CharState.TEXT:
            raise UnterminatedString(
                f"字符串未闭合，缓冲区残留：{self.buffer!r}")
        return self.results

    @classmethod
    def extract(cls, source: str, verbose: bool = False) -> List[str]:
        sm = cls(verbose=verbose)
        sm.feed(source)
        return sm.close()


def main() -> None:
    print("=== B3 源文件字符串提取状态机 ===")

    print("\n[0] 逐字符状态轨迹（输入：\"a\\\"b\"）")
    trace = StringExtractor(verbose=True)
    for ch in '"a\\"b"':
        print(f"  char={ch!r}")
        trace.send("CHAR", char=ch)
    print(f"  结果：{trace.close()}")

    print("\n[1] 题目示例")
    src = ('#include <stdio.h>\n'
           'int main() {\n'
           '    printf("一般学习一门编程语言的时候，基本上第一个程序是输出\\"Hello World!\\"");\n'
           '    return 0;\n'
           '}\n')
    got = StringExtractor.extract(src)
    for s in got:
        print(f"  提取到：{s}")

    print("\n[2] 多个字符串 + 转义反斜杠")
    src2 = 'p = "C:\\\\dir\\\\a.txt"; name = "测试"; empty = "";\n'
    got2 = StringExtractor.extract(src2)
    for s in got2:
        print(f"  提取到：{s}")

    print("\n[3] 未闭合字符串应当报错")
    try:
        StringExtractor.extract('x = "没有结束')
    except UnterminatedString as e:
        print(f"  已捕获异常：{e}")


if __name__ == "__main__":
    main()
