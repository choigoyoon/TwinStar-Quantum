# -*- coding: utf-8 -*-
"""
TwinStar Quantum - Language Manager
다국어 지원을 위한 언어 관리 모듈
"""

import json
import sys
import os
from pathlib import Path


class LangManager:
    """싱글톤 언어 관리자"""
    
    _instance = None
    _current_lang = 'ko'
    _translations = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.load_preference()
    
    def _get_locales_path(self) -> Path:
        """locales 폴더 경로 반환"""
        if getattr(sys, 'frozen', False):
            # PyInstaller 번들 환경
            base_path = Path(sys._MEIPASS)
        else:
            # 개발 환경
            base_path = Path(__file__).parent
        
        return base_path
    
    def set_language(self, lang_code: str):
        """
        언어 설정
        
        Args:
            lang_code: 'ko' 또는 'en'
        """
        self._current_lang = lang_code
        
        # JSON 파일 로드
        locales_path = self._get_locales_path()
        lang_file = locales_path / f"{lang_code}.json"
        
        if lang_file.exists():
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self._translations = json.load(f)
            except Exception as e:
                print(f"[Lang] Failed to load {lang_code}.json: {e}")
                self._translations = {}
        else:
            # 대체 경로 시도
            alt_paths = [
                Path("locales") / f"{lang_code}.json",
                Path(__file__).parent / f"{lang_code}.json",
            ]
            
            for alt_path in alt_paths:
                if alt_path.exists():
                    try:
                        with open(alt_path, 'r', encoding='utf-8') as f:
                            self._translations = json.load(f)
                        break
                    except:
                        continue
            else:
                print(f"[Lang] Language file not found: {lang_code}.json")
                self._translations = {}
        
        # 설정 저장
        self._save_preference(lang_code)
    
    def get(self, key: str, default: str = None) -> str:
        """
        번역 텍스트 가져오기
        
        Args:
            key: 점(.)으로 구분된 키 (예: 'dashboard.start_bot')
            default: 키가 없을 때 반환할 기본값
        
        Returns:
            번역된 텍스트
        """
        keys = key.split('.')
        value = self._translations
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default if default is not None else key
        
        return value if isinstance(value, str) else (default if default is not None else key)
    
    def t(self, key: str, default: str = None) -> str:
        """get()의 단축 메서드"""
        return self.get(key, default)
    
    def current_language(self) -> str:
        """현재 언어 코드 반환"""
        return self._current_lang
    
    def _save_preference(self, lang_code: str):
        """언어 설정 저장"""
        try:
            config_path = Path("config/settings.json")
            config = {}
            
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                except:
                    config = {}
            
            config['language'] = lang_code
            
            config_path.parent.mkdir(exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Lang] Failed to save preference: {e}")
    
    def load_preference(self):
        """저장된 언어 설정 불러오기"""
        try:
            config_path = Path("config/settings.json")
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    lang = config.get('language', 'ko')
                    self.set_language(lang)
            else:
                # 기본값: 한국어
                self.set_language('ko')
        except Exception as e:
            print(f"[Lang] Failed to load preference: {e}")
            self.set_language('ko')
    
    def get_available_languages(self) -> list:
        """사용 가능한 언어 목록"""
        return [
            {'code': 'ko', 'name': '한국어', 'flag': '🇰🇷'},
            {'code': 'en', 'name': 'English', 'flag': '🇺🇸'},
        ]


# ============ 전역 인스턴스 및 편의 함수 ============

_lang_manager: LangManager = None


def get_lang_manager() -> LangManager:
    """LangManager 싱글톤 인스턴스 반환"""
    global _lang_manager
    if _lang_manager is None:
        _lang_manager = LangManager()
    return _lang_manager


def t(key: str, default: str = None) -> str:
    """
    전역 번역 함수
    
    사용 예:
        from locales import t
        label = QLabel(t("dashboard.exchange"))
    
    Args:
        key: 점(.)으로 구분된 키
        default: 기본값
    
    Returns:
        번역된 텍스트
    """
    return get_lang_manager().t(key, default)


def set_language(lang_code: str):
    """
    전역 언어 설정
    
    Args:
        lang_code: 'ko' 또는 'en'
    """
    get_lang_manager().set_language(lang_code)


# 모듈 임포트 시 자동 초기화
get_lang_manager()
