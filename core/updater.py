"""
TwinStar Quantum Auto Updater
Silent Install 방식 - Setup.exe 다운로드 후 자동 설치
"""

import sys
import json
import logging
import requests
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Callable


class Updater:
    """앱 내 자동 업데이트 관리 (Silent Install 방식)"""
    
    VERSION_URL = "https://raw.githubusercontent.com/choigoyoon/TwinStar-Quantum/main/version.json"
    CURRENT_VERSION = "1.8.3"
    
    def __init__(self):
        self.base_path = self._get_base_path()
        self.current_version = self._load_current_version()
    
    def _get_base_path(self) -> Path:
        """설치 경로 반환"""
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        else:
            return Path(__file__).parent.parent
    
    def _load_current_version(self) -> str:
        """현재 버전 로드"""
        version_file = self.base_path / "version.txt"
        if version_file.exists():
            try:
                return version_file.read_text(encoding='utf-8').strip()
            except Exception:
                try:
                    return version_file.read_text(encoding='utf-8-sig').strip()
                except Exception as e:
                    logging.error(f"[UPDATER] 버전 파일 로드 실패 (utf-8-sig): {e}")
                    # The original code returned CURRENT_VERSION if both failed.
                    # The instruction's `return False` is not compatible with the method's return type (str).
                    # Reverting to original behavior of returning CURRENT_VERSION on failure,
                    # but adding the requested logging.
                    return self.CURRENT_VERSION
        return self.CURRENT_VERSION
    
    def _save_current_version(self, version: str):
        """버전 저장"""
        version_file = self.base_path / "version.txt"
        try:
            version_file.write_text(version, encoding='utf-8')
            self.current_version = version
        except Exception as e:
            logging.error(f"[UPDATER] 버전 저장 실패: {e}")
    
    def _compare_version(self, v1: str, v2: str) -> int:
        """버전 비교: v1 > v2 → 1, v1 == v2 → 0, v1 < v2 → -1"""
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]
            
            for i in range(max(len(parts1), len(parts2))):
                p1 = parts1[i] if i < len(parts1) else 0
                p2 = parts2[i] if i < len(parts2) else 0
                if p1 > p2:
                    return 1
                if p1 < p2:
                    return -1
            return 0
        except (ValueError, TypeError):
            return 0
    
    def check_update(self) -> dict:
        """서버에서 최신 버전 확인"""
        try:
            response = requests.get(self.VERSION_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # [FIX] version.json의 'version' 키 사용 (latest_version 대신)
            latest = data.get('version', data.get('latest_version', '0.0.0'))
            has_update = self._compare_version(latest, self.current_version) > 0

            
            return {
                'success': True,
                'has_update': has_update,
                'current_version': self.current_version,
                'latest_version': latest,
                'download_url': data.get('download_url', ''),  # Setup.exe URL
                'download_size': data.get('download_size', ''),
                'changelog': self._parse_changelog(data.get('changelog', []), latest),
                'force_update': data.get('force_update', False)
            }

        except requests.exceptions.RequestException as e:
            logging.error(f"[UPDATER] 버전 확인 실패: {e}")
            return {
                'success': False,
                'has_update': False,
                'error': str(e)
            }
        except Exception as e:
            logging.error(f"[UPDATER] 예외 발생: {e}")
            return {
                'success': False,
                'has_update': False,
                'error': str(e)
            }
    
    def download_installer(
        self, 
        url: str, 
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Optional[Path]:
        """Setup.exe 다운로드 (임시 폴더에)"""
        try:
            # 임시 폴더에 저장 (사용자 폴더라 권한 문제 없음)
            temp_dir = Path(tempfile.gettempdir())
            installer_path = temp_dir / "TwinStar_Update_Setup.exe"
            
            logging.info(f"[UPDATER] 다운로드 시작: {url}")
            
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(installer_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)
            
            logging.info(f"[UPDATER] 다운로드 완료: {installer_path}")
            return installer_path
            
        except Exception as e:
            logging.error(f"[UPDATER] 다운로드 실패: {e}")
            return None
    
    def run_installer_and_exit(self, installer_path: Path) -> bool:
        """
        인스톨러 실행 후 현재 앱 종료
        Inno Setup /SILENT 옵션 사용
        """
        try:
            if not installer_path.exists():
                logging.error(f"[UPDATER] 인스톨러 파일 없음: {installer_path}")
                return False
            
            logging.info(f"[UPDATER] 인스톨러 실행: {installer_path}")
            
            # Inno Setup Silent 실행
            # /SILENT = 진행률만 표시 (사용자 입력 불필요)
            # /CLOSEAPPLICATIONS = 실행 중인 앱 자동 종료
            # /RESTARTAPPLICATIONS = 설치 후 앱 재시작
            subprocess.Popen(
                [str(installer_path), '/SILENT', '/CLOSEAPPLICATIONS', '/RESTARTAPPLICATIONS'],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            
            logging.info("[UPDATER] 인스톨러 시작됨. 앱 종료 중...")
            
            # 현재 앱 종료 (인스톨러가 덮어쓸 수 있도록)
            sys.exit(0)
            
        except Exception as e:
            logging.error(f"[UPDATER] 인스톨러 실행 실패: {e}")
            return False


    def _parse_changelog(self, raw_data, version: str) -> list:
        """changelog 데이터 파싱 (Dict/List/Str -> List)"""
        try:
            if isinstance(raw_data, dict):
                # "v1.2.3" or "1.2.3" key search
                return raw_data.get(f"v{version}", raw_data.get(version, []))
            elif isinstance(raw_data, str):
                return [raw_data]
            elif isinstance(raw_data, list):
                return raw_data
            return []
        except Exception:
            return []


# 싱글톤
_updater_instance = None

def get_updater() -> Updater:
    """Updater 싱글톤 인스턴스"""
    global _updater_instance
    if _updater_instance is None:
        _updater_instance = Updater()
    return _updater_instance


if __name__ == "__main__":
    # 테스트
    updater = get_updater()
    logger.info(f"현재 버전: {updater.current_version}")
    logger.info(f"Base Path: {updater.base_path}")
    
    result = updater.check_update()
    logger.info(f"업데이트 확인: {result}")
