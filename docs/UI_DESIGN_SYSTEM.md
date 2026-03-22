# TwinStar Quantum UI 디자인 시스템

**작성일**: 2026-01-13  
**버전**: 1.0  
**목적**: UI 디자인 시스템 표준화 및 통합

---

## 1. 현재 상태 분석

### 1.1 스타일 파일 현황 (문제점)

| 파일 | 라인 수 | 역할 | 문제점 |
|------|---------|------|--------|
| `GUI/styles/theme.py` | 309 | 기본 다크 테마 | Theme 클래스 |
| `GUI/styles/premium_theme.py` | 255 | 프리미엄 폰트+스타일 | PremiumTheme 클래스 |
| `GUI/styles/elegant_theme.py` | 305 | 글래스모피즘 테마 | ElegantTheme 클래스 |
| `GUI/styles/vivid_theme.py` | 184 | 고대비 테마 | VividTheme 클래스 |
| `GUI/styles/fonts.py` | 94 | 폰트 관리 | FontSystem 클래스 |
| `GUI/legacy_styles.py` | 441 | TradingView 스타일 | COLORS + MAIN_STYLE |
| `ui/styles.py` | 209 | 새 UI 스타일 | COLORS + STYLESHEET |

### 1.2 핵심 문제점

#### 🔴 Critical Issues

1. **테마 클래스 분산 (5개 이상)**
   - Theme, PremiumTheme, ElegantTheme, VividTheme 각각 별도 클래스
   - 어떤 테마가 실제 사용되는지 추적 어려움

2. **색상 정의 중복**
   ```python
   # GUI/styles/theme.py
   ACCENT_PRIMARY = "#00d4aa"
   
   # GUI/legacy_styles.py
   'primary': '#2962ff'  # 다른 색상!
   
   # ui/styles.py
   'primary': '#4fc3f7'  # 또 다른 색상!
   ```

3. **폰트 정의 중복**
   - `fonts.py`: Pretendard, Inter 우선
   - `premium_theme.py`: 직접 폰트 지정
   - `legacy_styles.py`: -apple-system, BlinkMacSystemFont

4. **스타일시트 적용 혼란**
   - `Theme.get_stylesheet()`
   - `PremiumTheme.get_stylesheet()`
   - `apply_style(app)` (legacy)
   - `STYLESHEET` 상수 (ui/styles.py)

---

## 2. 통합 디자인 시스템 설계

### 2.1 디자인 토큰 (Design Tokens)

#### 색상 시스템 (Color System)

```
┌─────────────────────────────────────────────────────────────┐
│                    COLOR TOKENS                              │
├─────────────────────────────────────────────────────────────┤
│  Background                                                  │
│  ├── bg-base:      #0d1117  (최상위 배경)                   │
│  ├── bg-surface:   #161b22  (카드/패널 배경)                │
│  ├── bg-elevated:  #21262d  (입력 필드, 높은 요소)          │
│  └── bg-overlay:   #30363d  (호버, 드롭다운)                │
├─────────────────────────────────────────────────────────────┤
│  Text                                                        │
│  ├── text-primary:   #f0f6fc  (기본 텍스트)                 │
│  ├── text-secondary: #8b949e  (보조 텍스트)                 │
│  └── text-muted:     #484f58  (비활성 텍스트)               │
├─────────────────────────────────────────────────────────────┤
│  Brand / Accent                                              │
│  ├── accent-primary:   #00d4aa  (메인 민트)                 │
│  ├── accent-secondary: #58a6ff  (보조 블루)                 │
│  └── accent-gradient:  #00d4aa → #00b894                    │
├─────────────────────────────────────────────────────────────┤
│  Semantic                                                    │
│  ├── success:   #3fb950  (수익/성공)                        │
│  ├── danger:    #f85149  (손실/위험)                        │
│  ├── warning:   #d29922  (경고)                             │
│  └── info:      #58a6ff  (정보)                             │
├─────────────────────────────────────────────────────────────┤
│  Border                                                      │
│  ├── border-default:  #30363d                               │
│  ├── border-muted:    #21262d                               │
│  └── border-accent:   #00d4aa                               │
└─────────────────────────────────────────────────────────────┘
```

#### 타이포그래피 시스템 (Typography)

