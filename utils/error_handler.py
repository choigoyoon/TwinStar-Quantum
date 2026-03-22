"""
통합 에러 핸들러

일관된 에러 처리 및 사용자 피드백을 제공합니다.

v7.26 (2026-01-19): Phase 3 구현 - 에러 핸들링 통일
"""

import traceback
import logging
from typing import Optional, Callable, Any
from PyQt6.QtWidgets import QWidget, QMessageBox


class ErrorHandler:
    """
    통합 에러 핸들러 클래스

    모든 에러를 일관되게 처리하고 로깅/사용자 피드백을 제공합니다.
    """

    @staticmethod
    def handle_data_load_error(
        error: Exception,
        logger: logging.Logger,
        parent_widget: Optional[QWidget] = None,
        show_dialog: bool = True
    ) -> None:
        """
        데이터 로드 에러 핸들러

        Args:
            error: 발생한 예외
            logger: 로거 인스턴스
            parent_widget: 부모 위젯 (다이얼로그 표시용)
            show_dialog: 사용자 다이얼로그 표시 여부
        """
        error_type = type(error).__name__
        error_msg = f"데이터 로드 실패: {error_type}: {str(error)}"

        # 로깅
        logger.error(error_msg)
        logger.error(traceback.format_exc())

        # 사용자 피드백
        if show_dialog and parent_widget:
            QMessageBox.critical(
                parent_widget,
                "데이터 로드 오류",
                f"{error_msg}\n\n"
                f"가능한 원인:\n"
                f"1. 데이터 파일이 존재하지 않음\n"
                f"2. 데이터 형식이 잘못됨\n"
                f"3. 파일 접근 권한 없음\n\n"
                f"자세한 내용은 로그를 확인하세요."
            )

    @staticmethod
    def handle_optimization_error(
        error: Exception,
        logger: logging.Logger,
        parent_widget: Optional[QWidget] = None,
        show_dialog: bool = True,
        context: Optional[str] = None
    ) -> None:
        """
        최적화 실행 에러 핸들러

        Args:
            error: 발생한 예외
            logger: 로거 인스턴스
            parent_widget: 부모 위젯
            show_dialog: 다이얼로그 표시 여부
            context: 추가 컨텍스트 정보 (예: "Meta 최적화")
        """
        error_type = type(error).__name__
        context_str = f"{context} " if context else ""
        error_msg = f"{context_str}실행 중 에러: {error_type}: {str(error)}"

        # 로깅
        logger.error(error_msg)
        logger.error(traceback.format_exc())

        # 사용자 피드백
        if show_dialog and parent_widget:
            QMessageBox.critical(
                parent_widget,
                "최적화 오류",
                f"{error_msg}\n\n"
                f"가능한 원인:\n"
                f"1. 파라미터 범위가 잘못됨\n"
                f"2. 데이터가 충분하지 않음\n"
                f"3. 메모리 부족\n\n"
                f"자세한 내용은 로그를 확인하세요."
            )

    @staticmethod
    def handle_worker_error(
        error: Exception,
        logger: logging.Logger,
        parent_widget: Optional[QWidget] = None,
        show_dialog: bool = True,
        worker_name: Optional[str] = None
    ) -> None:
        """
        워커(QThread) 에러 핸들러

        Args:
            error: 발생한 예외
            logger: 로거 인스턴스
            parent_widget: 부모 위젯
            show_dialog: 다이얼로그 표시 여부
            worker_name: 워커 이름 (예: "OptimizationWorker")
        """
        error_type = type(error).__name__
        worker_str = f"{worker_name} " if worker_name else "워커 "
        error_msg = f"{worker_str}실행 중 에러: {error_type}: {str(error)}"

        # 로깅
        logger.error(error_msg)
        logger.error(traceback.format_exc())

        # 사용자 피드백
        if show_dialog and parent_widget:
            QMessageBox.critical(
                parent_widget,
                "워커 오류",
                f"{error_msg}\n\n"
                f"워커가 비정상 종료되었습니다.\n"
                f"자세한 내용은 로그를 확인하세요."
            )

    @staticmethod
    def handle_api_error(
        error: Exception,
        logger: logging.Logger,
        parent_widget: Optional[QWidget] = None,
        show_dialog: bool = True,
        api_name: Optional[str] = None
    ) -> None:
        """
        API 호출 에러 핸들러

        Args:
            error: 발생한 예외
            logger: 로거 인스턴스
            parent_widget: 부모 위젯
            show_dialog: 다이얼로그 표시 여부
            api_name: API 이름 (예: "Bybit API")
        """
        error_type = type(error).__name__
        api_str = f"{api_name} " if api_name else "API "
        error_msg = f"{api_str}호출 실패: {error_type}: {str(error)}"

        # 로깅
        logger.error(error_msg)
        logger.error(traceback.format_exc())

        # 사용자 피드백
        if show_dialog and parent_widget:
            QMessageBox.warning(
                parent_widget,
                "API 오류",
                f"{error_msg}\n\n"
                f"가능한 원인:\n"
                f"1. 네트워크 연결 문제\n"
                f"2. API 키가 잘못됨\n"
                f"3. 거래소 서버 문제\n"
                f"4. Rate Limit 초과\n\n"
                f"자세한 내용은 로그를 확인하세요."
            )

    @staticmethod
    def handle_generic_error(
        error: Exception,
        logger: logging.Logger,
        parent_widget: Optional[QWidget] = None,
        show_dialog: bool = True,
        operation: Optional[str] = None
    ) -> None:
        """
        일반 에러 핸들러

        Args:
            error: 발생한 예외
            logger: 로거 인스턴스
            parent_widget: 부모 위젯
            show_dialog: 다이얼로그 표시 여부
            operation: 작업 설명 (예: "파일 저장")
        """
        error_type = type(error).__name__
        operation_str = f"{operation} 중 " if operation else ""
        error_msg = f"{operation_str}에러 발생: {error_type}: {str(error)}"

        # 로깅
        logger.error(error_msg)
        logger.error(traceback.format_exc())

        # 사용자 피드백
        if show_dialog and parent_widget:
            QMessageBox.critical(
                parent_widget,
                "오류",
                f"{error_msg}\n\n"
                f"자세한 내용은 로그를 확인하세요."
            )

    @staticmethod
    def safe_execute(
        func: Callable,
        logger: logging.Logger,
        parent_widget: Optional[QWidget] = None,
        error_handler: Optional[Callable] = None,
        operation: Optional[str] = None,
        *args: Any,
        **kwargs: Any
    ) -> tuple[bool, Any]:
        """
        안전한 함수 실행 (try-except 래퍼)

        Args:
            func: 실행할 함수
            logger: 로거 인스턴스
            parent_widget: 부모 위젯
            error_handler: 커스텀 에러 핸들러
            operation: 작업 설명
            *args: 함수 인자
            **kwargs: 함수 키워드 인자

        Returns:
            (성공 여부, 반환값) 튜플
            - 성공: (True, result)
            - 실패: (False, None)

        Example:
            success, df = ErrorHandler.safe_execute(
                load_data,
                logger,
                parent_widget,
                operation="데이터 로드"
            )
            if success:
                process_data(df)
        """
        try:
            result = func(*args, **kwargs)
            return (True, result)
        except Exception as e:
            # 에러 핸들링
            if error_handler:
                error_handler(e, logger, parent_widget)
            else:
                ErrorHandler.handle_generic_error(
                    e, logger, parent_widget, operation=operation
                )
            return (False, None)


