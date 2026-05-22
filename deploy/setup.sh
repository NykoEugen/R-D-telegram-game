#!/bin/bash
# Oracle Cloud Ubuntu 22.04 — initial server setup for telegram game bot
# Usage: bash setup.sh your-subdomain.duckdns.org YOUR_DUCKDNS_TOKEN

set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain> <duckdns_token>}"
DUCKDNS_TOKEN="${2:?Usage: $0 <domain> <duckdns_token>}"
EMAIL="admin@${DOMAIN}"

echo "=== 1. System update ==="
sudo apt-get update && sudo apt-get upgrade -y

echo "=== 2. Install Docker ==="
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker "$USER"

echo "=== 3. Install Nginx + Certbot ==="
sudo apt-get install -y nginx certbot python3-certbot-nginx

echo "=== 4. Configure firewall ==="
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Oracle Cloud also requires iptables rules (their VCN firewall is separate)
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save 2>/dev/null || true

echo "=== 5. DuckDNS cron (update IP every 5 min) ==="
DUCKDNS_SUBDOMAIN="${DOMAIN%.duckdns.org}"
mkdir -p ~/duckdns
cat > ~/duckdns/duck.sh <<EOF
#!/bin/bash
echo url="https://www.duckdns.org/update?domains=${DUCKDNS_SUBDOMAIN}&token=${DUCKDNS_TOKEN}&ip=" | curl -k -o ~/duckdns/duck.log -K -
EOF
chmod +x ~/duckdns/duck.sh
(crontab -l 2>/dev/null; echo "*/5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1") | crontab -
~/duckdns/duck.sh
echo "DuckDNS updated: $(cat ~/duckdns/duck.log)"

echo "=== 6. Nginx initial config (HTTP for certbot challenge) ==="
sudo tee /etc/nginx/sites-available/telegram-bot <<EOF
server {
    listen 80;
    server_name ${DOMAIN};
    location / {
        return 200 'ok';
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/telegram-bot /etc/nginx/sites-enabled/telegram-bot
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

echo "=== 7. Let's Encrypt SSL ==="
sudo certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos -m "${EMAIL}" --redirect

echo "=== 8. Nginx final config (HTTPS proxy to bot) ==="
sudo tee /etc/nginx/sites-available/telegram-bot <<EOF
server {
    listen 80;
    server_name ${DOMAIN};
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name ${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location /webhook {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        return 404;
    }
}
EOF
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "=== Done! ==="
echo "Server is ready. Now:"
echo "  1. Clone the repo to ~/r-d-telegram-game"
echo "  2. Create .env based on .env.production.example"
echo "  3. Run: cd ~/r-d-telegram-game && docker compose -f docker-compose.prod.yml up -d"
echo "  4. Run migrations: docker compose -f docker-compose.prod.yml exec bot python -m alembic upgrade head"
echo ""
echo "Bot webhook URL: https://${DOMAIN}/webhook"