```
┌─────────────────────────────────────────────────────────────┐
│                    TYPOGRAPHY TOKENS                         │
├─────────────────────────────────────────────────────────────┤
│  Font Family                                                 │
│  ├── font-sans:   Pretendard, Inter, Segoe UI, sans-serif   │
│  └── font-mono:   JetBrains Mono, Consolas, monospace       │
├─────────────────────────────────────────────────────────────┤
│  Font Size                                                   │
│  ├── text-xs:   11px                                        │
│  ├── text-sm:   12px                                        │
│  ├── text-base: 14px  (기본)                                │
│  ├── text-lg:   16px                                        │
│  ├── text-xl:   18px                                        │
│  ├── text-2xl:  24px                                        │
│  └── text-3xl:  28px                                        │
├─────────────────────────────────────────────────────────────┤
│  Font Weight                                                 │
│  ├── font-normal:   400                                     │
│  ├── font-medium:   500                                     │
│  ├── font-semibold: 600                                     │
│  └── font-bold:     700                                     │
└─────────────────────────────────────────────────────────────┘
```

#### 간격 시스템 (Spacing)

```
┌─────────────────────────────────────────────────────────────┐
│                    SPACING TOKENS                            │
├─────────────────────────────────────────────────────────────┤
│  ├── space-0:   0px                                         │
│  ├── space-1:   4px                                         │
│  ├── space-2:   8px                                         │
│  ├── space-3:   12px                                        │
│  ├── space-4:   16px                                        │
│  ├── space-5:   20px                                        │
│  ├── space-6:   24px                                        │
│  ├── space-8:   32px                                        │
│  └── space-10:  40px                                        │
└─────────────────────────────────────────────────────────────┘
```

#### 모서리 / 그림자 (Radius & Shadow)

```
┌─────────────────────────────────────────────────────────────┐
│                    RADIUS TOKENS                             │
├─────────────────────────────────────────────────────────────┤
│  ├── radius-sm:   4px   (버튼, 입력)                        │
│  ├── radius-md:   8px   (카드)                              │
│  ├── radius-lg:   12px  (패널, 모달)                        │
│  └── radius-full: 9999px (원형)                             │
├─────────────────────────────────────────────────────────────┤
│                    SHADOW TOKENS                             │
├─────────────────────────────────────────────────────────────┤
│  ├── shadow-sm:   0 1px 2px rgba(0,0,0,0.3)                 │
│  ├── shadow-md:   0 4px 8px rgba(0,0,0,0.4)                 │
│  └── shadow-lg:   0 8px 16px rgba(0,0,0,0.5)                │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.2 통합 파일 구조

```
ui/
├── __init__.py              # 공개 API
├── design_system/           # 디자인 시스템 (신규)
│   ├── __init__.py
│   ├── tokens.py            # 디자인 토큰 정의
│   ├── colors.py            # 색상 상수
│   ├── typography.py        # 폰트 시스템
│   ├── spacing.py           # 간격 상수
│   └── theme.py             # 테마 생성기
│
├── styles/                  # 컴포넌트 스타일
│   ├── __init__.py
│   ├── base.py              # 기본 위젯 스타일
│   ├── buttons.py           # 버튼 스타일
│   ├── inputs.py            # 입력 필드 스타일
│   ├── tables.py            # 테이블 스타일
│   └── cards.py             # 카드 스타일
│
├── widgets/                 # UI 위젯
├── dialogs/                 # 다이얼로그
├── workers/                 # 백그라운드 워커
└── components/              # 재사용 컴포넌트
```

---

## 3. 통합 디자인 토큰 구현

### 3.1 tokens.py (핵심 파일)

```python
"""
ui/design_system/tokens.py
TwinStar Quantum 디자인 토큰 (Single Source of Truth)
"""

from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class ColorTokens:
    """색상 토큰"""
    # Background
    bg_base: str = "#0d1117"
    bg_surface: str = "#161b22"
    bg_elevated: str = "#21262d"
    bg_overlay: str = "#30363d"
    
    # Text
    text_primary: str = "#f0f6fc"
    text_secondary: str = "#8b949e"
    text_muted: str = "#484f58"
    
    # Accent
    accent_primary: str = "#00d4aa"
    accent_secondary: str = "#58a6ff"
    
    # Semantic
    success: str = "#3fb950"
    danger: str = "#f85149"
    warning: str = "#d29922"
    info: str = "#58a6ff"
    
    # Border
    border_default: str = "#30363d"
    border_muted: str = "#21262d"
    border_accent: str = "#00d4aa"


