"""
프리미엄 폰트 시스템
"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QFontDatabase
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class FontSystem:
    """폰트 관리 시스템"""
    
    # 폰트 우선순위 (설치된 것 중 사용)
    FONT_FAMILIES = [
        "Pretendard",
        "Pretendard Variable",
        "Spoqa Han Sans Neo",
        "Inter",
        "Noto Sans KR",
        "Malgun Gothic",  # 윈도우 기본
        "Apple SD Gothic Neo",  # 맥 기본
        "Segoe UI",
    ]
    
    MONO_FAMILIES = [
        "JetBrains Mono",
        "Fira Code",
        "D2Coding",
        "Consolas",
        "Monaco",
    ]
    
    @classmethod
    def load_custom_fonts(cls):
        """커스텀 폰트 로드 (fonts 폴더에서)"""
        try:
            # 프로젝트 루트의 fonts 폴더 찾기
            # 현재 파일: GUI/styles/fonts.py -> 상위: GUI/styles -> 상위: GUI -> 상위: Root
            root_dir = Path(__file__).parent.parent.parent
            fonts_dir = root_dir / "assets" / "fonts"  # assets/fonts 경로 권장
            
            if not fonts_dir.exists():
                # 혹시나 루트의 fonts 폴더일 경우
                fonts_dir = root_dir / "fonts"
            
            if fonts_dir.exists():
                count = 0
                for ext in ["*.ttf", "*.otf"]:
                    for font_file in fonts_dir.glob(ext):
                        QFontDatabase.addApplicationFont(str(font_file))
                        count += 1
                logger.info(f"Loaded {count} custom fonts from {fonts_dir}")
        except Exception as e:
            logger.warning(f"Failed to load custom fonts: {e}")
    
    @classmethod
    def get_best_font(cls) -> str:
        """사용 가능한 최적 폰트 반환"""
        db = QFontDatabase()
        available = db.families()
        
        for font in cls.FONT_FAMILIES:
            if font in available:
                return font
        
        return "Segoe UI"
    
    @classmethod
    def get_mono_font(cls) -> str:
        """모노스페이스 폰트 반환"""
        db = QFontDatabase()
        available = db.families()
        
        for font in cls.MONO_FAMILIES:
            if font in available:
                return font
        
        return "Consolas"
    
    @classmethod
    def apply_to_app(cls, app: QApplication):
        """앱 전체에 폰트 적용"""
        cls.load_custom_fonts()
        
        best_font = cls.get_best_font()
        font = QFont(best_font, 10)
        font.setStyleStrategy(QFont.PreferAntialias)
        
        app.setFont(font)
        logger.info(f"✅ 폰트 적용: {best_font}")
        
        return best_font
