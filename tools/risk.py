"""
Quản trị rủi ro & kỷ luật — bài 06.

Công thức position sizing (đã được sửa, file 06):
    Tiền rủi ro     = Vốn × Rủi ro%            (số tiền sẵn sàng mất tối đa/lệnh)
    Vốn giải ngân   = Tiền rủi ro / Cắt lỗ%    (tổng tiền đặt vào cổ phiếu)
    Số cổ phiếu     = Tiền rủi ro / (Giá vào − Giá cắt lỗ)

Quy tắc: rủi ro 1–2%/lệnh; cắt lỗ 7–8% (O'Neil); R:R = Reward:Risk ≥ 2:1.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RiskPlan:
    entry: float
    stop: float
    target: float | None
    risk_pct: float                 # % vốn rủi ro/lệnh
    capital: float
    risk_money: float               # Tiền rủi ro (VND)
    stop_pct: float                 # % cắt lỗ so giá vào
    target_pct: float | None        # % mục tiêu so giá vào
    rr_ratio: float                 # Reward:Risk
    deployable: float               # Vốn giải ngân
    shares: float                   # Số cổ phiếu
    deployable_pct: float           # Vốn giải ngân / Vốn
    verdict: str                    # ĐẠT / CẢNH BÁO
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "entry": round(self.entry, 2), "stop": round(self.stop, 2),
            "target": round(self.target, 2) if self.target else None,
            "risk_pct": self.risk_pct, "capital": self.capital,
            "risk_money": round(self.risk_money), "stop_pct": round(self.stop_pct * 100, 2),
            "target_pct": round(self.target_pct * 100, 2) if self.target_pct else None,
            "rr_ratio": round(self.rr_ratio, 2), "deployable": round(self.deployable),
            "shares": round(self.shares), "deployable_pct": round(self.deployable_pct * 100, 1),
            "verdict": self.verdict, "warnings": self.warnings,
        }


def suggest_stop(entry: float, atr_value: float | None,
                 method: str = "atr", pct: float = 0.08) -> float:
    """Gợi ý giá cắt lỗ.

    method='atr'   → entry − 2×ATR (swing, bao gồm nhiễu).
    method='oneil' → entry × (1 − pct), mặc định 8% (O'Neil: 7–8%).
    """
    if method == "atr" and atr_value and atr_value > 0:
        return entry - 2.0 * atr_value
    return entry * (1.0 - pct)


def position_size(capital: float, risk_pct: float, entry: float,
                  stop: float, target: float | None = None) -> RiskPlan:
    """Tính kế hoạch rủi ro theo công thức đã sửa ở file 06."""
    warnings: list[str] = []
    if stop >= entry:
        raise ValueError(f"Giá cắt lỗ ({stop}) phải thấp hơn giá vào ({entry}) cho lệnh LONG.")
    if risk_pct <= 0 or risk_pct > 0.05:
        warnings.append(f"Rủi ro {risk_pct*100:.1f}%/lệnh nằm ngoài khuyến nghị 1–2% (cần <5%).")

    risk_money = capital * risk_pct
    stop_pct = (entry - stop) / entry
    risk_per_share = entry - stop
    shares = risk_money / risk_per_share
    deployable = shares * entry
    deployable_pct = deployable / capital

    if deployable_pct > 1.0:
        warnings.append(f"Vốn giải ngân {deployable_pct*100:.0f}% vốn > 100%: cắt lỗ quá hẹp "
                        f"hoặc rủi ro quá cao cho vốn này.")
    if stop_pct > 0.10:
        warnings.append(f"Cắt lỗ {stop_pct*100:.1f}% > 8% khuyến nghị O'Neil — có thể rộng quá.")

    target_pct = None
    rr = None
    if target and target > entry:
        reward = target - entry
        rr = reward / risk_per_share
        target_pct = (target - entry) / entry
        if rr < 2.0:
            warnings.append(f"R:R = {rr:.2f}:1 < 2:1 — phần thưởng chưa bù được rủi ro.")
    else:
        rr = 0.0

    verdict = "ĐẠT" if (rr is None or rr >= 2.0) and deployable_pct <= 1.0 else "CẢNH BÁO"
    return RiskPlan(
        entry=entry, stop=stop, target=target, risk_pct=risk_pct, capital=capital,
        risk_money=risk_money, stop_pct=stop_pct, target_pct=target_pct, rr_ratio=rr or 0.0,
        deployable=deployable, shares=shares, deployable_pct=deployable_pct,
        verdict=verdict, warnings=warnings,
    )


def suggest_target(entry: float, stop: float, rr: float = 2.0) -> float:
    """Mục tiêu tối thiểu cho R:R yêu cầu (target = entry + rr × (entry − stop))."""
    return entry + rr * (entry - stop)


def atr_pct(df, n: int = 14) -> float | None:
    """ATR tính theo % giá (vd 2.02 nghĩa là 2.02%) — gợi ý stop tự nhiên (file 06)."""
    if df is None or df.empty or len(df) < n:
        return None
    from .indicators import atr
    a = atr(df, n)
    if a.empty:
        return None
    last = a.iloc[-1]
    price = df["close"].iloc[-1]
    return round(float(last / price * 100), 2) if price else None
