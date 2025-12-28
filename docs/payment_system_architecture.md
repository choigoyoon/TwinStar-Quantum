# TwinStar Quantum 결제 시스템 아키텍처

**작성일:** 2025-12-19  
**버전:** v1.0.0

---

## 1. 전체 흐름

```
[EXE - Python]                    [웹 - PHP]                     [DB]
      │                                │                            │
      ├── 로그인 요청 ──────────────────►├── 인증 확인 ──────────────►│
      │◄─────────────── 결과 반환 ──────┤◄─────────────── 조회 ──────┤
      │                                │                            │
      ├── 세션 생성 요청 ───────────────►├── 세션 저장 ──────────────►│
      │◄─────────────── session_id ────┤                            │
      │                                │                            │
      ├── 브라우저 열기 ───────────────►├── 결제 페이지 표시          │
      │   (sid=xxx)                    │                            │
      │                                ├── 등급 선택                 │
      │                                ├── 결제 처리                 │
      │                                ├── DB 업데이트 ─────────────►│
      │                                │                            │
      ├── 라이센스 확인 ────────────────►├── 등급 조회 ──────────────►│
      │◄─────────────── 새 등급 반환 ───┤◄─────────────── 결과 ──────┤
```

---

## 2. 역할 분담

### 2.1 Python (EXE) 담당

| 기능 | 파일 | 설명 |
|------|------|------|
| 로그인/인증 | `pc_license_dialog.py` | API 호출로 인증 |
| 세션 생성 | `payment_dialog.py` | 업그레이드 세션 요청 |
| 브라우저 열기 | `payment_dialog.py` | webbrowser.open() |
| 등급 제한 체크 | `unified_bot.py` | 심볼/거래소 수 제한 |
| 등급 표시 | `staru_main.py` | 상단 바 표시 |

### 2.2 PHP (웹) 담당

| 기능 | 파일 | 설명 |
|------|------|------|
| 인증 처리 | `license_api.php` | 이메일+HW_ID 확인 |
| 세션 관리 | `upgrade.php` | session_id 생성/검증 |
| 결제 처리 | `payment.php` | 결제 게이트웨이 연동 |
| DB 업데이트 | `update_tier.php` | 등급/만료일 변경 |

### 2.3 DB 담당

| 테이블 | 컬럼 | 설명 |
|--------|------|------|
| `users` | `email`, `hw_id`, `tier`, `expires`, `created` | 사용자 정보 |
| `sessions` | `session_id`, `email`, `created`, `used` | 업그레이드 세션 |
| `payments` | `payment_id`, `email`, `amount`, `tier`, `created` | 결제 기록 |

---

## 3. Python 코드 예시

### 3.1 로그인/인증

```python
# pc_license_dialog.py

def on_login_click(self):
    response = requests.post(API_URL, data={
        'action': 'check',
        'email': email,
        'hw_id': self.hw_id
    })
    # 결과: tier, days_left, expires 등
```

### 3.2 업그레이드 세션 생성 → 웹 열기

```python
# payment_dialog.py

def on_upgrade_click(self):
    # 세션 요청
    response = requests.post(API_URL, data={
        'action': 'create_upgrade_session',
        'email': self.email,
        'hw_id': get_hardware_id()
    })
    
    session_id = response.json()['session_id']
    
    # 브라우저 열기 (주소에 정보 노출 안 됨)
    url = f"https://youngstreet.co.kr/membership/upgrade.php?sid={session_id}"
    webbrowser.open(url)
    
    QMessageBox.information(self, "안내", 
        "웹에서 결제 완료 후 프로그램을 재시작해주세요.")
```

### 3.3 등급 제한 체크

```python
# unified_bot.py

TIER_LIMITS = {
    'free': {'symbols': 1, 'exchanges': 0, 'positions': 1},
    'basic': {'symbols': 3, 'exchanges': 1, 'positions': 2},
    'standard': {'symbols': 10, 'exchanges': 3, 'positions': 5},
    'premium': {'symbols': 999, 'exchanges': 999, 'positions': 999},
}

def _check_tier_limits(self):
    limits = TIER_LIMITS[self.tier]
    
    if len(self.symbols) > limits['symbols']:
        return "코인 개수 초과"
    
    if len(self.exchanges) > limits['exchanges']:
        return "거래소 개수 초과"
    
    if self.tier == 'free':
        if self.trial_days_left <= 0:
            return "무료 체험 만료"
    
    return None  # OK
```

### 3.4 등급 표시

```python
# staru_main.py 상단 바

def _update_tier_display(self):
    tier = self.license_info['tier']
    days = self.license_info['days_left']
    
    tier_icons = {
        'free': '🎁', 
        'basic': '⬜', 
        'standard': '🔷', 
        'premium': '💎'
    }
    
    self.tier_label.setText(f"{tier_icons[tier]} {tier.upper()} | {days}일")
```

---

## 4. 등급별 제한

| 등급 | 가격 | 심볼 | 거래소 | 동시 포지션 | 기타 |
|------|------|------|--------|-------------|------|
| 🎁 Free | $0 | 1개 | 0개 | 1개 | 백테스트만, 7일 체험 |
| ⬜ Basic | $29/월 | 3개 | 1개 | 2개 | 실매매, 텔레그램 |
| 🔷 Standard | $59/월 | 10개 | 3개 | 5개 | + 최적화 |
| 💎 Premium | $99/월 | 무제한 | 전체 | 무제한 | + 우선 지원 |

---

## 5. API 엔드포인트

### 5.1 라이선스 체크

```
POST https://youngstreet.co.kr/api/license.php
Content-Type: application/x-www-form-urlencoded

action=check&email=user@example.com&hw_id=ABC123
```

**응답:**
```json
{
  "success": true,
  "tier": "premium",
  "expires": "2025-12-31",
  "days_left": 365
}
```

### 5.2 업그레이드 세션 생성

```
POST https://youngstreet.co.kr/api/license.php
Content-Type: application/x-www-form-urlencoded

action=create_upgrade_session&email=user@example.com&hw_id=ABC123
```

**응답:**
```json
{
  "success": true,
  "session_id": "abc123def456"
}
```

### 5.3 업그레이드 페이지

```
GET https://youngstreet.co.kr/membership/upgrade.php?sid=abc123def456
```

---

## 6. 보안 고려사항

1. **HW_ID 검증**: 하드웨어 ID로 기기 바인딩
2. **세션 만료**: 업그레이드 세션 30분 후 만료
3. **HTTPS**: 모든 API 통신 암호화
4. **API 키 암호화**: Fernet으로 로컬 저장

---

## 7. 구현 체크리스트

| 기능 | Python | PHP | DB | 상태 |
|------|--------|-----|----|----|
| 로그인 | ✅ | ✅ | ✅ | 완료 |
| 등급 표시 | ✅ | - | - | 완료 |
| 세션 생성 | ❓ | ❓ | ❓ | 확인 필요 |
| 결제 처리 | - | ❓ | ❓ | 확인 필요 |
| 등급 제한 | ❓ | - | - | 확인 필요 |

---

**문서 작성:** Antigravity AI  
**검토:** -
