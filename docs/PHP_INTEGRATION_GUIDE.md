# PHP 웹사이트 연동 가이드 (v7.29)

## 📁 파일 구조

```
your-php-website/
├── config/
│   └── twinstar_config.php      # TwinStar API 설정
├── classes/
│   └── TwinStarClient.php       # API 클라이언트 클래스
├── pages/
│   ├── dashboard.php            # 대시보드
│   ├── backtest.php             # 백테스트
│   ├── optimization.php         # 최적화
│   ├── trades.php               # 거래 내역
│   └── settings.php             # 설정
├── api/
│   └── proxy.php                # AJAX 프록시
└── assets/
    ├── css/twinstar.css         # 스타일
    └── js/twinstar.js           # JavaScript
```

---

## 🔧 1. 설정 파일

### config/twinstar_config.php

```php
<?php
/**
 * TwinStar Quantum API 설정
 */

return [
    // FastAPI 서버 URL
    'api_url' => 'http://localhost:8000/api',

    // JWT 인증 토큰 (환경 변수 권장)
    'api_token' => getenv('TWINSTAR_API_TOKEN') ?: 'your_jwt_token_here',

    // 타임아웃 설정 (초)
    'timeout' => 30,

    // 캐시 활성화
    'cache_enabled' => true,
    'cache_ttl' => 300, // 5분

    // 지원 거래소
    'exchanges' => ['bybit', 'binance', 'okx', 'bingx', 'bitget'],

    // 지원 타임프레임
    'timeframes' => ['15m', '1h', '4h', '1d'],

    // 최적화 모드
    'optimization_modes' => [
        'quick' => ['조합 8개', '예상 2분'],
        'standard' => ['조합 60개', '예상 15분'],
        'deep' => ['조합 1,080개', '예상 4.5시간'],
        'adaptive' => ['조합 360개', '예상 10분', '핵심 100%'],
        'meta' => ['자동 범위 탐색', '예상 20초']
    ]
];
?>
```

---

## 📦 2. API 클라이언트 클래스

### classes/TwinStarClient.php

