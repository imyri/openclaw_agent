from datetime import datetime, timedelta, timezone

import pandas as pd

from strategy.market_structure import QuantitativeEngine


def test_quant_engine_emits_stop_reference_for_bullish_setup():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for idx in range(12):
        ts = start + timedelta(minutes=5 * idx)
        if idx == 5:
            open_, high, low, close = 100, 110, 99, 101
        elif idx == 9:
            open_, high, low, close = 102, 104, 101, 103
        elif idx == 10:
            open_, high, low, close = 104, 106, 103, 105
        elif idx == 11:
            # Bullish FVG: low (111) > high at idx 9 (104), and strong bullish body.
            open_, high, low, close = 111.2, 120, 111, 119
        else:
            open_, high, low, close = 100 + idx * 0.3, 101 + idx * 0.3, 99 + idx * 0.3, 100 + idx * 0.3
        rows.append([ts, open_, high, low, close, 1_000])

    df = pd.DataFrame(rows, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"]).set_index("timestamp")
    state = QuantitativeEngine(df).run_execution_checklist()

    assert state.valid_poi_found is True
    assert state.setup_type == "BULLISH_MSS_WITH_DISPLACEMENT"
    assert state.stop_reference is not None
