"""
에러 해결 가이드
- 자주 발생하는 에러와 해결책
- 에러 코드별 대응 방법
"""

# 에러 코드별 해결 가이드
ERROR_SOLUTIONS = {
    # 연결 오류
    "CONNECTION_ERROR": {
        "title": "연결 오류",
        "causes": [
            "인터넷 연결 끊김",
            "거래소 서버 점검",
            "API 키 만료",
        ],
        "solutions": [
            "인터넷 연결 상태 확인",
            "거래소 공지사항 확인 (서버 점검 여부)",
            "API 키 재발급 및 재입력",
            "5분 후 재시도",
        ],
        "auto_recovery": True
    },
    
    "INVALID_API_KEY": {
        "title": "API 키 오류",
        "causes": [
            "잘못된 API 키 입력",
            "API 키 권한 부족",
            "API 키 삭제됨",
        ],
        "solutions": [
            "API 키 재확인 (복사 시 공백 주의)",
            "거래소에서 권한 설정 확인 (거래 권한 필요)",
            "API 키 재발급",
        ],
        "auto_recovery": False
    },
    
    "IP_NOT_WHITELISTED": {
        "title": "IP 화이트리스트 오류",
        "causes": [
            "IP 주소가 등록되지 않음",
            "IP 주소가 변경됨 (동적 IP)",
        ],
        "solutions": [
            "거래소에서 현재 IP를 화이트리스트에 추가",
            "고정 IP 서비스 사용 권장",
            "VPS 서비스 이용 고려",
        ],
        "note": "⚠️ 업비트는 고정 IP가 필수입니다!",
        "auto_recovery": False
    },
    
    "INSUFFICIENT_BALANCE": {
        "title": "잔고 부족",
        "causes": [
            "계좌 잔고 부족",
            "마진 부족 (선물)",
        ],
        "solutions": [
            "거래소에 자금 입금",
            "매매 금액 설정 낮추기",
            "레버리지 조정",
        ],
        "auto_recovery": False
    },
    
    "RATE_LIMIT": {
        "title": "요청 제한 초과",
        "causes": [
            "API 요청이 너무 많음",
            "다른 봇/프로그램과 동시 사용",
        ],
        "solutions": [
            "잠시 대기 후 자동 재시도됨",
            "다른 프로그램에서 같은 API 사용 중인지 확인",
        ],
        "auto_recovery": True
    },
    
    "ORDER_FAILED": {
        "title": "주문 실패",
        "causes": [
            "주문량이 최소 주문량 미달",
            "가격 변동이 심함",
            "시장 주문 불가 상태",
        ],
        "solutions": [
            "매매 금액 늘리기",
            "잠시 후 재시도",
            "거래소 상태 확인",
        ],
        "auto_recovery": True
    },
    
    "POSITION_ALREADY_EXISTS": {
        "title": "포지션 중복",
        "causes": [
            "이미 같은 심볼에 포지션 보유 중",
        ],
        "solutions": [
            "기존 포지션 청산 후 진입",
            "설정에서 최대 포지션 수 조정",
        ],
        "auto_recovery": False
    },
    
    "NETWORK_TIMEOUT": {
        "title": "네트워크 타임아웃",
        "causes": [
            "인터넷 속도 느림",
            "거래소 응답 지연",
        ],
        "solutions": [
            "인터넷 연결 확인",
            "다른 네트워크 시도 (WiFi ↔ 모바일 데이터)",
            "자동 재연결 대기",
        ],
        "auto_recovery": True
    },
}


def get_error_solution(error_code: str) -> dict:
    """에러 코드에 대한 해결책 반환"""
    return ERROR_SOLUTIONS.get(error_code, {
        "title": "알 수 없는 오류",
        "causes": ["원인 파악 불가"],
        "solutions": [
            "프로그램 재시작",
            "설정 재확인",
            "고객 지원 문의",
        ],
        "auto_recovery": False
    })


def diagnose_error(error_message: str) -> str:
    """에러 메시지에서 에러 코드 추론"""
    error_message = error_message.lower()
    
    if "api" in error_message and ("key" in error_message or "invalid" in error_message):
        return "INVALID_API_KEY"
    elif "ip" in error_message and ("whitelist" in error_message or "allowed" in error_message):
        return "IP_NOT_WHITELISTED"
    elif "balance" in error_message or "insufficient" in error_message:
        return "INSUFFICIENT_BALANCE"
    elif "rate" in error_message and "limit" in error_message:
        return "RATE_LIMIT"
    elif "timeout" in error_message:
        return "NETWORK_TIMEOUT"
    elif "connection" in error_message or "connect" in error_message:
        return "CONNECTION_ERROR"
    elif "order" in error_message and "fail" in error_message:
        return "ORDER_FAILED"
    elif "position" in error_message and "exist" in error_message:
        return "POSITION_ALREADY_EXISTS"
    
    return "UNKNOWN_ERROR"


def format_error_guide(error_code: str) -> str:
    """에러 가이드 포맷팅"""
    solution = get_error_solution(error_code)
    
    text = f"""
❌ {solution.get('title', '오류')}

📌 원인:
"""
    for cause in solution.get('causes', []):
        text += f"  • {cause}\n"
    
    text += "\n✅ 해결 방법:\n"
    for sol in solution.get('solutions', []):
        text += f"  1. {sol}\n"
    
    if solution.get('note'):
        text += f"\n{solution['note']}"
    
    if solution.get('auto_recovery'):
        text += "\n\n🔄 자동 재시도됩니다."
    
    return text


# 테스트
if __name__ == "__main__":
    print("=== 에러 진단 테스트 ===\n")
    
    test_errors = [
        "Error: Invalid API key",
        "IP address not in whitelist",
        "Insufficient balance",
        "Rate limit exceeded",
    ]
    
    for error in test_errors:
        code = diagnose_error(error)
        print(f"에러: {error}")
        print(f"코드: {code}")
        print(format_error_guide(code))
        print("-" * 50)