```php
<?php
/**
 * TwinStar Quantum API 클라이언트
 */
class TwinStarClient {
    private $api_url;
    private $api_token;
    private $timeout;
    private $cache_enabled;
    private $cache_ttl;

    public function __construct($config) {
        $this->api_url = rtrim($config['api_url'], '/');
        $this->api_token = $config['api_token'];
        $this->timeout = $config['timeout'] ?? 30;
        $this->cache_enabled = $config['cache_enabled'] ?? true;
        $this->cache_ttl = $config['cache_ttl'] ?? 300;
    }

    /**
     * HTTP GET 요청
     */
    private function get($endpoint, $use_cache = true) {
        $cache_key = "twinstar_" . md5($endpoint);

        // 캐시 확인
        if ($use_cache && $this->cache_enabled) {
            $cached = apcu_fetch($cache_key);
            if ($cached !== false) {
                return $cached;
            }
        }

        $ch = curl_init($this->api_url . $endpoint);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => $this->timeout,
            CURLOPT_HTTPHEADER => [
                'Authorization: Bearer ' . $this->api_token,
                'Content-Type: application/json',
                'Accept: application/json'
            ]
        ]);

        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($http_code !== 200) {
            throw new Exception("API Error: HTTP $http_code - $response");
        }

        $data = json_decode($response, true);

        // 캐시 저장
        if ($use_cache && $this->cache_enabled) {
            apcu_store($cache_key, $data, $this->cache_ttl);
        }

        return $data;
    }

    /**
     * HTTP POST 요청
     */
    private function post($endpoint, $data = []) {
        $ch = curl_init($this->api_url . $endpoint);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($data),
            CURLOPT_TIMEOUT => $this->timeout,
            CURLOPT_HTTPHEADER => [
                'Authorization: Bearer ' . $this->api_token,
                'Content-Type: application/json',
                'Accept: application/json'
            ]
        ]);

        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($http_code !== 200 && $http_code !== 201 && $http_code !== 202) {
            throw new Exception("API Error: HTTP $http_code - $response");
        }

        return json_decode($response, true);
    }

    // ========== 대시보드 API ==========

    /**
     * 봇 상태 조회
     */
    public function getDashboardStatus() {
        return $this->get('/dashboard/status');
    }

    /**
     * 전체 PnL 조회
     */
    public function getTotalPnL() {
        $status = $this->getDashboardStatus();
        return [
            'total_pnl' => $status['total_pnl'] ?? 0,
            'today_pnl' => $status['today_pnl'] ?? 0,
            'win_rate' => $status['win_rate'] ?? 0,
            'active_trades' => $status['active_trades'] ?? 0
        ];
    }

    // ========== 백테스트 API ==========

    /**
     * 백테스트 실행
     */
    public function runBacktest($exchange, $symbol, $timeframe, $params = null) {
        return $this->post('/backtest', [
            'exchange' => $exchange,
            'symbol' => $symbol,
            'timeframe' => $timeframe,
            'params' => $params
        ]);
    }

    /**
     * 백테스트 결과 조회
     */
    public function getBacktestResult($task_id) {
        return $this->get("/backtest/result/$task_id", false);
    }

    // ========== 최적화 API ==========

    /**
     * 파라미터 최적화 실행
     */
    public function runOptimization($exchange, $symbol, $timeframe, $mode = 'quick') {
        return $this->post('/optimize', [
            'exchange' => $exchange,
            'symbol' => $symbol,
            'timeframe' => $timeframe,
            'mode' => $mode
        ]);
    }

    /**
     * 최적화 결과 조회
     */
    public function getOptimizationResult($task_id) {
        return $this->get("/optimize/result/$task_id", false);
    }

    // ========== 프리셋 API ==========

    /**
     * 프리셋 목록 조회
     */
    public function listPresets() {
        return $this->get('/presets');
    }

    /**
     * 프리셋 로드
     */
    public function loadPreset($symbol, $timeframe) {
        return $this->get("/presets/$symbol/$timeframe");
    }

    /**
     * 프리셋 저장
     */
    public function savePreset($symbol, $timeframe, $params, $metrics) {
        return $this->post('/presets', [
            'symbol' => $symbol,
            'timeframe' => $timeframe,
            'params' => $params,
            'metrics' => $metrics
        ]);
    }

    // ========== 거래 API ==========

    /**
     * 활성 포지션 조회
     */
    public function getActivePositions($exchange = null) {
        $endpoint = $exchange ? "/positions/$exchange" : '/positions';
        return $this->get($endpoint);
    }

    /**
     * 거래 내역 조회
     */
    public function getTradeHistory($limit = 100) {
        return $this->get("/trades?limit=$limit");
    }

    /**
     * 거래 실행
     */
    public function executeTrade($exchange, $symbol, $side, $amount) {
        return $this->post('/trade', [
            'exchange' => $exchange,
            'symbol' => $symbol,
            'side' => $side,
            'amount' => $amount
        ]);
    }

    // ========== 유틸리티 ==========

    /**
     * 캐시 클리어
     */
    public function clearCache() {
        if (function_exists('apcu_clear_cache')) {
            apcu_clear_cache();
        }
    }

    /**
     * 헬스 체크
     */
    public function healthCheck() {
        try {
            $this->get('/health', false);
            return true;
        } catch (Exception $e) {
            return false;
        }
    }
}
?>
```

---

## 📄 3. 페이지 예시

### pages/dashboard.php

