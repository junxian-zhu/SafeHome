# -*- coding: utf-8 -*-
"""B1 恒温水箱 —— 状态图对应的 Python 实现。

状态图要点（见图 B1）：
    恒温水箱 = 休眠 + 复合状态"恒温烧水过程"（检测 / 加热）+ 维修
    - 07:00 上电 → 进入恒温烧水过程，由初始伪状态进入"检测"
    - 检测：水温 < 20℃ 且有水 → 闭合继电器，进入"加热"
            水温 ≥ 20℃ 或 无水 → 保持断电（自环）
    - 加热：水温 = 100℃ → 断开继电器，回到"检测"
    - 任一子状态收到 23:00 定时事件 → 断开总电源，进入"休眠"
    - 水箱烧坏 → "维修"；维修完成 → 重新进入恒温烧水过程
"""
from __future__ import annotations

from enum import Enum
from typing import Dict

from statekit import StateMachine, Transition


class TankState(Enum):
    SLEEP = "休眠"
    SENSING = "检测"
    HEATING = "加热"
    REPAIR = "维修"


# ---------- 守卫（对应状态图转移上的 [ ] 条件） ----------
def at(hour: int):
    return lambda sm, ctx: ctx.get("hour") == hour


def need_heat(sm: "WaterTank", ctx: Dict) -> bool:
    """水温低于 20℃ 且水箱有水 —— 才允许闭合继电器。"""
    return ctx["temperature"] < 20 and ctx["has_water"]


def keep_off(sm: "WaterTank", ctx: Dict) -> bool:
    """水温已达 20℃ 或 无水 —— 保持断电。"""
    return not (ctx["temperature"] < 20 and ctx["has_water"])


def boiling(sm: "WaterTank", ctx: Dict) -> bool:
    return ctx["temperature"] >= 100


def not_boiling(sm: "WaterTank", ctx: Dict) -> bool:
    return ctx["temperature"] < 100


class WaterTank(StateMachine):
    """恒温水箱控制器。"""

    def __init__(self) -> None:
        self.relay_on = False          # 继电器（加热电源）状态
        self.temperature = 25.0
        self.has_water = True
        self.repaired = False
        super().__init__("恒温水箱", TankState.SLEEP, [
            # ---- 定时事件 ----
            Transition(TankState.SLEEP, "TIME", TankState.SENSING,
                       action=self._power_on, guard=at(7),
                       label="07:00 / 上电自检"),
            Transition(TankState.SENSING, "TIME", TankState.SLEEP,
                       action=self._power_off, guard=at(23),
                       label="23:00 / 断开总电源"),
            Transition(TankState.HEATING, "TIME", TankState.SLEEP,
                       action=self._power_off, guard=at(23),
                       label="23:00 / 断开总电源"),
            # ---- 检测状态 ----
            Transition(TankState.SENSING, "SENSE", TankState.HEATING,
                       action=self._relay_on, guard=need_heat,
                       label="水温<20℃ 且有水 / 闭合继电器"),
            Transition(TankState.SENSING, "SENSE", TankState.SENSING,
                       guard=keep_off,
                       label="水温≥20℃ 或 无水 / 保持断电"),
            # ---- 加热状态 ----
            Transition(TankState.HEATING, "SENSE", TankState.SENSING,
                       action=self._relay_off, guard=boiling,
                       label="水温=100℃ / 断开继电器"),
            Transition(TankState.HEATING, "SENSE", TankState.HEATING,
                       guard=not_boiling,
                       label="水温<100℃ / 继续加热"),
            # ---- 故障与维修 ----
            Transition(TankState.SENSING, "FAULT", TankState.REPAIR,
                       action=self._relay_off, label="水箱烧坏 / 停止加热"),
            Transition(TankState.HEATING, "FAULT", TankState.REPAIR,
                       action=self._relay_off, label="水箱烧坏 / 停止加热"),
            Transition(TankState.REPAIR, "REPAIRED", TankState.SENSING,
                       action=self._after_repair, label="维修完成 / 重新自检"),
        ])

    # ---------- 动作 ----------
    def _power_on(self, sm, ctx):
        print("    · 上电，进入恒温烧水过程")

    def _power_off(self, sm, ctx):
        self.relay_on = False
        print("    · 断开总电源，继电器复位")

    def _relay_on(self, sm, ctx):
        self.relay_on = True
        print(f"    · 继电器闭合，开始加热（当前 {self.temperature}℃）")

    def _relay_off(self, sm, ctx):
        self.relay_on = False
        print("    · 继电器断开，停止加热")

    def _after_repair(self, sm, ctx):
        self.repaired = True
        print("    · 维修完成，重新自检")

    # ---------- 对外接口 ----------
    def sense(self, temperature: float, has_water: bool = True) -> None:
        """温度/水量传感器采样一次。"""
        self.temperature, self.has_water = temperature, has_water
        self.send("SENSE", temperature=temperature, has_water=has_water)

    def time_event(self, hour: int) -> None:
        self.send("TIME", hour=hour)

    def fault(self) -> None:
        self.send("FAULT")

    def repair_done(self) -> None:
        self.send("REPAIRED")


def main() -> None:
    print("=== B1 恒温水箱状态机 ===")
    tank = WaterTank()

    print("\n[1] 07:00 定时上电")
    tank.time_event(7)

    print("\n[2] 检测到 18℃，有水 → 应当开始加热")
    tank.sense(18.5, has_water=True)
    print(f"    继电器：{'闭合' if tank.relay_on else '断开'}，状态：{tank.state.value}")

    print("\n[3] 水温升到 99℃ → 继续加热；升到 100℃ → 断开电源")
    tank.sense(99.0)
    tank.sense(100.0)
    print(f"    继电器：{'闭合' if tank.relay_on else '断开'}，状态：{tank.state.value}")

    print("\n[4] 水温 25℃，高于 20℃ → 保持断电（自环）")
    tank.sense(25.0)

    print("\n[5] 水温 18℃ 但水箱无水 → 不闭合继电器（自环）")
    tank.sense(18.0, has_water=False)
    print(f"    继电器：{'闭合' if tank.relay_on else '断开'}，状态：{tank.state.value}")

    print("\n[6] 加水后水温 18℃ → 开始加热；此时水箱烧坏 → 转维修")
    tank.sense(18.0, has_water=True)
    tank.fault()
    print(f"    继电器：{'闭合' if tank.relay_on else '断开'}，状态：{tank.state.value}")
    tank.repair_done()

    print("\n[7] 加热中收到 23:00 定时事件 → 断开电源进入休眠")
    tank.sense(18.0, has_water=True)
    tank.time_event(23)
    print(f"    继电器：{'闭合' if tank.relay_on else '断开'}，状态：{tank.state.value}")

    print(f"\n状态轨迹：{tank.path}")


if __name__ == "__main__":
    main()
