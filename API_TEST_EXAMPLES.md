# FreqTrade API Testing Examples

## Quick Tests (from within Docker network)

### 1. Basic Connectivity Test
```bash
curl -s http://freqtrade:8080/api/v1/ping
```

### 2. Authenticate and get token
```bash
# Get authentication token
TOKEN=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"freq","password":"abcdef"}' \
  http://freqtrade:8080/api/v1/token/login | \
  grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

echo "Token: $TOKEN"
```

### 3. Check Status (requires token)
```bash
curl -s -X GET \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://freqtrade:8080/api/v1/status | jq .
```

### 4. Start Bot
```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://freqtrade:8080/api/v1/start | jq .
```

### 5. Stop Bot
```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://freqtrade:8080/api/v1/stop | jq .
```

### 6. Get Version
```bash
curl -s -X GET \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://freqtrade:8080/api/v1/version | jq .
```

### 7. Get Profit Summary
```bash
curl -s -X GET \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://freqtrade:8080/api/v1/profit | jq .
```

### 8. List Open Trades
```bash
curl -s -X GET \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://freqtrade:8080/api/v1/status | jq '.open_trades'
```

## Testing from Host Machine (localhost)

Replace `http://freqtrade:8080` with `http://localhost:8080` in all commands above.

## One-liner Complete Test

```bash
# Complete test in one command
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"username":"freq","password":"abcdef"}' \
  http://freqtrade:8080/api/v1/token/login | \
  grep -o '"access_token":"[^"]*"' | cut -d'"' -f4 | \
  xargs -I {} curl -s -X GET \
  -H "Authorization: Bearer {}" \
  -H "Content-Type: application/json" \
  http://freqtrade:8080/api/v1/status
```

## Docker Command Examples

### Run from agent-zero container
```bash
# Enter the agent-zero container
docker exec -it agent-zero bash

# Then run the test script
./test_freqtrade_api.sh
```

### Run as standalone Docker command
```bash
# Test from host using docker run
docker run --rm --network rutger_agent-network \
  curlimages/curl:latest \
  curl -s http://freqtrade:8080/api/v1/ping
```

## PowerShell Examples (Windows)

### Get Token
```powershell
$response = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/token/login" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username":"freq","password":"abcdef"}'

$token = $response.access_token
```

### Check Status
```powershell
$headers = @{
  "Authorization" = "Bearer $token"
  "Content-Type" = "application/json"
}

Invoke-RestMethod -Uri "http://localhost:8080/api/v1/status" `
  -Method GET `
  -Headers $headers
```

## Troubleshooting

### Common Issues:

1. **Connection refused**: FreqTrade container is not running
   ```bash
   docker ps | grep freqtrade
   ```

2. **401 Unauthorized**: Wrong credentials or expired token
   - Check username/password in config
   - Get new token

3. **Network issues**: Wrong URL or network
   - From host: use `localhost:8080`
   - From Docker: use `freqtrade:8080`

4. **JSON parsing errors**: Install jq for better output
   ```bash
   # Alpine/Docker
   apk add jq
   
   # Ubuntu/Debian
   apt-get install jq
   ```