@dataclass(frozen=True)
class TypographyTokens:
    """타이포그래피 토큰"""
    # Font Family
    font_sans: str = "'Pretendard', 'Inter', 'Segoe UI', sans-serif"
    font_mono: str = "'JetBrains Mono', 'Consolas', monospace"
    
    # Font Size
    text_xs: str = "11px"
    text_sm: str = "12px"
    text_base: str = "14px"
    text_lg: str = "16px"
    text_xl: str = "18px"
    text_2xl: str = "24px"
    text_3xl: str = "28px"
    
    # Font Weight
    font_normal: int = 400
    font_medium: int = 500
    font_semibold: int = 600
    font_bold: int = 700


@dataclass(frozen=True)
class SpacingTokens:
    """간격 토큰"""
    space_0: str = "0px"
    space_1: str = "4px"
    space_2: str = "8px"
    space_3: str = "12px"
    space_4: str = "16px"
    space_5: str = "20px"
    space_6: str = "24px"
    space_8: str = "32px"
    space_10: str = "40px"


@dataclass(frozen=True)
class RadiusTokens:
    """모서리 토큰"""
    radius_sm: str = "4px"
    radius_md: str = "8px"
    radius_lg: str = "12px"
    radius_full: str = "9999px"


@dataclass(frozen=True)
class ShadowTokens:
    """그림자 토큰"""
    shadow_sm: str = "0 1px 2px rgba(0,0,0,0.3)"
    shadow_md: str = "0 4px 8px rgba(0,0,0,0.4)"
    shadow_lg: str = "0 8px 16px rgba(0,0,0,0.5)"


# 싱글톤 인스턴스
Colors = ColorTokens()
Typography = TypographyTokens()
Spacing = SpacingTokens()
Radius = RadiusTokens()
Shadow = ShadowTokens()


# 편의 함수
def get_gradient(start: str = None, end: str = None) -> str:
    """그라디언트 문자열 생성"""
    start = start or Colors.accent_primary
    end = end or "#00b894"
    return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {start}, stop:1 {end})"
```

### 3.2 theme.py (테마 생성기)

```python
"""
ui/design_system/theme.py
통합 테마 생성기
"""

from .tokens import Colors, Typography, Spacing, Radius, Shadow, get_gradient