```php
<?php
require_once '../config/twinstar_config.php';
require_once '../classes/TwinStarClient.php';

$config = require '../config/twinstar_config.php';
$client = new TwinStarClient($config);

try {
    // 대시보드 데이터 조회
    $status = $client->getDashboardStatus();
    $pnl = $client->getTotalPnL();
    $positions = $client->getActivePositions();

} catch (Exception $e) {
    $error = $e->getMessage();
}
?>

<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TwinStar Quantum - 대시보드</title>
    <link rel="stylesheet" href="../assets/css/twinstar.css">
</head>
<body>
    <div class="container">
        <h1>TwinStar Quantum 대시보드</h1>

        <?php if (isset($error)): ?>
            <div class="alert alert-error">
                ⚠️ API 연결 실패: <?= htmlspecialchars($error) ?>
            </div>
        <?php else: ?>

            <!-- 봇 상태 -->
            <div class="status-card">
                <h2>봇 상태</h2>
                <div class="status-indicator <?= $status['is_running'] ? 'online' : 'offline' ?>">
                    <?= $status['is_running'] ? '🟢 실행 중' : '🔴 중지' ?>
                </div>
                <p>업타임: <?= $status['uptime'] ?? 'N/A' ?></p>
            </div>

            <!-- PnL 요약 -->
            <div class="pnl-card">
                <h2>수익 현황</h2>
                <div class="metric">
                    <span class="label">총 수익:</span>
                    <span class="value <?= $pnl['total_pnl'] >= 0 ? 'positive' : 'negative' ?>">
                        <?= number_format($pnl['total_pnl'], 2) ?>%
                    </span>
                </div>
                <div class="metric">
                    <span class="label">오늘 수익:</span>
                    <span class="value <?= $pnl['today_pnl'] >= 0 ? 'positive' : 'negative' ?>">
                        <?= number_format($pnl['today_pnl'], 2) ?>%
                    </span>
                </div>
                <div class="metric">
                    <span class="label">승률:</span>
                    <span class="value"><?= number_format($pnl['win_rate'], 1) ?>%</span>
                </div>
            </div>

            <!-- 활성 포지션 -->
            <div class="positions-card">
                <h2>활성 포지션 (<?= count($positions) ?>)</h2>
                <?php if (empty($positions)): ?>
                    <p class="no-data">활성 포지션 없음</p>
                <?php else: ?>
                    <table class="positions-table">
                        <thead>
                            <tr>
                                <th>심볼</th>
                                <th>방향</th>
                                <th>진입가</th>
                                <th>현재가</th>
                                <th>수익</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($positions as $pos): ?>
                                <tr>
                                    <td><?= htmlspecialchars($pos['symbol']) ?></td>
                                    <td class="<?= strtolower($pos['side']) ?>">
                                        <?= $pos['side'] === 'Long' ? '🔼 롱' : '🔽 숏' ?>
                                    </td>
                                    <td>$<?= number_format($pos['entry_price'], 2) ?></td>
                                    <td>$<?= number_format($pos['current_price'], 2) ?></td>
                                    <td class="<?= $pos['pnl'] >= 0 ? 'positive' : 'negative' ?>">
                                        <?= number_format($pos['pnl'], 2) ?>%
                                    </td>
                                </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                <?php endif; ?>
            </div>

        <?php endif; ?>
    </div>

    <script src="../assets/js/twinstar.js"></script>
</body>
</html>
```

### pages/backtest.php