# 편의 함수들

def handle_data_load_error(
    error: Exception,
    logger: logging.Logger,
    parent_widget: Optional[QWidget] = None
) -> None:
    """데이터 로드 에러 핸들러 (단축 함수)"""
    ErrorHandler.handle_data_load_error(error, logger, parent_widget)


def handle_optimization_error(
    error: Exception,
    logger: logging.Logger,
    parent_widget: Optional[QWidget] = None,
    context: Optional[str] = None
) -> None:
    """최적화 에러 핸들러 (단축 함수)"""
    ErrorHandler.handle_optimization_error(error, logger, parent_widget, context=context)


def handle_worker_error(
    error: Exception,
    logger: logging.Logger,
    parent_widget: Optional[QWidget] = None,
    worker_name: Optional[str] = None
) -> None:
    """워커 에러 핸들러 (단축 함수)"""
    ErrorHandler.handle_worker_error(error, logger, parent_widget, worker_name=worker_name)


def safe_execute(
    func: Callable,
    logger: logging.Logger,
    parent_widget: Optional[QWidget] = None,
    operation: Optional[str] = None,
    *args: Any,
    **kwargs: Any
) -> tuple[bool, Any]:
    """안전한 함수 실행 (단축 함수)"""
    return ErrorHandler.safe_execute(
        func, logger, parent_widget, operation=operation, *args, **kwargs
    )


__all__ = [
    'ErrorHandler',
    'handle_data_load_error',
    'handle_optimization_error',
    'handle_worker_error',
    'safe_execute'
]
