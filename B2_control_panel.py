# -*- coding: utf-8 -*-
"""B2 SafeHome 控制面板 ControlPanel —— 状态图对应的 Python 实现。

状态图要点（见图 B2）：
    空闲 --按下按键--> 读取键入字符
    读取键入字符 --键入字符 / 长度<4--> 读取键入字符（自环，显示 *）
    读取键入字符 --长度=4--> 校验（选择伪状态）
        密码正确                → 系统功能选择
        密码错误 且 次数<3      → 读取键入字符（次数+1，清空缓冲区）
        错误次数=3              → 锁定
    锁定 --计时<120 秒--> 锁定（自环）
    锁定 --超过 120 秒--> 空闲
    系统功能选择 --功能执行完毕 / 取消--> 空闲
"""
from __future__ import annotations

from enum import Enum
from typing import Dict

from statekit import StateMachine, Transition


class PanelState(Enum):
    IDLE = "空闲"
    READING = "读取键入字符"
    LOCKED = "锁定"
    MENU = "系统功能选择"


# ---------- 守卫：校验用的是"已输入 + 本次按键" ----------
def _candidate(sm: "ControlPanel", ctx: Dict) -> str:
    return sm.buffer + ctx["char"]


def still_short(sm, ctx):
    return len(sm.buffer) < 3


def correct(sm, ctx):
    return len(sm.buffer) == 3 and _candidate(sm, ctx) == sm.password


def wrong_and_retry(sm, ctx):
    return len(sm.buffer) == 3 and _candidate(sm, ctx) != sm.password and sm.fails < 2


def wrong_and_lock(sm, ctx):
    return len(sm.buffer) == 3 and _candidate(sm, ctx) != sm.password and sm.fails >= 2


def locked_timeout(sm, ctx):
    return ctx["now"] - sm.locked_at >= sm.lock_seconds


def still_locked(sm, ctx):
    return ctx["now"] - sm.locked_at < sm.lock_seconds


class ControlPanel(StateMachine):
    """SafeHome 控制面板。密码 4 位，连续错误 3 次锁定 120 秒。"""

    def __init__(self, password: str = "1234", lock_seconds: int = 120) -> None:
        self.password = password
        self.lock_seconds = lock_seconds
        self.buffer = ""
        self.fails = 0            # 连续错误次数
        self.locked_at = 0.0
        self.now = 0.0
        super().__init__("ControlPanel", PanelState.IDLE, [
            Transition(PanelState.IDLE, "KEY", PanelState.READING,
                       action=self._start, label="按下按键 / 清空缓冲区"),
            Transition(PanelState.READING, "KEY", PanelState.READING,
                       action=self._append, guard=still_short,
                       label="键入字符 长度<4 / 缓存并显示 *"),
            Transition(PanelState.READING, "KEY", PanelState.MENU,
                       action=self._accept, guard=correct,
                       label="密码正确 / 进入功能选择"),
            Transition(PanelState.READING, "KEY", PanelState.READING,
                       action=self._reject, guard=wrong_and_retry,
                       label="密码错误 且 次数<3 / 次数+1，清空"),
            Transition(PanelState.READING, "KEY", PanelState.LOCKED,
                       action=self._lock, guard=wrong_and_lock,
                       label="错误次数=3 / 锁定 120 秒"),
            Transition(PanelState.LOCKED, "TICK", PanelState.LOCKED,
                       guard=still_locked, label="计时<120 秒"),
            Transition(PanelState.LOCKED, "TICK", PanelState.IDLE,
                       action=self._unlock, guard=locked_timeout,
                       label="超过 120 秒 / 解除锁定"),
            Transition(PanelState.MENU, "SELECT", PanelState.IDLE,
                       action=self._finish, label="功能执行完毕"),
            Transition(PanelState.MENU, "CANCEL", PanelState.IDLE,
                       action=self._finish, label="取消"),
        ])

    # ---------- 动作 ----------
    def _start(self, sm, ctx):
        self.buffer = ctx["char"]
        print(f"    · 开始输入：{self._masked()}")

    def _append(self, sm, ctx):
        self.buffer += ctx["char"]
        print(f"    · 已输入 {len(self.buffer)}/4：{self._masked()}")

    def _accept(self, sm, ctx):
        self.buffer = ""
        self.fails = 0
        print("    · 密码正确，进入系统功能选择")

    def _reject(self, sm, ctx):
        self.fails += 1
        self.buffer = ""
        print(f"    · 密码错误，连续错误 {self.fails} 次，清空缓冲区")

    def _lock(self, sm, ctx):
        self.fails += 1
        self.buffer = ""
        self.locked_at = self.now
        print(f"    · 连续错误 {self.fails} 次，锁定 {self.lock_seconds} 秒")

    def _unlock(self, sm, ctx):
        self.buffer = ""
        self.fails = 0
        self.locked_at = None
        print("    · 锁定超时，解除锁定，允许再次输入")

    def _finish(self, sm, ctx):
        print("    · 功能结束，返回空闲")

    def _masked(self) -> str:
        return "*" * len(self.buffer)

    # ---------- 对外接口 ----------
    def key(self, ch: str) -> None:
        self.send("KEY", char=ch)

    def type_code(self, code: str) -> None:
        for ch in code:
            self.key(ch)

    def advance(self, seconds: float) -> None:
        self.now += seconds
        self.send("TICK", now=self.now)

    def select(self) -> None:
        self.send("SELECT")

    def cancel(self) -> None:
        self.send("CANCEL")


def main() -> None:
    print("=== B2 SafeHome 控制面板状态机 ===")
    panel = ControlPanel(password="1234", lock_seconds=120)

    print("\n[1] 输入正确密码 1234")
    panel.type_code("1234")
    print(f"    状态：{panel.state.value}")

    print("\n[2] 选择功能后返回空闲")
    panel.select()

    print("\n[3] 连续输错 3 次")
    for i in range(3):
        print(f"  第 {i + 1} 次错误输入：")
        panel.type_code("0000")
    print(f"    状态：{panel.state.value}，锁定中：{panel.locked_at is not None}")

    print("\n[4] 60 秒后仍在锁定（自环）")
    panel.advance(60)
    print(f"    状态：{panel.state.value}")

    print("\n[5] 超过 120 秒后自动解锁")
    panel.advance(61)
    print(f"    状态：{panel.state.value}")

    print("\n[6] 解锁后再输正确密码")
    panel.type_code("1234")
    print(f"    状态：{panel.state.value}")
    panel.cancel()

    print(f"\n状态轨迹：{panel.path}")


if __name__ == "__main__":
    main()