```php
<?php
require_once '../config/twinstar_config.php';
require_once '../classes/TwinStarClient.php';

$config = require '../config/twinstar_config.php';
$client = new TwinStarClient($config);

// 폼 처리
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        $exchange = $_POST['exchange'];
        $symbol = $_POST['symbol'];
        $timeframe = $_POST['timeframe'];

        $result = $client->runBacktest($exchange, $symbol, $timeframe);
        $task_id = $result['task_id'];

        // 결과 페이지로 리다이렉트
        header("Location: backtest_result.php?task_id=$task_id");
        exit;

    } catch (Exception $e) {
        $error = $e->getMessage();
    }
}
?>

<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>백테스트 실행</title>
    <link rel="stylesheet" href="../assets/css/twinstar.css">
</head>
<body>
    <div class="container">
        <h1>백테스트 실행</h1>

        <?php if (isset($error)): ?>
            <div class="alert alert-error">⚠️ <?= htmlspecialchars($error) ?></div>
        <?php endif; ?>

        <form method="POST" class="backtest-form">
            <div class="form-group">
                <label>거래소</label>
                <select name="exchange" required>
                    <?php foreach ($config['exchanges'] as $ex): ?>
                        <option value="<?= $ex ?>"><?= strtoupper($ex) ?></option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div class="form-group">
                <label>심볼</label>
                <input type="text" name="symbol" value="BTCUSDT" required>
            </div>

            <div class="form-group">
                <label>타임프레임</label>
                <select name="timeframe" required>
                    <?php foreach ($config['timeframes'] as $tf): ?>
                        <option value="<?= $tf ?>" <?= $tf === '1h' ? 'selected' : '' ?>>
                            <?= $tf ?>
                        </option>
                    <?php endforeach; ?>
                </select>
            </div>

            <button type="submit" class="btn btn-primary">백테스트 시작</button>
        </form>
    </div>
</body>
</html>
```

### pages/backtest_result.php

```php
<?php
require_once '../config/twinstar_config.php';
require_once '../classes/TwinStarClient.php';

$config = require '../config/twinstar_config.php';
$client = new TwinStarClient($config);

$task_id = $_GET['task_id'] ?? null;
if (!$task_id) {
    header('Location: backtest.php');
    exit;
}

try {
    $result = $client->getBacktestResult($task_id);

    // 결과 대기 중
    if ($result['status'] === 'pending' || $result['status'] === 'running') {
        $waiting = true;
    } else {
        $waiting = false;
        $metrics = $result['result']['metrics'];
    }

} catch (Exception $e) {
    $error = $e->getMessage();
}
?>

<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>백테스트 결과</title>
    <link rel="stylesheet" href="../assets/css/twinstar.css">
    <?php if (isset($waiting) && $waiting): ?>
        <meta http-equiv="refresh" content="3">
    <?php endif; ?>
</head>
<body>
    <div class="container">
        <h1>백테스트 결과</h1>

        <?php if (isset($error)): ?>
            <div class="alert alert-error">⚠️ <?= htmlspecialchars($error) ?></div>
        <?php elseif (isset($waiting) && $waiting): ?>
            <div class="alert alert-info">
                ⏳ 백테스트 실행 중... (자동 새로고침)
            </div>
        <?php else: ?>

            <div class="result-card">
                <h2>백테스트 메트릭</h2>

                <div class="metrics-grid">
                    <div class="metric-item">
                        <span class="label">승률</span>
                        <span class="value"><?= number_format($metrics['win_rate'], 2) ?>%</span>
                    </div>

                    <div class="metric-item">
                        <span class="label">총 거래</span>
                        <span class="value"><?= number_format($metrics['total_trades']) ?>회</span>
                    </div>

                    <div class="metric-item">
                        <span class="label">MDD</span>
                        <span class="value negative"><?= number_format($metrics['mdd'], 2) ?>%</span>
                    </div>

                    <div class="metric-item">
                        <span class="label">총 수익</span>
                        <span class="value <?= $metrics['total_pnl'] >= 0 ? 'positive' : 'negative' ?>">
                            <?= number_format($metrics['total_pnl'], 2) ?>%
                        </span>
                    </div>

                    <div class="metric-item">
                        <span class="label">Sharpe Ratio</span>
                        <span class="value"><?= number_format($metrics['sharpe_ratio'], 2) ?></span>
                    </div>

                    <div class="metric-item">
                        <span class="label">Profit Factor</span>
                        <span class="value"><?= number_format($metrics['profit_factor'], 2) ?></span>
                    </div>
                </div>

                <div class="grade-badge grade-<?= strtolower($metrics['stability']) ?>">
                    등급: <?= $metrics['stability'] ?>
                </div>
            </div>

            <a href="backtest.php" class="btn btn-secondary">다시 실행</a>

        <?php endif; ?>
    </div>
</body>
</html>
```

