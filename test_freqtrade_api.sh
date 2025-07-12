#!/bin/bash
# FreqTrade API Test Script for CLI/Docker
# Usage: ./test_freqtrade_api.sh [base_url] [username] [password]

# Default configuration (from your docker-compose setup)
BASE_URL="${1:-http://freqtrade:8080}"  # Use container name when running inside Docker network
USERNAME="${2:-freq}"
PASSWORD="${3:-abcdef}"

echo "🔍 FreqTrade API Test"
echo "   Base URL: $BASE_URL"
echo "   Username: $USERNAME"
echo "=================================================="

# Function to make authenticated API calls
make_api_call() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    
    if [ -z "$TOKEN" ]; then
        echo "❌ No authentication token available"
        return 1
    fi
    
    if [ "$method" = "GET" ]; then
        curl -s -X GET \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            "$BASE_URL$endpoint"
    else
        if [ -n "$data" ]; then
            curl -s -X "$method" \
                -H "Authorization: Bearer $TOKEN" \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$BASE_URL$endpoint"
        else
            curl -s -X "$method" \
                -H "Authorization: Bearer $TOKEN" \
                -H "Content-Type: application/json" \
                "$BASE_URL$endpoint"
        fi
    fi
}

# Test basic connectivity
echo "🔗 Testing basic connectivity..."
if ! curl -s --connect-timeout 5 "$BASE_URL/api/v1/ping" > /dev/null; then
    echo "❌ Cannot connect to FreqTrade API at $BASE_URL"
    echo "   Make sure FreqTrade is running and accessible"
    exit 1
fi
echo "✅ Basic connectivity OK"

# Authenticate and get token
echo ""
echo "🔐 Authenticating..."
AUTH_RESPONSE=$(curl -s -X POST \
    --user "$USERNAME:$PASSWORD" \
    "$BASE_URL/api/v1/token/login")

if [ $? -ne 0 ]; then
    echo "❌ Authentication request failed"
    exit 1
fi

# Extract token from response
TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Authentication failed"
    echo "   Response: $AUTH_RESPONSE"
    exit 1
fi

echo "✅ Authentication successful!"
echo "   Token: $(echo "$TOKEN" | cut -c1-20)..."

