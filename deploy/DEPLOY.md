# Deploying SkillBridge (free: Oracle Cloud Always Free)

The stack runs on one VM with Docker Compose:

| Service | What it does |
|---|---|
| `web` | Caddy: serves the React build, proxies `/api` to Flask, automatic HTTPS (Let's Encrypt) |
| `api` | Flask under gunicorn (1 process, 8 threads) |
| `worker` | `job_worker.py`: the two-hour job sync |
| `db` | PostgreSQL 16 |

Why Oracle: the sentence-transformers model needs about 1 GB of RAM. The free plans on Render and Koyeb have 512 MB, and Railway and Fly.io no longer have free plans. Oracle's Always Free ARM VM (up to 4 cores and 24 GB RAM) has no time limit and doesn't sleep.

## 1. Create the server (about 20 minutes, one time)

1. Sign up at <https://www.oracle.com/cloud/free/>. Oracle asks for a card to verify your identity and doesn't charge it on Always Free resources. Choose a home region near your users (e.g. Mumbai or Hyderabad); you can't change it later.
2. **Compute → Instances → Create instance**
   - Image: **Ubuntu 24.04**
   - Shape: **Ampere VM.Standard.A1.Flex**, 2 OCPU, 12 GB RAM (stays within the free limits)
   - Download the SSH private key Oracle offers.
   - If it says "out of capacity", try another availability domain, or try again later.
3. **Networking → the instance's subnet → Security list → Add ingress rules:** TCP 80 and TCP 443 from `0.0.0.0/0`.
4. Get a free hostname at <https://www.duckdns.org> (e.g. `skillbridge-xyz.duckdns.org`) and point it at the instance's public IP.

## 2. Prepare the VM

```sh
ssh -i <your-key>.key ubuntu@<public-ip>

# Ubuntu images on Oracle block 80/443 in iptables as well:
sudo iptables -I INPUT 6 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
sudo apt-get update && sudo apt-get install -y iptables-persistent && sudo netfilter-persistent save

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu && exit     # log in again afterwards
```

## 3. Deploy

```sh
git clone https://github.com/AYSHA-GITT/skillbridge.git && cd skillbridge/deploy
cp production.env.example production.env && chmod 600 production.env
openssl rand -hex 32   # run twice: once for SECRET_KEY, once for POSTGRES_PASSWORD
nano production.env    # SITE_DOMAIN, both secrets, mail settings, NEW API keys

docker compose --env-file production.env up -d --build      # first build takes 10-15 min
docker compose --env-file production.env exec api flask --app app db stamp head
docker compose --env-file production.env exec api flask --app app skills seed-questions
```

`db stamp head` records that the fresh schema (created by `db.create_all()` at start-up) is already at the latest migration. Run it **only on the first deploy**.

Open `https://<SITE_DOMAIN>`. The certificate is issued on the first request.

## 4. Create the admin account

Register through the site with your own email and a strong password, then:

```sh
docker compose --env-file production.env exec api flask --app app users make-admin you@example.com
```

There is no default admin in production. Don't recreate `admin@skillbridge.edu` / `admin123`.

## 5. Backups

```sh
chmod +x ~/skillbridge/deploy/backup.sh
crontab -e     # add:  30 2 * * * /home/ubuntu/skillbridge/deploy/backup.sh >> /home/ubuntu/backup.log 2>&1
```

Copy `~/skillbridge-backups` off the server now and then. If the VM is lost, the backups go with it.

## Updating after a new push

```sh
cd ~/skillbridge && git pull
cd deploy && docker compose --env-file production.env up -d --build
docker compose --env-file production.env exec api flask --app app db upgrade
```

## Useful commands

```sh
docker compose --env-file production.env ps
docker compose --env-file production.env logs -f api worker
docker compose --env-file production.env exec api flask --app app jobs status
```

## Before inviting real users

- [ ] Email works: `docker compose --env-file production.env exec api flask --app app users test-email you@example.com`, then request a password reset for your own account. In production the reset link is only ever sent by email, never shown on screen or written to the logs. If email isn't configured, the API logs an error at start-up and reset requests send nothing. For port 465, set `MAIL_PORT=465` and `MAIL_USE_SSL=true`.
- [ ] All API keys are new ones made for production. The GitHub token on your laptop has expired.
- [ ] Backups run, and you have restored one once (`pg_restore -U skillbridge -d skillbridge --clean`).
- [ ] The salary table is still illustrative data. Label it as such, or replace it.