---

## 🎨 4. CSS 스타일

### assets/css/twinstar.css

```css
/* TwinStar Quantum PHP 스타일 */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background: #0f1419;
    color: #e4e6eb;
    line-height: 1.6;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

h1 {
    font-size: 28px;
    margin-bottom: 20px;
    color: #00d4ff;
}

h2 {
    font-size: 20px;
    margin-bottom: 15px;
    color: #b0b3b8;
}

/* 카드 */
.status-card, .pnl-card, .positions-card, .result-card {
    background: #1a1b1e;
    border: 1px solid #2a2d31;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
}

/* 상태 표시 */
.status-indicator {
    font-size: 18px;
    font-weight: 600;
    padding: 10px;
    border-radius: 6px;
    display: inline-block;
}

.status-indicator.online {
    background: rgba(0, 212, 255, 0.1);
    color: #00d4ff;
}

.status-indicator.offline {
    background: rgba(248, 81, 73, 0.1);
    color: #f85149;
}

/* 메트릭 */
.metric {
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid #2a2d31;
}

.metric:last-child {
    border-bottom: none;
}

.metric .label {
    color: #8b949e;
}

.metric .value {
    font-weight: 600;
    font-size: 18px;
}

.metric .value.positive {
    color: #3fb950;
}

.metric .value.negative {
    color: #f85149;
}

/* 테이블 */
.positions-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
}

.positions-table thead {
    background: #2a2d31;
}

.positions-table th,
.positions-table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #2a2d31;
}

.positions-table td.long {
    color: #3fb950;
}

.positions-table td.short {
    color: #f85149;
}

/* 폼 */
.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;
    margin-bottom: 8px;
    color: #b0b3b8;
    font-weight: 500;
}

.form-group input,
.form-group select {
    width: 100%;
    padding: 10px;
    background: #1a1b1e;
    border: 1px solid #2a2d31;
    border-radius: 6px;
    color: #e4e6eb;
    font-size: 14px;
}

.form-group input:focus,
.form-group select:focus {
    outline: none;
    border-color: #00d4ff;
}

/* 버튼 */
.btn {
    display: inline-block;
    padding: 12px 24px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    transition: all 0.2s;
}

.btn-primary {
    background: #00d4ff;
    color: #0f1419;
}

.btn-primary:hover {
    background: #00bfe6;
}

.btn-secondary {
    background: #2a2d31;
    color: #e4e6eb;
}

.btn-secondary:hover {
    background: #3a3d41;
}

/* 알림 */
.alert {
    padding: 15px;
    border-radius: 6px;
    margin-bottom: 20px;
}

.alert-error {
    background: rgba(248, 81, 73, 0.1);
    border: 1px solid #f85149;
    color: #f85149;
}

.alert-info {
    background: rgba(0, 212, 255, 0.1);
    border: 1px solid #00d4ff;
    color: #00d4ff;
}

/* 등급 뱃지 */
.grade-badge {
    display: inline-block;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 600;
    margin-top: 15px;
}

.grade-badge.grade-s {
    background: rgba(255, 215, 0, 0.2);
    color: #ffd700;
}

.grade-badge.grade-a {
    background: rgba(0, 212, 255, 0.2);
    color: #00d4ff;
}

.grade-badge.grade-b {
    background: rgba(63, 185, 80, 0.2);
    color: #3fb950;
}

.grade-badge.grade-c {
    background: rgba(255, 165, 0, 0.2);
    color: #ffa500;
}

.grade-badge.grade-d,
.grade-badge.grade-f {
    background: rgba(248, 81, 73, 0.2);
    color: #f85149;
}

/* 메트릭 그리드 */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 20px;
}

.metric-item {
    background: #2a2d31;
    padding: 15px;
    border-radius: 6px;
    text-align: center;
}

.metric-item .label {
    display: block;
    color: #8b949e;
    font-size: 12px;
    margin-bottom: 8px;
}

.metric-item .value {
    display: block;
    font-size: 24px;
    font-weight: 700;
}

.no-data {
    color: #8b949e;
    text-align: center;
    padding: 20px;
}
```

