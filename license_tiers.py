"""
라이선스 등급별 기능 및 코인 접근 권한
"""

import os
import json
from typing import List, Dict
from dataclasses import dataclass, asdict


@dataclass
class LicenseTier:
    """라이선스 등급 정의"""
    name: str
    license_fee: float        # 라이선스 1회 구매 비용
    price_monthly: float      # 월 구독료 (라이선스 구매 후)
    price_yearly: float       # 연간 구독료 (할인)
    coins: List[str]
    exchanges: List[str]
    max_positions: int
    features: List[str]
    description: str


# 라이선스 등급 정의 (1회 구매 + 월 구독)
# 라이선스 = 프로그램 사용권한 (1회, 1PC 고정)
# 월 구독 = 서버 유지비 (고정)
# ⚠️ 라이선스는 PC 하드웨어에 고정 - 중복 실행 불가
LICENSE_TIERS = {
    "free": LicenseTier(
        name="Free",
        license_fee=0,
        price_monthly=0,
        price_yearly=0,
        coins=["BTCUSDT"],
        exchanges=["*"],      # 모든 거래소 중 선택 가능
        max_positions=1,      # 라이브 매매 1개 허용
        features=[
            "BTC 1종 라이브 매매",
            "모든 거래소 지원",
            "7일 제한",
        ],
        description="7일 무료 체험 (BTC)"
    ),
    
    "basic": LicenseTier(
        name="Basic",
        license_fee=500,
        price_monthly=9,
        price_yearly=90,
        coins=["BTCUSDT"],  # 1코인
        exchanges=["bybit", "binance"],  # 2거래소
        max_positions=1,
        features=[
            "BTC 1종 라이브 매매",
            "기본 전략",
            "이메일 지원",
        ],
        description="BTC 전용 - 입문자용"
    ),
    
    "standard": LicenseTier(
        name="Standard",
        license_fee=1500,
        price_monthly=9,
        price_yearly=90,
        coins=["BTCUSDT", "ETHUSDT"],  # 2코인
        exchanges=["bybit", "binance", "okx"],  # 3거래소
        max_positions=2,
        features=[
            "BTC, ETH 매매",
            "고급 전략",
            "텔레그램 알림",
            "우선 지원",
        ],
        description="BTC+ETH - 일반 사용자용"
    ),
    
    "premium": LicenseTier(
        name="Premium",
        license_fee=3000,
        price_monthly=9,
        price_yearly=90,
        coins=[
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
            "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT",
            "LINKUSDT", "MATICUSDT"  # 바이낸스 기준 10코인
        ],
        exchanges=["bybit", "binance", "okx", "bitget", "upbit", "bithumb"],  # 6거래소
        max_positions=10,
        features=[
            "바이낸스 TOP 10 코인",
            "모든 전략",
            "텔레그램 알림",
            "VIP 지원",
            "자동 포지션 사이징",
        ],
        description="바이낸스 TOP 10 - 전문 트레이더용"
    )
}


def get_tier(tier_name: str) -> LicenseTier:
    """등급 정보 반환"""
    return LICENSE_TIERS.get(tier_name.lower(), LICENSE_TIERS["basic"])


def get_available_coins(tier_name: str) -> List[str]:
    """등급별 사용 가능 코인 목록"""
    tier = get_tier(tier_name)
    if "*" in tier.coins:
        return ["*"]  # 무제한
    return tier.coins


def get_available_exchanges(tier_name: str) -> List[str]:
    """등급별 사용 가능 거래소 목록"""
    tier = get_tier(tier_name)
    if "*" in tier.exchanges:
        return ["*"]
    return tier.exchanges


def is_coin_allowed(tier_name: str, symbol: str) -> bool:
    """해당 등급에서 코인 사용 가능 여부"""
    tier = get_tier(tier_name)
    
    if "*" in tier.coins:
        return True
    
    # 심볼 정규화
    symbol_upper = symbol.upper().replace("-", "/")
    
    for allowed in tier.coins:
        if allowed.upper() in symbol_upper or symbol_upper in allowed.upper():
            return True
    
    return False


def is_exchange_allowed(tier_name: str, exchange: str) -> bool:
    """해당 등급에서 거래소 사용 가능 여부"""
    tier = get_tier(tier_name)
    
    if "*" in tier.exchanges:
        return True
    
    return exchange.lower() in [e.lower() for e in tier.exchanges]


def get_tier_comparison() -> str:
    """등급 비교표 생성"""
    text = "📊 라이선스 등급 비교\n"
    text += "━" * 50 + "\n\n"
    
    for tier_key, tier in LICENSE_TIERS.items():
        text += f"💎 {tier.name} (라이선스: ${tier.license_fee}, 월: ${tier.price_monthly})\n"
        text += f"   {tier.description}\n"
        text += f"   📈 코인: {len(tier.coins) if '*' not in tier.coins else '무제한'}개\n"
        text += f"   🏦 거래소: {', '.join(tier.exchanges) if '*' not in tier.exchanges else '전체'}\n"
        text += f"   📊 동시 포지션: {tier.max_positions}개\n"
        text += "\n"
    
    return text


# 사용자 라이선스 등급 확인
def get_user_tier() -> str:
    """현재 사용자 라이선스 등급"""
    try:
        from license_manager import get_license_manager
        lm = get_license_manager()
        
        # 라이선스 정보에서 등급 확인
        result = lm.check()
        
        if result.get('valid', False) or result.get('expired', False):
            # 만료되었어도 등급 정보는 반환 (만료 처리는 별도)
            return result.get('tier', 'free').lower()
        else:
            return "free"
    except Exception as e:
        print(f"Tier check error: {e}")
        return "free"


# 테스트
if __name__ == "__main__":
    print(get_tier_comparison())
    
    print("\n=== 등급별 코인 확인 테스트 ===")
    for tier in ["basic", "standard", "premium", "unlimited"]:
        print(f"\n{tier}:")
        for coin in ["BTCUSDT", "ETHUSDT", "XRPUSDT", "DOGEUSDT"]:
            allowed = "✅" if is_coin_allowed(tier, coin) else "❌"
            print(f"  {coin}: {allowed}")
