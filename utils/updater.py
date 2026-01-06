"""
TwinStar Quantum - Auto Updater
서버 버전 확인 및 업데이트 알림 관리
"""
import requests
import json
import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

class AutoUpdater:
    """
    자동 업데이트 관리자
    - 서버의 version.json 확인
    - 로컬 버전과 비교
    - 업데이트 공지 및 링크 제공
    """
    
    UPDATE_URL = "http://youngstreet.co.kr/update/version.json"
    
    def __init__(self, current_version: str):
        self.current_version = current_version
        self.latest_info: Optional[Dict] = None

    def check_for_updates(self) -> Tuple[bool, Optional[Dict]]:
        """
        업데이트 필요 여부 확인
        Returns: (needs_update, latest_info)
        """
        logger.info(f"[UPDATE] Checking for updates (Current: {self.current_version})...")
        
        try:
            response = requests.get(self.UPDATE_URL, timeout=5)
            if response.status_code == 200:
                self.latest_info = response.json()
                latest_version = self.latest_info.get('version', '1.0.0')
                
                needs_update = self._compare_versions(self.current_version, latest_version)
                
                if needs_update:
                    logger.info(f"[UPDATE] New version available: {latest_version}")
                else:
                    logger.info("[UPDATE] System is up to date.")
                    
                return needs_update, self.latest_info
            else:
                logger.warning(f"[UPDATE] Failed to fetch version info: {response.status_code}")
        except Exception as e:
            logger.error(f"[UPDATE] Update check error: {e}")
            
        return False, None

    def _compare_versions(self, current: str, latest: str) -> bool:
        """버전 문자열 비교 (예: v1.7.0 vs v1.8.0)"""
        def parse_v(v_str):
            v_str = v_str.lower().strip()
            if v_str.startswith('v'): v_str = v_str[1:]
            return [int(x) for x in v_str.split('.') if x.isdigit()]
        
        try:
            c_parts = parse_v(current)
            l_parts = parse_v(latest)
            
            # 메이저, 마이너, 패치 비교
            for i in range(min(len(c_parts), len(l_parts))):
                if l_parts[i] > c_parts[i]: return True
                if l_parts[i] < c_parts[i]: return False
                
            return len(l_parts) > len(c_parts) # 예: 1.7.0 vs 1.7.0.1
        except:
            return latest != current

    def get_download_url(self) -> str:
        """최신 버전 다운로드 URL 반환"""
        if self.latest_info:
            return self.latest_info.get('download_url', 'http://youngstreet.co.kr/update/')
        return "http://youngstreet.co.kr/update/"

    def get_change_log(self) -> str:
        """변경 사항 요약 반환"""
        if self.latest_info:
            return self.latest_info.get('changes', '공지된 변경 사항이 없습니다.')
        return ""

if __name__ == "__main__":
    # 테스트
    updater = AutoUpdater("v1.7.0")
    # 실제 서버가 없으므로 로컬 테스트 시에는 URL을 모킹하거나 예외 처리됨
    needs_update, info = updater.check_for_updates()
    if needs_update:
        logger.info(f"새 버전 발견: {info['version']}")
        logger.info(f"다운로드: {updater.get_download_url()}")
    else:
        logger.info("최신 버전입니다.")

