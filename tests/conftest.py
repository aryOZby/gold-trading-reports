from __future__ import annotations

from pathlib import Path

import pytest

CLOSED_HEADER = (
    "deal,position,comment,group,side,lot,placed_israel,opened_israel,closed_israel,"
    "open_price,close_price,initial_sl,initial_tp,sl_at_close,profit,commission,swap,reason"
)
OPEN_HEADER = "kind,ticket,comment,group,side,lot,placed_israel,opened_israel,open_price,sl,tp,profit"
UNFILLED_HEADER = "deleted_israel,placed_israel,age_hours,comment,group,ticket,type,entry,sl,tp,lot,reason"

# G2 N1 — strategy 1 SELL: TP4 hit, TP5/TP6 stopped at entry after breakeven -> Profit
# G2 N2 — strategy 1 SELL: all three stopped at the signal SL -> Loss
# G2 N3 — closed by the EA at the Friday close
# G4 N1 — strategy 3 limits deleted because TP1 came first -> Not executed
# G4 N2 — strategy 3 limit still pending -> Open
# G1 N1 — placed in October: belongs to the October report
# GT1-18857-TP4 — an older trade without the S|G|N|tp comment
CLOSED_ROWS = [
    "101,9001,S1|G2|N1|tp4,G2,SELL,0.01,2026.11.03 10:00:00,2026.11.03 10:00:01,2026.11.03 11:00:00,4315.00,4300.00,4327.00,4300.00,4327.00,15.00,-0.07,0.00,TP",
    "102,9002,S1|G2|N1|tp5,G2,SELL,0.01,2026.11.03 10:00:00,2026.11.03 10:00:01,2026.11.03 12:00:00,4315.00,4315.05,4327.00,4295.00,4315.00,-0.05,-0.07,0.00,SL",
    "103,9003,S1|G2|N1|tp6,G2,SELL,0.01,2026.11.03 10:00:00,2026.11.03 10:00:01,2026.11.03 12:00:00,4315.00,4315.05,4327.00,4285.00,4315.00,-0.05,-0.07,0.00,SL",
    "104,9004,S1|G2|N2|tp4,G2,SELL,0.01,2026.11.04 09:00:00,2026.11.04 09:00:01,2026.11.04 09:30:00,4200.00,4212.00,4212.00,4190.00,4212.00,-12.00,-0.07,0.00,SL",
    "105,9005,S1|G2|N2|tp5,G2,SELL,0.01,2026.11.04 09:00:00,2026.11.04 09:00:01,2026.11.04 09:30:00,4200.00,4212.00,4212.00,4185.00,4212.00,-12.00,-0.07,0.00,SL",
    "106,9006,S1|G2|N2|tp6,G2,SELL,0.01,2026.11.04 09:00:00,2026.11.04 09:00:01,2026.11.04 09:30:00,4200.00,4212.00,4212.00,4180.00,4212.00,-12.00,-0.07,0.00,SL",
    "107,9007,S2|G2|N3|tp1,G2,BUY,0.02,2026.11.06 20:00:00,2026.11.06 20:00:01,2026.11.06 23:30:05,4100.00,4104.00,4090.00,4120.00,4090.00,8.00,-0.14,-0.30,EXPERT",
    "108,9008,S1|G1|N1|tp4,G1,BUY,0.01,2026.10.31 22:00:00,2026.10.31 22:00:01,2026.11.01 09:00:00,4000.00,4010.00,3990.00,4010.00,3990.00,10.00,-0.07,0.00,TP",
    "109,9009,GT1-18857-TP4,G1,SELL,0.01,2026.11.10 10:00:00,2026.11.10 10:00:01,2026.11.10 10:56:37,4087.55,4080.00,4100.00,4080.00,4100.00,7.55,-0.07,0.00,TP",
]
OPEN_ROWS = [
    "order,9101,S3|G4|N2|tp4,G4,SELL,0.01,2026.11.20 08:00:00,,4083.00,4095.00,4060.00,0",
]
UNFILLED_ROWS = [
    "2026.11.12 14:00:00,2026.11.12 09:00:00,5.0,S3|G4|N1|tp4,G4,9201,SELL_LIMIT,4083.00,4095.00,4060.00,0.01,tp1_before_fill",
    "2026.11.12 14:00:00,2026.11.12 09:00:00,5.0,S3|G4|N1|tp5,G4,9202,SELL_LIMIT,4083.00,4095.00,4050.00,0.01,tp1_before_fill",
]


@pytest.fixture
def journal_dir(tmp_path: Path) -> Path:
    (tmp_path / "closed.csv").write_text("\n".join([CLOSED_HEADER, *CLOSED_ROWS]) + "\n", encoding="ascii")
    (tmp_path / "open.csv").write_text("\n".join([OPEN_HEADER, *OPEN_ROWS]) + "\n", encoding="ascii")
    (tmp_path / "unfilled.csv").write_text("\n".join([UNFILLED_HEADER, *UNFILLED_ROWS]) + "\n", encoding="ascii")
    return tmp_path
