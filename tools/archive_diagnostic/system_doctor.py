"""
자동 시스템 진단 및 수정 모듈
- 시작 시 자동 점검
- 문제 자동 해결
- 사용자 개입 최소화
"""

import os
import time
import json
import logging
import subprocess
import platform
from datetime import datetime
from typing import Tuple, List, Dict


class SystemDoctor:
    """시스템 자동 진단 및 치료"""
    
    def __init__(self):
        self.issues = []
        self.fixed = []
        self.warnings = []
    
    def run_full_checkup(self) -> Dict:
        """전체 시스템 점검"""
        logging.info("🏥 시스템 진단 시작...")
        
        results = {
            'time_sync': self.check_and_fix_time_sync(),
            'dependencies': self.check_dependencies(),
            'config_files': self.check_config_files(),
            'network': self.check_network(),
            'disk_space': self.check_disk_space(),
        }
        
        success_count = sum(1 for r in results.values() if r['status'] == 'OK')
        total = len(results)
        
        logging.info(f"🏥 진단 완료: {success_count}/{total} 정상")
        
        return {
            'results': results,
            'success': success_count,
            'total': total,
            'issues': self.issues,
            'fixed': self.fixed,
            'warnings': self.warnings
        }
    
    def check_and_fix_time_sync(self) -> Dict:
        """시간 동기화 점검 및 수정"""
        result = {'status': 'OK', 'message': '', 'action': None}
        
        try:
            import requests
            
            # 서버 시간 확인 (여러 소스)
            try:
                # Bybit 서버 시간
                resp = requests.get('https://api.bybit.com/v5/market/time', timeout=5)
                server_time = int(resp.json()['result']['timeSecond']) * 1000
            except:
                # 대체: worldtimeapi
                try:
                    resp = requests.get('http://worldtimeapi.org/api/ip', timeout=5)
                    server_time = int(datetime.fromisoformat(
                        resp.json()['datetime'].replace('Z', '+00:00')
                    ).timestamp() * 1000)
                except:
                    result['status'] = 'SKIP'
                    result['message'] = '서버 시간 확인 불가 (오프라인?)'
                    return result
            
            local_time = int(time.time() * 1000)
            offset = server_time - local_time
            
            if abs(offset) > 3000:  # 3초 이상 차이
                self.issues.append(f"시간 오차: {offset/1000:.1f}초")
                
                # Windows에서 시간 동기화 시도
                if platform.system() == 'Windows':
                    try:
                        # 관리자 권한 없이도 작동하는 방법
                        result['action'] = 'TIME_OFFSET_COMPENSATION'
                        result['offset_ms'] = offset
                        
                        # 설정 파일에 오프셋 저장
                        self._save_time_offset(offset)
                        
                        self.fixed.append(f"시간 오프셋 보정 적용: {offset}ms")
                        result['status'] = 'FIXED'
                        result['message'] = f'시간 오프셋 {offset/1000:.1f}초 자동 보정됨'
                    except Exception as e:
                        result['status'] = 'WARNING'
                        result['message'] = f'시간 동기화 필요: {offset/1000:.1f}초 차이'
                        self.warnings.append("Windows 설정 > 시간 동기화 권장")
                else:
                    result['status'] = 'WARNING'
                    result['message'] = f'시간 오프셋: {offset/1000:.1f}초'
            else:
                result['status'] = 'OK'
                result['message'] = f'시간 동기화 정상 (오프셋: {offset}ms)'
                
        except Exception as e:
            result['status'] = 'WARNING'
            result['message'] = f'시간 점검 실패: {e}'
        
        return result
    
    def _save_time_offset(self, offset: int):
        """시간 오프셋 저장"""
        config_path = os.path.join(os.path.dirname(__file__), 'data', 'system_config.json')
        
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        
        config['time_offset_ms'] = offset
        config['last_check'] = datetime.now().isoformat()
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def check_dependencies(self) -> Dict:
        """필수 패키지 점검"""
        result = {'status': 'OK', 'message': '', 'missing': []}
        
        required = ['ccxt', 'pybit', 'PyQt5', 'pandas', 'numpy', 'requests']
        missing = []
        
        for pkg in required:
            try:
                # PyQt5는 특별 케이스 (대소문자 유지)
                if pkg == 'PyQt5':
                    import PyQt5.QtCore
                else:
                    __import__(pkg.lower().replace('-', '_'))
            except ImportError:
                missing.append(pkg)
        
        if missing:
            result['status'] = 'ERROR'
            result['message'] = f'필수 패키지 누락: {", ".join(missing)}'
            result['missing'] = missing
            self.issues.append(f"패키지 누락: {missing}")
            
            # [FIX] EXE 환경에서는 pip 설치 불가
            if not getattr(sys, 'frozen', False):
                # 개발 환경: 자동 설치 시도
                for pkg in missing:
                    try:
                        subprocess.run(['pip', 'install', pkg], 
                                       capture_output=True, timeout=60)
                        self.fixed.append(f'{pkg} 자동 설치')
                    except:
                        pass
            else:
                # EXE 환경: 사용자에게 안내
                self.warnings.append(f"패키지 누락: {missing} - EXE 재빌드 필요")
                result['message'] += ' (EXE 재빌드 필요)'
        else:
            result['message'] = '모든 패키지 정상'
        
        return result
    
    def check_config_files(self) -> Dict:
        """설정 파일 점검"""
        result = {'status': 'OK', 'message': '', 'created': []}
        
        base_path = os.path.dirname(__file__)
        data_path = os.path.join(base_path, 'data')
        
        # 필수 디렉토리 생성
        os.makedirs(data_path, exist_ok=True)
        
        # 기본 설정 파일 생성
        default_configs = {
            'payment_config.json': {
                'usdt_address': '',
                'btc_address': '',
                'license_price_usd': 100
            },
            'capital_config.json': {
                'total_capital': 1000,
                'risk_per_trade': 2.0,
                'leverage': 3,
                'auto_sizing': False
            },
            'system_config.json': {
                'time_offset_ms': 0,
                'auto_check_enabled': True,
                'language': 'ko'
            }
        }
        
        created = []
        for filename, default_content in default_configs.items():
            filepath = os.path.join(data_path, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(default_content, f, indent=2, ensure_ascii=False)
                created.append(filename)
        
        if created:
            result['created'] = created
            result['message'] = f'설정 파일 생성: {", ".join(created)}'
            self.fixed.append(f'설정 파일 자동 생성: {created}')
        else:
            result['message'] = '모든 설정 파일 존재'
        
        return result
    
    def check_network(self) -> Dict:
        """네트워크 연결 점검"""
        result = {'status': 'OK', 'message': '', 'exchanges': {}}
        
        import requests
        
        endpoints = {
            'bybit': 'https://api.bybit.com/v5/market/time',
            'binance': 'https://api.binance.com/api/v3/time',
            'upbit': 'https://api.upbit.com/v1/market/all',
        }
        
        working = []
        failed = []
        
        for name, url in endpoints.items():
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    working.append(name)
                    result['exchanges'][name] = 'OK'
                else:
                    failed.append(name)
                    result['exchanges'][name] = 'ERROR'
            except:
                failed.append(name)
                result['exchanges'][name] = 'TIMEOUT'
        
        if failed:
            if len(failed) == len(endpoints):
                result['status'] = 'ERROR'
                result['message'] = '인터넷 연결 확인 필요'
                self.issues.append('네트워크 연결 실패')
            else:
                result['status'] = 'WARNING'
                result['message'] = f'{", ".join(failed)} 연결 불가'
                self.warnings.append(f'{failed} 거래소 연결 불가')
        else:
            result['message'] = '모든 거래소 연결 정상'
        
        return result
    
    def check_disk_space(self) -> Dict:
        """디스크 공간 점검"""
        result = {'status': 'OK', 'message': ''}
        
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            free_gb = free / (1024**3)
            
            if free_gb < 1:
                result['status'] = 'ERROR'
                result['message'] = f'디스크 공간 부족: {free_gb:.1f}GB'
                self.issues.append('디스크 공간 부족')
            elif free_gb < 5:
                result['status'] = 'WARNING'
                result['message'] = f'디스크 공간 주의: {free_gb:.1f}GB'
                self.warnings.append('디스크 공간 부족 주의')
            else:
                result['message'] = f'디스크 공간: {free_gb:.1f}GB'
        except:
            result['status'] = 'SKIP'
            result['message'] = '디스크 공간 확인 불가'
        
        return result


# 시작 시 자동 점검 함수
def auto_startup_check() -> Dict:
    """앱 시작 시 자동 점검"""
    doctor = SystemDoctor()
    return doctor.run_full_checkup()


def get_time_offset() -> int:
    """저장된 시간 오프셋 반환"""
    config_path = os.path.join(os.path.dirname(__file__), 'data', 'system_config.json')
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get('time_offset_ms', 0)
        except:
            pass
    
    return 0


# 테스트
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("=" * 50)
    print("🏥 시스템 자동 진단")
    print("=" * 50)
    
    result = auto_startup_check()
    
    print("\n📋 점검 결과:")
    for name, check in result['results'].items():
        status_icon = {'OK': '✅', 'FIXED': '🔧', 'WARNING': '⚠️', 'ERROR': '❌', 'SKIP': '⏭️'}
        icon = status_icon.get(check['status'], '❓')
        print(f"  {icon} {name}: {check['message']}")
    
    if result['fixed']:
        print("\n🔧 자동 수정:")
        for fix in result['fixed']:
            print(f"  • {fix}")
    
    if result['warnings']:
        print("\n⚠️ 주의사항:")
        for warn in result['warnings']:
            print(f"  • {warn}")
    
    print(f"\n📊 결과: {result['success']}/{result['total']} 정상")