class ThemeGenerator:
    """테마 스타일시트 생성기"""
    
    @classmethod
    def generate(cls) -> str:
        """전체 스타일시트 생성"""
        return f"""
        /* ===== Global ===== */
        QWidget {{
            background-color: {Colors.bg_base};
            color: {Colors.text_primary};
            font-family: {Typography.font_sans};
            font-size: {Typography.text_base};
        }}
        
        /* ===== Main Window ===== */
        QMainWindow {{
            background-color: {Colors.bg_base};
        }}
        
        /* ===== Cards / GroupBox ===== */
        QGroupBox {{
            background-color: {Colors.bg_surface};
            border: 1px solid {Colors.border_default};
            border-radius: {Radius.radius_lg};
            margin-top: {Spacing.space_4};
            padding: {Spacing.space_4};
            font-weight: {Typography.font_semibold};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: {Spacing.space_4};
            padding: 0 {Spacing.space_2};
            color: {Colors.accent_primary};
        }}
        
        /* ===== Buttons ===== */
        QPushButton {{
            background: {get_gradient()};
            color: {Colors.bg_base};
            border: none;
            border-radius: {Radius.radius_sm};
            padding: {Spacing.space_3} {Spacing.space_5};
            font-weight: {Typography.font_semibold};
            min-height: 36px;
        }}
        
        QPushButton:hover {{
            background: {Colors.accent_primary};
        }}
        
        QPushButton:pressed {{
            background: #00b894;
        }}
        
        QPushButton:disabled {{
            background: {Colors.bg_elevated};
            color: {Colors.text_muted};
        }}
        
        QPushButton[variant="danger"] {{
            background: {Colors.danger};
            color: white;
        }}
        
        QPushButton[variant="secondary"] {{
            background: {Colors.bg_elevated};
            color: {Colors.text_primary};
            border: 1px solid {Colors.border_default};
        }}
        
        /* ===== Input Fields ===== */
        QLineEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {Colors.bg_elevated};
            border: 1px solid {Colors.border_default};
            border-radius: {Radius.radius_sm};
            padding: {Spacing.space_2} {Spacing.space_3};
            color: {Colors.text_primary};
            min-height: 36px;
        }}
        
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {Colors.accent_primary};
        }}
        
        /* ===== ComboBox ===== */
        QComboBox {{
            background-color: {Colors.bg_elevated};
            border: 1px solid {Colors.border_default};
            border-radius: {Radius.radius_sm};
            padding: {Spacing.space_2} {Spacing.space_3};
            min-height: 36px;
        }}
        
        QComboBox:hover {{
            border-color: {Colors.accent_primary};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {Colors.bg_surface};
            border: 1px solid {Colors.border_default};
            selection-background-color: {Colors.accent_primary};
            selection-color: {Colors.bg_base};
        }}
        
        /* ===== Tabs ===== */
        QTabWidget::pane {{
            border: none;
            background: {Colors.bg_base};
        }}
        
        QTabBar::tab {{
            background: transparent;
            color: {Colors.text_secondary};
            padding: {Spacing.space_3} {Spacing.space_6};
            border-bottom: 2px solid transparent;
            font-weight: {Typography.font_medium};
        }}
        
        QTabBar::tab:selected {{
            color: {Colors.accent_primary};
            border-bottom: 2px solid {Colors.accent_primary};
        }}
        
        QTabBar::tab:hover:!selected {{
            color: {Colors.text_primary};
            background: {Colors.bg_overlay};
        }}
        
        /* ===== Tables ===== */
        QTableWidget {{
            background-color: {Colors.bg_surface};
            border: none;
            gridline-color: {Colors.border_default};
        }}
        
        QTableWidget::item {{
            padding: {Spacing.space_2};
            border-bottom: 1px solid {Colors.border_muted};
        }}
        
        QTableWidget::item:selected {{
            background-color: {Colors.accent_primary};
            color: {Colors.bg_base};
        }}
        
        QHeaderView::section {{
            background-color: {Colors.bg_elevated};
            color: {Colors.text_secondary};
            padding: {Spacing.space_3};
            border: none;
            font-weight: {Typography.font_semibold};
            font-size: {Typography.text_sm};
        }}
        
        /* ===== ScrollBar ===== */
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {Colors.border_default};
            border-radius: {Radius.radius_sm};
            min-height: 30px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: {Colors.accent_primary};
        }}
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        
        /* ===== Labels ===== */
        QLabel {{
            color: {Colors.text_primary};
            background: transparent;
        }}
        
        QLabel[variant="muted"] {{
            color: {Colors.text_secondary};
            font-size: {Typography.text_sm};
        }}
        
        QLabel[variant="success"] {{
            color: {Colors.success};
            font-weight: {Typography.font_semibold};
        }}
        
        QLabel[variant="danger"] {{
            color: {Colors.danger};
            font-weight: {Typography.font_semibold};
        }}
        
        QLabel[variant="accent"] {{
            color: {Colors.accent_primary};
            font-weight: {Typography.font_semibold};
        }}
        
        /* ===== TextEdit (Log) ===== */
        QTextEdit {{
            background-color: #000000;
            border: 1px solid {Colors.border_default};
            border-radius: {Radius.radius_md};
            font-family: {Typography.font_mono};
            font-size: {Typography.text_sm};
            padding: {Spacing.space_2};
            color: #00ff00;
        }}
        
        /* ===== CheckBox ===== */
        QCheckBox {{
            spacing: {Spacing.space_2};
        }}
        
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: {Radius.radius_sm};
            border: 2px solid {Colors.border_default};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {Colors.accent_primary};
            border-color: {Colors.accent_primary};
        }}
        
        /* ===== ProgressBar ===== */
        QProgressBar {{
            background-color: {Colors.bg_elevated};
            border: none;
            border-radius: {Radius.radius_sm};
            height: 8px;
            text-align: center;
        }}
        
        QProgressBar::chunk {{
            background: {get_gradient()};
            border-radius: {Radius.radius_sm};
        }}
        
        /* ===== Splitter ===== */
        QSplitter::handle {{
            background: {Colors.border_default};
        }}
        
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        
        /* ===== ToolTip ===== */
        QToolTip {{
            background-color: {Colors.bg_surface};
            color: {Colors.text_primary};
            border: 1px solid {Colors.border_default};
            border-radius: {Radius.radius_sm};
            padding: {Spacing.space_2} {Spacing.space_3};
        }}
        """
