"""
가상자산 결제 시스템
- USDT/BTC/ETH 입금 주소 표시
- 입금 확인 (수동/자동)
- 라이선스 활성화 연동
"""

import os
import json
from typing import Dict, Optional
from datetime import datetime

# 설정 파일 경로 (core/data 쪽에 저장하거나, user settings에 저장하는 것이 좋음)
# 여기서는 원본 유지하되 경로만 적절히 수정
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user', 'global', 'settings', 'payment_config.json')


# 기본 설정
DEFAULT_CONFIG = {
    'license_price_usd': 100.0,  # 평생 라이선스 가격
    'wallets': {
        "USDT_TRC20": {
            "address": "TPEzvE85juFiQLhmBACbFNJgUWTtv7TCk3",
            "memo": "",
            'network': 'Tron (TRC-20)',
            'min_confirmations': 1
        },
        'BTC': {
            'address': '',  # 관리자가 설정
            'network': 'Bitcoin',
            'min_confirmations': 3
        },
        'ETH': {
            'address': '',  # 관리자가 설정
            'network': 'Ethereum',
            'min_confirmations': 12
        }
    }
}


class CryptoPayment:
    """가상자산 결제 관리"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """설정 로드"""
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                self._save_config(DEFAULT_CONFIG)
                return DEFAULT_CONFIG
        except Exception as e:
            logging.error(f"Failed to load payment configuration from {CONFIG_PATH}: {e}")
            return DEFAULT_CONFIG
    
    def _save_config(self, config: Dict):
        """설정 저장"""
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to save payment configuration to {CONFIG_PATH}: {e}")
    
    def get_price_usd(self) -> float:
        """라이선스 가격 (USD)"""
        return self.config.get('license_price_usd', 100.0)
    
    def get_wallets(self) -> Dict:
        """지갑 주소 목록"""
        return self.config.get('wallets', {})
    
    def set_wallet(self, crypto_type: str, address: str):
        """지갑 주소 설정 (관리자용)"""
        if crypto_type in self.config['wallets']:
            self.config['wallets'][crypto_type]['address'] = address
            self._save_config(self.config)
    
    def get_payment_info(self, user_id: int, email: str) -> Dict:
        """
        사용자별 결제 정보 생성
        - 고유 메모/태그 생성 (입금 식별용)
        """
        # 사용자 고유 태그 (user_id 기반)
        user_tag = f"USER{user_id:06d}"
        
        payment_options = []
        wallets = self.get_wallets()
        price_usd = self.get_price_usd()
        
        for crypto, info in wallets.items():
            if info.get('address'):
                payment_options.append({
                    'crypto': crypto,
                    'address': info['address'],
                    'network': info['network'],
                    'amount_usd': price_usd,
                    'memo': user_tag,  # 입금 시 메모에 입력
                    'instructions': self._get_instructions(crypto, info)
                })
        
        return {
            'user_id': user_id,
            'email': email,
            'price_usd': price_usd,
            'user_tag': user_tag,
            'payment_options': payment_options,
            'created_at': datetime.now().isoformat()
        }
    
    def _get_instructions(self, crypto: str, info: Dict) -> str:
        """결제 안내 메시지"""
        return f"""
📌 {crypto} 결제 방법:

1. 아래 주소로 ${self.get_price_usd()} 상당의 {crypto}를 전송하세요
2. 네트워크: {info['network']}
3. 주소: {info['address']}
4. ⚠️ 반드시 메모(Memo/Tag)에 USER ID를 입력하세요!

입금 확인까지 최대 30분이 소요될 수 있습니다.
문의: [관리자 이메일]
"""
    
    def verify_payment_manual(self, user_id: int, tx_hash: str, 
                               crypto_type: str) -> Dict:
        """
        수동 결제 확인 요청
        - 관리자가 확인 후 활성화
        """
        try:
            from core.license_manager import get_license_manager
            
            lm = get_license_manager()
            payment_id = lm.record_payment(
                user_id=user_id,
                amount_usd=self.get_price_usd(),
                crypto_type=crypto_type,
                tx_hash=tx_hash
            )
            
            return {
                'payment_id': payment_id,
                'status': 'pending',
                'message': '결제 확인 요청이 접수되었습니다. 관리자 확인 후 활성화됩니다.'
            }
        except ImportError:
             # 라이선스 매니저가 없을 경우 (테스트 등)
             return {
                'payment_id': 0,
                'status': 'error',
                'message': '매니저 모듈 없음'
            }

    
    def admin_confirm_payment(self, payment_id: int) -> bool:
        """관리자 결제 확인 및 라이선스 활성화"""
        try:
            from core.license_manager import get_license_manager
            
            lm = get_license_manager()
            return lm.confirm_payment(payment_id)
        except:
            return False
        
    def check_transaction(self, tx_hash: str, crypto_type: str, my_address: str, expected_memo: str = None) -> Dict:
        """
        블록체인 거래 조회 (공개 API 활용)
        - 실제로는 BlockCypher, Etherscan 등의 API를 사용해야 합니다.
        - 여기서는 데모용 시뮬레이션 로직을 포함합니다.
        """
        import time
        import random
        
        # 1. 시뮬레이션 (데모용)
        # 특정 접두사로 시작하면 테스트 성공으로 간주
        if tx_hash.startswith("TEST_SUCCESS_") or tx_hash == "demo_tx_12345":
            return {
                'valid': True,
                'amount': self.get_price_usd(),
                'sender': '0xTestSender...',
                'confirmations': 5
            }
            
        if tx_hash.startswith("TEST_FAIL_"):
             return {'valid': False, 'reason': 'Transaction failed or not found'}
             
        # 여기서는 "유효한 해시 길이"라면 "확인 요청 접수됨" 상태로 넘기는게 현실적.
        if len(tx_hash) > 10:
             # 자동 확인 로직이 없으므로 일단 승인 처리 (데모 모드)
             return {
                'valid': True,
                'amount': 0, # 금액 정보 모름
                'reason': 'Auto-verified by client (Demonstration)'
            }
            
        return {'valid': False, 'reason': '유효하지 않은 TX Hash입니다.'}


# QR 코드 생성 (선택)
def generate_payment_qr(address: str, amount: float = None, 
                        crypto: str = 'BTC') -> Optional[str]:
    """결제용 QR 코드 생성 (PNG 파일 경로 반환)"""
    try:
        import qrcode
        
        # 표준 URI 형식
        if crypto == 'BTC':
            uri = f"bitcoin:{address}"
        elif crypto.startswith('ETH'):
            uri = f"ethereum:{address}"
        else:
            uri = address
        
        if amount:
            uri += f"?amount={amount}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 저장
        qr_path = os.path.join(os.path.dirname(__file__), 'data', 'payment_qr.png')
        img.save(qr_path)
        
        return qr_path
    except ImportError:
        # print("QR 코드 생성을 위해 'pip install qrcode[pil]' 설치 필요")
        return None


# 전역 인스턴스
_crypto_payment = None

def get_crypto_payment() -> CryptoPayment:
    """CryptoPayment 싱글톤"""
    global _crypto_payment
    if _crypto_payment is None:
        _crypto_payment = CryptoPayment()
    return _crypto_payment
