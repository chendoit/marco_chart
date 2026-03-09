# Flask Highcharts 應用

這是一個使用 Flask 和 Highcharts 構建的數據可視化應用，支持 Cloudflare Turnstile 驗證。

## 環境配置

應用程序支持通過環境變量進行配置，使同一份代碼可以在本地開發和生產環境中使用不同的設置。

### 設置環境變量

1. 複製 `.env.example` 文件為 `.env`：

```bash
cp .env.example .env
```

2. 根據需要修改 `.env` 文件中的設置：

```
# 環境類型: development 或 production
FLASK_ENV=development

# Cloudflare Turnstile 配置 (僅在 FLASK_ENV=production 時需要設置)
CF_TURNSTILE_SECRET_KEY=your_secret_key
CF_TURNSTILE_SITE_KEY=your_site_key

# Session 密鑰
SECRET_KEY=your_secure_random_string

# 驗證有效期（小時）
VERIFICATION_VALID_HOURS=24
```

### 環境變量說明

- `FLASK_ENV`: 設置環境類型，影響端口選擇、調試模式和 Turnstile 驗證
  - `development`: 使用開發環境設置（端口 6002，啟用調試模式，使用測試密鑰並自動跳過驗證）
  - `production`: 使用生產環境設置（端口 5002，禁用調試模式，使用實際密鑰並啟用驗證）

- `CF_TURNSTILE_SECRET_KEY`: Cloudflare Turnstile 密鑰
  - 當 `FLASK_ENV=development` 時，自動使用測試密鑰 `1x0000000000000000000000000000000AA`
  - 當 `FLASK_ENV=production` 時，使用此環境變量設置的實際密鑰

- `CF_TURNSTILE_SITE_KEY`: Cloudflare Turnstile 站點密鑰
  - 當 `FLASK_ENV=development` 時，自動使用測試站點密鑰 `1x00000000000000000000AA`
  - 當 `FLASK_ENV=production` 時，使用此環境變量設置的實際站點密鑰

- `SECRET_KEY`: 用於加密 session 的密鑰
  - 如果未設置，將自動生成隨機密鑰（每次重啟應用程序時會變更）
  - 在生產環境中應設置為固定值，以確保重啟後 session 仍然有效

- `VERIFICATION_VALID_HOURS`: 驗證有效期（小時）
  - 默認為 24 小時
  - 可根據需要調整

## 運行應用

```bash
python main.py
```

應用將根據環境變量設置啟動，並在控制台顯示當前配置信息。