```

---

## 4. 컴포넌트 스타일 가이드

### 4.1 버튼 (Buttons)

| 변형 | 용도 | 스타일 |
|------|------|--------|
| `default` | 기본 액션 | 민트 그라디언트 배경 |
| `secondary` | 보조 액션 | 회색 배경 + 테두리 |
| `danger` | 위험 액션 (삭제, 중지) | 빨간 배경 |
| `ghost` | 텍스트 버튼 | 투명 배경 |

```python
# 사용 예시
btn = QPushButton("시작")
btn.setProperty("variant", "default")

stop_btn = QPushButton("중지")
stop_btn.setProperty("variant", "danger")
```

### 4.2 카드 (Cards)

```python
# 상태 카드
class StatusCard(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setProperty("variant", "card")
        # ...
```

### 4.3 입력 필드 (Inputs)

| 상태 | 스타일 |
|------|--------|
| 기본 | 회색 테두리 |
| 포커스 | 민트 테두리 |
| 오류 | 빨간 테두리 |
| 비활성 | 흐린 배경 |

### 4.4 테이블 (Tables)

- 헤더: 어두운 배경, 대문자, 작은 글씨
- 행: 호버 시 배경 변경
- 선택: 민트 배경

---

## 5. 마이그레이션 가이드

### 5.1 기존 테마 매핑

| 기존 | 신규 | 상태 |
|------|------|------|
| `Theme` | `ThemeGenerator` | 대체 |
| `PremiumTheme` | (병합) | 삭제 |
| `ElegantTheme` | (병합) | 삭제 |
| `VividTheme` | (병합) | 삭제 |
| `FontSystem` | `Typography` 토큰 | 통합 |
| `legacy_styles.COLORS` | `Colors` 토큰 | 대체 |
| `ui/styles.COLORS` | `Colors` 토큰 | 대체 |

### 5.2 코드 변경 예시

```python
# Before (기존)
from GUI.styles.theme import Theme
app.setStyleSheet(Theme.get_stylesheet())

# After (신규)
from ui.design_system.theme import ThemeGenerator
app.setStyleSheet(ThemeGenerator.generate())
```

```python
# Before (색상 직접 참조)
label.setStyleSheet("color: #00d4aa;")

# After (토큰 사용)
from ui.design_system.tokens import Colors
label.setStyleSheet(f"color: {Colors.accent_primary};")
```

---

## 6. 구현 우선순위

### Phase 0: 디자인 시스템 기반 (1주)

1. [ ] `ui/design_system/tokens.py` 생성
2. [ ] `ui/design_system/theme.py` 생성
3. [ ] 기존 테마들의 스타일 통합
4. [ ] 폰트 시스템 통합

### Phase 1: 점진적 마이그레이션 (2주)

1. [ ] `staru_main.py`에서 새 테마 적용
2. [ ] 주요 위젯에 토큰 적용
3. [ ] 기존 테마 파일 deprecated 표시
4. [ ] 문서화

### Phase 2: 완전 이전 (1주)

1. [ ] 모든 위젯 새 시스템 적용
2. [ ] 기존 테마 파일 제거
3. [ ] 테스트 및 QA

---

## 7. 부록

### A. 색상 팔레트 시각화

```
Background Scale:
#0d1117 ████ bg-base (가장 어두움)
#161b22 ████ bg-surface
#21262d ████ bg-elevated
#30363d ████ bg-overlay (가장 밝음)

Text Scale:
#f0f6fc ████ text-primary
#8b949e ████ text-secondary
#484f58 ████ text-muted

Accent:
#00d4aa ████ accent-primary (민트)
#58a6ff ████ accent-secondary (블루)

Semantic:
#3fb950 ████ success (녹색)
#f85149 ████ danger (빨강)
#d29922 ████ warning (노랑)
#58a6ff ████ info (파랑)
```

### B. 폰트 우선순위

1. **Pretendard** - 한글/영문 최적화
2. **Inter** - 숫자 가독성 우수
3. **Segoe UI** - Windows 기본
4. **Apple SD Gothic Neo** - macOS 기본

### C. 접근성 고려사항

- 최소 대비율: 4.5:1 (WCAG AA)
- 포커스 상태 명확히 표시
- 색각 이상자를 위한 추가 구분 요소 (아이콘, 텍스트)

---

**문서 작성**: AI Assistant  
**최종 수정**: 2026-01-13