# Test version endpoint
echo ""
echo "📋 Testing version endpoint..."
VERSION_RESPONSE=$(make_api_call "GET" "/api/v1/version")
if echo "$VERSION_RESPONSE" | grep -q "version"; then
    VERSION=$(echo "$VERSION_RESPONSE" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    echo "✅ Version endpoint working!"
    echo "   FreqTrade version: $VERSION"
else
    echo "❌ Version endpoint failed"
    echo "   Response: $VERSION_RESPONSE"
fi

# Test status endpoint
echo ""
echo "📊 Testing status endpoint..."
STATUS_RESPONSE=$(make_api_call "GET" "/api/v1/status")
echo "   Raw response: $STATUS_RESPONSE"

if echo "$STATUS_RESPONSE" | grep -q "state"; then
    STATE=$(echo "$STATUS_RESPONSE" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
    STRATEGY=$(echo "$STATUS_RESPONSE" | grep -o '"strategy":"[^"]*"' | cut -d'"' -f4)
    TRADES=$(echo "$STATUS_RESPONSE" | grep -o '"open_trade_count":[0-9]*' | cut -d':' -f2)
    echo "✅ Status endpoint working!"
    echo "   Bot state: $STATE"
    echo "   Strategy: $STRATEGY"
    echo "   Open trades: $TRADES"
elif echo "$STATUS_RESPONSE" | grep -q "\[\]"; then
    echo "⚠️  Status endpoint returns empty array - bot may not be fully initialized"
    echo "   This is normal when FreqTrade is starting up or stopped"
else
    echo "❌ Status endpoint failed"
    echo "   Response: $STATUS_RESPONSE"
fi

# Test profit endpoint
echo ""
echo "💰 Testing profit endpoint..."
PROFIT_RESPONSE=$(make_api_call "GET" "/api/v1/profit")
if echo "$PROFIT_RESPONSE" | grep -q "profit_all_coin"; then
    PROFIT=$(echo "$PROFIT_RESPONSE" | grep -o '"profit_all_coin":[0-9.-]*' | cut -d':' -f2)
    CURRENCY=$(echo "$PROFIT_RESPONSE" | grep -o '"stake_currency":"[^"]*"' | cut -d'"' -f4)
    echo "✅ Profit endpoint working!"
    echo "   Total profit: $PROFIT $CURRENCY"
else
    echo "❌ Profit endpoint failed"
    echo "   Response: $PROFIT_RESPONSE"
fi

# Interactive mode if no arguments provided for commands
if [ $# -eq 0 ] || [ "$4" = "interactive" ]; then
    echo ""
    echo "🎛️  Interactive mode:"
    echo "   Available commands:"
    echo "   - start: Start the trading bot"
    echo "   - stop: Stop the trading bot" 
    echo "   - status: Check bot status"
    echo "   - show_config: Show bot configuration"
    echo "   - trades: List open trades"
    echo "   - logs: Show recent logs via API"
    echo "   - docker_logs: Show live Docker container logs"
    echo "   - debug: Debug API endpoints"
    echo "   - quit: Exit"
    echo ""
    
    while true; do
        read -p "> " command
        
        case "$command" in
            "start")
                echo "🚀 Starting bot..."
                START_RESPONSE=$(make_api_call "POST" "/api/v1/start")
                if echo "$START_RESPONSE" | grep -q "status"; then
                    echo "✅ Bot started successfully!"
                else
                    echo "❌ Failed to start bot"
                    echo "   Response: $START_RESPONSE"
                fi
                ;;
            "stop")
                echo "🛑 Stopping bot..."
                STOP_RESPONSE=$(make_api_call "POST" "/api/v1/stop")
                if echo "$STOP_RESPONSE" | grep -q "status"; then
                    echo "✅ Bot stopped successfully!"
                else
                    echo "❌ Failed to stop bot"
                    echo "   Response: $STOP_RESPONSE"
                fi
                ;;
            "status")
                echo "📊 Checking status..."
                STATUS_RESPONSE=$(make_api_call "GET" "/api/v1/status")
                echo "   Raw response: $STATUS_RESPONSE"
                
                # Try alternative endpoints
                echo "   Trying /api/v1/show_config..."
                CONFIG_RESPONSE=$(make_api_call "GET" "/api/v1/show_config")
                if echo "$CONFIG_RESPONSE" | grep -q "strategy"; then
                    STRATEGY=$(echo "$CONFIG_RESPONSE" | grep -o '"strategy":"[^"]*"' | cut -d'"' -f4)
                    echo "   Strategy from config: $STRATEGY"
                fi
                
                echo "   Trying /api/v1/count..."
                COUNT_RESPONSE=$(make_api_call "GET" "/api/v1/count")
                echo "   Count response: $COUNT_RESPONSE"
                
                if echo "$STATUS_RESPONSE" | grep -q "state"; then
                    STATE=$(echo "$STATUS_RESPONSE" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
                    echo "   Bot state: $STATE"
                elif echo "$STATUS_RESPONSE" | grep -q "\[\]"; then
                    echo "   Bot state: Unknown (empty response - checking if bot is actually running)"
                    echo "   Check docker logs for more details"
                else
                    echo "❌ Status check failed"
                fi
                ;;
            "show_config")
                echo "⚙️  Showing bot configuration..."
                CONFIG_RESPONSE=$(make_api_call "GET" "/api/v1/show_config")
                echo "$CONFIG_RESPONSE"
                ;;
            "logs")
                echo "📝 Showing recent logs..."
                LOGS_RESPONSE=$(make_api_call "GET" "/api/v1/logs")
                if [ "$LOGS_RESPONSE" != "[]" ] && [ -n "$LOGS_RESPONSE" ]; then
                    echo "$LOGS_RESPONSE" | sed 's/\\n/\n/g' | sed 's/\\t/\t/g'
                else
                    echo "   No logs available via API, use: docker logs freqtrade"
                fi
                ;;
            "debug")
                echo "🔍 Debug mode - Testing various endpoints..."
                
                echo "1. /api/v1/ping:"
                curl -s "$BASE_URL/api/v1/ping"
                echo ""
                
                echo "2. /api/v1/version:"
                make_api_call "GET" "/api/v1/version"
                echo ""
                
                echo "3. /api/v1/status:"
                make_api_call "GET" "/api/v1/status"
                echo ""
                
                echo "4. /api/v1/count:"
                make_api_call "GET" "/api/v1/count"
                echo ""
                
                echo "5. /api/v1/balance:"
                make_api_call "GET" "/api/v1/balance"
                echo ""
                
                echo "6. /api/v1/trades:"
                make_api_call "GET" "/api/v1/trades"
                echo ""
                
                echo "7. /api/v1/available_pairs:"
                make_api_call "GET" "/api/v1/available_pairs"
                echo ""
                
                echo "8. /api/v1/whitelist:"
                make_api_call "GET" "/api/v1/whitelist"
                echo ""
                ;;
            "docker_logs")
                echo "📋 Showing live Docker logs (Press Ctrl+C to stop)..."
                docker logs -f freqtrade
                ;;
            "trades")
                echo "📈 Listing open trades..."
                TRADES_RESPONSE=$(make_api_call "GET" "/api/v1/status")
                echo "$TRADES_RESPONSE" | grep -o '"open_trades":\[[^]]*\]' || echo "   No open trades or error"
                ;;
            "quit"|"exit"|"q")
                echo "👋 Goodbye!"
                break
                ;;
            "")
                continue
                ;;
            *)
                echo "❓ Unknown command: $command"
                echo "   Use: start, stop, status, show_config, trades, logs, docker_logs, debug, quit"
                ;;
        esac
    done
fi

echo ""
echo "🏁 API test completed!"
