/**
 * TwinStar Quantum - 웹 UI 가이드 데이터
 * 사용법, 매매법, FAQ, 텔레그램 설정 가이드
 */

const GUIDE_DATA = {
    // ========== 빠른 시작 가이드 ==========
    quickStart: {
        title: '🚀 빠른 시작 가이드',
        steps: [
            {
                num: 1,
                title: 'API 설정',
                desc: '설정 탭에서 거래소 API 키 등록 및 연결 테스트',
                icon: '🔑'
            },
            {
                num: 2,
                title: '데이터 수집',
                desc: '데이터 탭에서 원하는 심볼/기간 데이터 다운로드',
                icon: '📥'
            },
            {
                num: 3,
                title: '백테스트',
                desc: '백테스트 탭에서 전략 성과 검증',
                icon: '📊'
            },
            {
                num: 4,
                title: '파라미터 최적화',
                desc: '최적화 탭에서 최적의 파라미터 자동 탐색',
                icon: '🎯'
            },
            {
                num: 5,
                title: '프리셋 적용',
                desc: '검증된 설정을 프리셋으로 저장',
                icon: '💾'
            },
            {
                num: 6,
                title: '실매매 시작',
                desc: '자동매매 탭에서 봇 실행',
                icon: '🤖'
            }
        ],
        note: '※ 초기 1회 설정 후에는 6번(매매 시작)만 수행하면 됩니다.'
    },

    // ========== 워크플로우 ==========
    workflow: {
        title: '🔄 프로그램 운영 순서',
        items: [
            { step: 'API 설정', desc: '거래소 API 키 등록 및 연결 확인', tab: '설정' },
            { step: '데이터 수집', desc: '전략 검증을 위한 과거 캔들 데이터 다운로드', tab: '데이터' },
            { step: '백테스트', desc: '수집된 데이터로 전략의 과거 성과 검정', tab: '백테스트' },
            { step: '최적화', desc: '해당 코인에 가장 잘 맞는 파라미터 찾기', tab: '최적화' },
            { step: '프리셋 적용', desc: '검증된 설정값을 프리셋으로 저장', tab: '최적화' },
            { step: '실매매 시작', desc: '봇을 실행하여 실시간 시그널 매매', tab: '자동매매' }
        ]
    },

    // ========== 각 탭 기능 설명 ==========
    tabs: {
        title: '📑 각 탭 기능',
        items: [
            { 
                name: '📊 매매', 
                desc: '실시간 거래 실행, 포지션 관리, 잔고 확인',
                features: ['단일 거래 (롱/숏)', '활성 포지션 모니터링', '잔고 새로고침']
            },
            { 
                name: '🔬 백테스트', 
                desc: '과거 데이터로 전략 성과 검증',
                features: ['기간 설정', '레버리지 설정', '수익률/승률/MDD 분석']
            },
            { 
                name: '🎯 최적화', 
                desc: '최적의 파라미터 자동 탐색',
                features: ['빠른/표준/심층 검색', 'MACD/ADX-DI 전략 선택', '프리셋 자동 저장']
            },
            { 
                name: '⚙️ 설정', 
                desc: 'API 키, 텔레그램, 테마 설정',
                features: ['거래소 API 연동', '텔레그램 알림', '다크/라이트 테마']
            },
            { 
                name: '📜 거래내역', 
                desc: '매매 기록 조회 및 분석',
                features: ['필터링 (기간/심볼)', '손익 통계', 'CSV 내보내기']
            },
            { 
                name: '📥 데이터', 
                desc: '과거 캔들 데이터 다운로드',
                features: ['심볼/기간 선택', '다운로드 진행률', '파일 관리']
            },
            { 
                name: '🤖 자동매매', 
                desc: '다중 코인 자동 매매 봇',
                features: ['복리/고정 모드', '감시 대상 설정', '실시간 상태 모니터링']
            }
        ]
    },

    // ========== 거래소별 매매법 ==========
    tradingMethods: {
        title: '📈 거래소별 매매법',
        futures: {
            name: '선물 매매 (Bybit/Binance)',
            exchanges: ['Bybit', 'Binance', 'OKX', 'Bitget', 'BingX'],
            features: [
                '롱/숏 양방향 매매',
                '레버리지 사용 가능 (기본 3x)',
                'W 패턴 → 롱 진입',
                'M 패턴 → 숏 진입'
            ],
            params: {
                atrMult: '1.5 (손절)',
                trailingStart: '1.0R',
                trailingDist: '0.2R',
                rsiPeriod: 21
            },
            tips: [
                '포지션당 1-3% 리스크',
                '레버리지 3-5x 권장',
                '최대 레버리지 10x 이하 유지'
            ],
            warnings: [
                '청산가 확인 필수',
                '높은 레버리지 = 높은 리스크',
                '변동성 큰 시장 주의'
            ]
        },
        spot: {
            name: '현물 매매 (업비트/빗썸)',
            exchanges: ['업비트', '빗썸'],
            features: [
                '롱만 가능 (매수 → 매도)',
                '레버리지 없음 (1x)',
                'W 패턴만 감지',
                '청산 위험 없음'
            ],
            params: {
                atrMult: '1.5 (손절)',
                trailingStart: '1.0R',
                trailingDist: '0.2R',
                rsiPeriod: 21
            },
            tips: [
                '매매당 자본금 직접 설정',
                '기본 100,000원',
                '분산 투자 권장'
            ],
            warnings: [
                '업비트: IP 화이트리스트 필수!',
                '빗썸: 고객인증 완료 필요',
                '하락장에서는 수익 제한적'
            ]
        }
    },

    // ========== 텔레그램 설정 가이드 ==========
    telegram: {
        title: '📱 텔레그램 알림 설정',
        steps: [
            {
                num: 1,
                title: '봇 생성',
                desc: '텔레그램에서 @BotFather 검색 후 대화 시작',
                detail: '/newbot 입력 → 봇 이름 설정'
            },
            {
                num: 2,
                title: 'Bot Token 복사',
                desc: '봇 생성 완료 시 표시되는 토큰 복사',
                detail: '예: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz'
            },
            {
                num: 3,
                title: 'Chat ID 확인',
                desc: '@userinfobot 검색 → /start 입력',
                detail: '표시되는 숫자가 Chat ID (예: 987654321)'
            },
            {
                num: 4,
                title: '설정 입력',
                desc: '설정 탭에서 Bot Token과 Chat ID 입력',
                detail: '테스트 전송으로 연결 확인 후 저장'
            }
        ],
        notificationTypes: [
            { type: 'trade', label: '💰 진입/청산', desc: '매매 진입 및 청산 시 알림', default: true },
            { type: 'signal', label: '📊 신호 감지', desc: 'W/M 패턴 신호 발생 시', default: true },
            { type: 'system', label: '⚙️ 시스템', desc: '봇 시작/중지/에러 알림', default: true },
            { type: 'daily', label: '📈 일일 요약', desc: '매일 23:59 수익 요약', default: false }
        ]
    },

    // ========== 거래소 가입 혜택 (레퍼럴) ==========
    referrals: {
        title: '🎁 거래소 가입 혜택',
        exchanges: [
            {
                name: 'Bybit',
                benefits: ['수수료 20% 평생 할인', '최대 $30,000 보너스'],
                guide: '1. 아래 링크로 가입\n2. KYC 인증 완료\n3. 첫 입금 시 보너스 지급',
                link: 'https://www.bybit.com/invite?ref=TWINSTAR'
            },
            {
                name: 'Binance',
                benefits: ['수수료 10% 평생 할인', 'BNB 추가 할인'],
                guide: '1. 아래 링크로 가입\n2. 신원 인증 완료\n3. BNB 보유 시 추가 할인',
                link: 'https://www.binance.com/register?ref=TWINSTAR'
            },
            {
                name: 'OKX',
                benefits: ['수수료 20% 할인', '미스터리 박스'],
                guide: '1. 아래 링크로 가입\n2. 거래 시작 시 미스터리 박스 지급',
                link: 'https://www.okx.com/join/TWINSTAR'
            },
            {
                name: '업비트',
                benefits: ['국내 1위 거래소', '원화 입출금'],
                guide: '1. 업비트 앱 설치\n2. 본인인증 완료\n3. 은행 계좌 연동',
                link: 'https://upbit.com'
            },
            {
                name: '빗썸',
                benefits: ['국내 거래소', '원화 입출금'],
                guide: '1. 빗썸 앱 설치\n2. 본인인증 완료\n3. 은행 계좌 연동',
                link: 'https://bithumb.com'
            }
        ]
    },

    // ========== FAQ ==========
    faq: {
        title: '❓ 자주 묻는 질문',
        items: [
            {
                q: '라이선스는 어떻게 구매하나요?',
                a: '앱 실행 시 표시되는 USDT 주소로 $100 입금 후 "수동 활성화" 버튼을 클릭하세요.'
            },
            {
                q: '업비트에서 API가 안 되요.',
                a: '업비트는 고정 IP 등록이 필수입니다. VPS나 고정 IP 서비스를 이용하세요.'
            },
            {
                q: '봇이 매매를 안 해요.',
                a: '패턴이 감지되지 않으면 대기합니다. W/M 패턴은 자주 발생하지 않으니 인내심을 갖고 기다리세요.'
            },
            {
                q: '손절이 너무 빨라요.',
                a: 'ATR 배수를 조정할 수 있습니다. 기본 1.5에서 2.0으로 늘리면 여유가 생깁니다.'
            },
            {
                q: '테스트넷으로 먼저 해보고 싶어요.',
                a: 'Bybit/Binance는 Testnet 지원합니다. 설정에서 "Testnet Mode" 체크하세요.'
            },
            {
                q: '여러 코인을 동시에 거래할 수 있나요?',
                a: '자동매매 탭에서 감시 대상 수를 설정하면 다중 코인 매매가 가능합니다.'
            },
            {
                q: '수수료는 얼마나 드나요?',
                a: '거래소 수수료만 발생합니다. 레퍼럴 가입 시 20% 할인 가능!'
            },
            {
                q: 'API 연동에 실패합니다.',
                a: '키 입력 시 앞뒤 공백이 없는지, 거래소에서 API를 생성할 때 "Trading" 권한을 주었는지 확인하세요.'
            }
        ]
    },

    // ========== 주의사항 ==========
    warnings: {
        title: '⚠️ 주의사항',
        items: [
            '반드시 Testnet에서 먼저 테스트하세요!',
            '투자 금액은 잃어도 되는 금액만 사용하세요!',
            'API 키 권한은 최소한으로 설정 (출금 비활성화)',
            '24시간 봇 운영 시 서버 사용을 권장합니다',
            '과거 성과가 미래 수익을 보장하지 않습니다'
        ]
    },

    // ========== 에러 해결 ==========
    errors: {
        title: '❌ 주요 에러 해결',
        items: [
            {
                error: 'Insufficient Balance',
                cause: '거래소 계좌에 USDT(또는 KRW)가 부족',
                solution: '거래소에 자금 입금 후 재시도'
            },
            {
                error: 'Invalid Signature',
                cause: 'API 키 또는 시크릿 키가 부정확',
                solution: 'API 키 재확인 및 재입력'
            },
            {
                error: 'Connectivity Error',
                cause: '인터넷 또는 거래소 서버 상태 불안정',
                solution: '네트워크 확인 후 재시도'
            },
            {
                error: 'Position Not Found',
                cause: '청산하려는 포지션이 이미 없음',
                solution: '거래소에서 포지션 상태 확인'
            },
            {
                error: 'Rate Limit Exceeded',
                cause: 'API 호출 횟수 초과',
                solution: '잠시 대기 후 재시도 (보통 1분)'
            }
        ]
    },

    // ========== 자본 관리 설명 ==========
    capitalManagement: {
        title: '💰 자본 관리 모드',
        modes: [
            {
                name: '복리 모드',
                icon: '📈',
                desc: '현재 잔고 기준으로 거래',
                detail: '수익이 나면 다음 거래 금액도 증가, 손실 시 감소',
                example: '초기 $100 → 10% 수익 → 다음 거래 $110 기준'
            },
            {
                name: '고정 모드',
                icon: '📊',
                desc: '초기 시드 기준으로 거래',
                detail: '수익/손실과 관계없이 항상 동일한 금액으로 거래',
                example: '초기 $100 설정 → 항상 $100 기준 거래'
            }
        ],
        lockFeature: {
            title: '🔒 시드 잠금',
            desc: '잠금 시 초기 시드를 변경할 수 없습니다',
            tip: '실수로 시드를 변경하는 것을 방지합니다'
        }
    },

    // ========== 최적화 모드 설명 ==========
    optimizationModes: {
        title: '🎯 최적화 검색 모드',
        modes: [
            {
                name: '빠른 검색',
                combinations: '~36개',
                time: '~2분',
                desc: '핵심 파라미터만 빠르게 검색'
            },
            {
                name: '표준 검색',
                combinations: '~3,600개',
                time: '~20분',
                desc: '권장되는 밸런스 있는 검색'
            },
            {
                name: '심층 검색',
                combinations: '~12,800개',
                time: '~1시간',
                desc: '매우 정밀한 파라미터 탐색'
            },
            {
                name: '순차 검색',
                combinations: '~135개',
                time: '~5분',
                desc: '4단계 자동 순차 최적화'
            }
        ]
    }
};

// 내보내기 (브라우저 환경)
if (typeof window !== 'undefined') {
    window.GUIDE_DATA = GUIDE_DATA;
}

// 내보내기 (Node.js 환경)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GUIDE_DATA;
}