---

## 🔄 5. AJAX 실시간 업데이트 (선택)

### assets/js/twinstar.js

```javascript
/**
 * TwinStar Quantum JavaScript
 */

// 실시간 대시보드 업데이트
function updateDashboard() {
    fetch('/api/proxy.php?action=status')
        .then(res => res.json())
        .then(data => {
            // 봇 상태 업데이트
            const indicator = document.querySelector('.status-indicator');
            if (data.is_running) {
                indicator.className = 'status-indicator online';
                indicator.textContent = '🟢 실행 중';
            } else {
                indicator.className = 'status-indicator offline';
                indicator.textContent = '🔴 중지';
            }

            // PnL 업데이트
            updateMetric('total_pnl', data.total_pnl);
            updateMetric('today_pnl', data.today_pnl);
            updateMetric('win_rate', data.win_rate + '%');
        })
        .catch(err => console.error('Dashboard update failed:', err));
}

function updateMetric(id, value) {
    const elem = document.getElementById(id);
    if (elem) {
        elem.textContent = value;

        // 색상 업데이트
        if (id.includes('pnl')) {
            elem.className = value >= 0 ? 'value positive' : 'value negative';
        }
    }
}

// 5초마다 업데이트
setInterval(updateDashboard, 5000);
```

### api/proxy.php

```php
<?php
/**
 * AJAX 프록시 (CORS 우회)
 */
require_once '../config/twinstar_config.php';
require_once '../classes/TwinStarClient.php';

header('Content-Type: application/json');

$config = require '../config/twinstar_config.php';
$client = new TwinStarClient($config);

$action = $_GET['action'] ?? null;

try {
    switch ($action) {
        case 'status':
            echo json_encode($client->getDashboardStatus());
            break;

        case 'positions':
            echo json_encode($client->getActivePositions());
            break;

        case 'trades':
            $limit = $_GET['limit'] ?? 100;
            echo json_encode($client->getTradeHistory($limit));
            break;

        default:
            http_response_code(400);
            echo json_encode(['error' => 'Invalid action']);
    }

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
}
?>
```

---

## 🚀 6. 설치 및 실행

### Python 측 (TwinStar FastAPI 서버)

```bash
# 1. TwinStar 서버 시작
cd f:\TwinStar-Quantum\web
python run_server.py

# → http://localhost:8000 실행 중
```

### PHP 측 (웹사이트)

```bash
# 1. PHP 내장 서버 (테스트용)
cd your-php-website
php -S localhost:8080

# 2. Apache/Nginx 설정 (프로덕션)
# DocumentRoot를 your-php-website/로 설정

# 3. 환경 변수 설정
# .env 파일 생성
TWINSTAR_API_TOKEN=your_jwt_token_here
```

### 브라우저 접속

```
http://localhost:8080/pages/dashboard.php
```

---

## ✅ 체크리스트

- [ ] TwinStar FastAPI 서버 실행 (`http://localhost:8000`)
- [ ] PHP 설정 파일 작성 (`config/twinstar_config.php`)
- [ ] API 클라이언트 클래스 복사 (`classes/TwinStarClient.php`)
- [ ] 페이지 파일 생성 (`pages/*.php`)
- [ ] CSS/JS 파일 복사 (`assets/`)
- [ ] PHP APCu 캐시 활성화 (선택, 성능 향상)
- [ ] JWT 토큰 발급 및 설정
- [ ] 브라우저 테스트

---

이 가이드로 PHP 웹사이트 내부에서 TwinStar 데이터를 완전히 통합할 수 있습니다!
