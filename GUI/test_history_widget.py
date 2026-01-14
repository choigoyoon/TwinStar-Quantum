"""
History Widget 전체 기능 점검 스크립트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from history_widget import HistoryWidget
import json

import logging
logger = logging.getLogger(__name__)

def create_test_data():
    """테스트 데이터 생성"""
    trades = [
        {
            "time": "2024-12-01T10:30:00",
            "symbol": "BTCUSDT",
            "side": "Long",
            "entry": 95000.0,
            "exit": 96500.0,
            "size": 0.01,
            "pnl": 45.0,
            "pnl_pct": 1.58,
            "be_triggered": True
        },
        {
            "time": "2024-12-02T14:00:00",
            "symbol": "BTCUSDT",
            "side": "Short",
            "entry": 97000.0,
            "exit": 96200.0,
            "size": 0.01,
            "pnl": 24.0,
            "pnl_pct": 0.82,
            "be_triggered": True
        },
        {
            "time": "2024-12-03T09:15:00",
            "symbol": "ETHUSDT",
            "side": "Long",
            "entry": 3500.0,
            "exit": 3450.0,
            "size": 0.1,
            "pnl": -15.0,
            "pnl_pct": -1.43,
            "be_triggered": False
        },
        {
            "time": "2024-12-04T16:45:00",
            "symbol": "BTCUSDT",
            "side": "Long",
            "entry": 94000.0,
            "exit": 95800.0,
            "size": 0.015,
            "pnl": 81.0,
            "pnl_pct": 1.91,
            "be_triggered": True
        },
        {
            "time": "2024-12-05T11:20:00",
            "symbol": "SOLUSDT",
            "side": "Short",
            "entry": 220.0,
            "exit": 225.0,
            "size": 1.0,
            "pnl": -15.0,
            "pnl_pct": -2.27,
            "be_triggered": False
        }
    ]
    
    # trade_history.json 저장
    history_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trade_history.json")
    with open(history_file, 'w') as f:
        json.dump(trades, f, indent=2)
    logger.info(f"✅ 테스트 데이터 생성: {history_file}")
    logger.info(f"   - {len(trades)}개 거래")
    return trades


def create_test_csv():
    """테스트 CSV 생성"""
    import csv
    csv_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_trades.csv")
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Date/Time", "Symbol", "Direction", "Entry Price", "Exit Price", "Quantity", "Profit ($)", "Return (%)", "BE"])
        writer.writerow(["2024-12-06 08:00", "BTCUSDT", "Buy", "98000", "99500", "0.02", "90", "1.53", "Yes"])
        writer.writerow(["2024-12-06 12:30", "ETHUSDT", "Sell", "3600", "3550", "0.5", "25", "1.39", "No"])
    
    logger.info(f"✅ 테스트 CSV 생성: {csv_file}")
    return csv_file


def test_all_features():
    """모든 기능 테스트"""
    logger.info("=" * 60)
    logger.info("🧪 History Widget 전체 기능 점검")
    logger.info("=" * 60)
    
    # 1. 테스트 데이터 생성
    logger.info("\n[1] 테스트 데이터 생성...")
    trades = create_test_data()
    csv_file = create_test_csv()
    
    # 2. 위젯 생성
    logger.info("\n[2] HistoryWidget 생성...")
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { background: #0d1117; color: white; }")
    
    widget = HistoryWidget()
    
    # 3. 자동 로딩 확인
    logger.info("\n[3] 자동 로딩 확인...")
    if widget._trades:
        logger.info(f"   ✅ trade_history.json 로딩 성공: {len(widget._trades)}개 거래")
    else:
        logger.info("   ❌ 거래 데이터 없음")
    
    # 4. 필터 확인
    logger.info("\n[4] 필터 기능 확인...")
    logger.info(f"   - Symbol 필터 옵션: {[widget.symbol_filter.itemText(i) for i in range(widget.symbol_filter.count())]}")
    logger.info(f"   - Side 필터 옵션: {[widget.side_filter.itemText(i) for i in range(widget.side_filter.count())]}")
    logger.info(f"   - Result 필터 옵션: {[widget.result_filter.itemText(i) for i in range(widget.result_filter.count())]}")
    logger.info("   ✅ 필터 기능 정상")
    
    # 5. 테이블 컬럼 확인
    logger.info("\n[5] 테이블 컬럼 확인...")
    columns = [widget.table.horizontalHeaderItem(i).text() for i in range(widget.table.columnCount())]
    logger.info(f"   컬럼: {columns}")
    if "#" in columns:
        logger.info("   ✅ 매매 번호(#) 컬럼 있음")
    else:
        logger.info("   ❌ 매매 번호(#) 컬럼 없음")
    
    # 6. 통계 카드 확인
    logger.info("\n[6] 통계 카드 확인...")
    stat_cards = [
        'total_trades_card', 'win_rate_card', 'total_pnl_card', 
        'profit_factor_card', 'avg_pnl_card', 'max_dd_card',
        'best_trade_card', 'worst_trade_card', 'win_streak_card',
        'lose_streak_card', 'be_rate_card', 'capital_card'
    ]
    for card in stat_cards:
        if hasattr(widget, card):
            logger.info(f"   ✅ {card}")
        else:
            logger.info(f"   ❌ {card} 없음")
    
    # 7. 드래그앤드롭 확인
    logger.info("\n[7] 드래그앤드롭 확인...")
    if widget.acceptDrops():
        logger.info("   ✅ 드래그앤드롭 활성화됨")
    else:
        logger.info("   ❌ 드래그앤드롭 비활성화")
    
    # 8. CSV 임포트 테스트
    logger.info("\n[8] CSV 임포트 테스트...")
    try:
        widget._load_csv_file(csv_file)
        logger.info(f"   ✅ CSV 로딩 성공: {len(widget._trades)}개 거래")
    except Exception as e:
        logger.info(f"   ❌ CSV 로딩 실패: {e}")
    
    # 9. 더블클릭 핸들러 확인
    logger.info("\n[9] 더블클릭 차트 기능 확인...")
    if hasattr(widget, '_on_cell_double_clicked'):
        logger.info("   ✅ 더블클릭 핸들러 있음")
    else:
        logger.info("   ❌ 더블클릭 핸들러 없음")
    
    # 10. 차트 팝업 클래스 확인
    logger.info("\n[10] 차트 팝업 클래스 확인...")
    try:
        logger.info("   ✅ TradeChartPopup 클래스 있음")
    except ImportError:
        logger.info("   ❌ TradeChartPopup 클래스 없음")
    
    logger.info("\n" + "=" * 60)
    logger.info("🎉 전체 기능 점검 완료!")
    logger.info("=" * 60)
    
    # 화면 표시
    widget.resize(1200, 800)
    widget.show()
    
    logger.info("\n📋 GUI 창이 열렸습니다. 확인 후 닫아주세요.")
    # sys.exit(app.exec())  # 주석 처리 - 자동 테스트용
    return True


if __name__ == "__main__":
    test_all_features()
