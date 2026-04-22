from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class OverheadConfig(Base):
    __tablename__ = "overhead_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Default")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    # Labor burden (applied to raw labor cost)
    fica_rate: Mapped[float] = mapped_column(Float, default=0.0765)      # 7.65%
    futa_rate: Mapped[float] = mapped_column(Float, default=0.006)       # 0.6%
    suta_rate: Mapped[float] = mapped_column(Float, default=0.027)       # 2.7%
    workers_comp_rate: Mapped[float] = mapped_column(Float, default=0.12) # 12%
    general_liability_rate: Mapped[float] = mapped_column(Float, default=0.015)
    health_insurance_rate: Mapped[float] = mapped_column(Float, default=0.08)
    vacation_rate: Mapped[float] = mapped_column(Float, default=0.05)
    total_burden_rate: Mapped[float] = mapped_column(Float, default=0.35)  # computed sum

    # General overhead (% of direct costs)
    general_overhead_rate: Mapped[float] = mapped_column(Float, default=0.10)  # 10%
    small_tools_rate: Mapped[float] = mapped_column(Float, default=0.02)

    # Markup
    material_markup: Mapped[float] = mapped_column(Float, default=0.10)   # 10%
    profit_margin: Mapped[float] = mapped_column(Float, default=0.08)     # 8%
    contingency_rate: Mapped[float] = mapped_column(Float, default=0.03)  # 3%
    bond_rate: Mapped[float] = mapped_column(Float, default=0.015)        # 1.5%
    permit_rate: Mapped[float] = mapped_column(Float, default=0.01)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
