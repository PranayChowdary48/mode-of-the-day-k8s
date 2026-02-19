import random
import datetime
import redis
from flask import Flask, render_template, jsonify, Response, request, g
import socket
import time
import os
from pythonjsonlogger import jsonlogger
import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest

app = Flask(__name__)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(levelname)s %(message)s %(container)s %(request_path)s'
)
logHandler.setFormatter(formatter)

logger.handlers = []
logger.addHandler(logHandler)


REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_latency_seconds",
    "Request latency",
    ["path", "method"]
)

ACTIVE_REQUESTS = Gauge(
    "http_requests_in_flight",
    "In-flight HTTP requests"
)

def require_basic_auth():
    user = os.getenv("REFRESH_USER")
    password = os.getenv("REFRESH_PASSWORD")
    if not user or not password:
        return False
    auth = request.authorization
    if not auth:
        return False
    return auth.username == user and auth.password == password

@app.before_request
def start_timer():
    g.start_time = time.perf_counter()
    ACTIVE_REQUESTS.inc()

@app.after_request
def record_metrics(response):
    REQUEST_COUNT.labels(
        request.method, request.path, response.status_code
    ).inc()
    if hasattr(g, "start_time"):
        REQUEST_LATENCY.labels(request.path, request.method).observe(
            time.perf_counter() - g.start_time
        )
    ACTIVE_REQUESTS.dec()
    return response

@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype="text/plain")

# Redis connection (host/port configurable for sidecar proxy)
redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_client = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True
)

MOODS = {
    "Happy": "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2FubWFtNDhxbDNsOTV6Z2ExbXdtYTdrZm9hOHd2bG44NjQ1eW5ldCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/fUQ4rhUZJYiQsas6WD/giphy.gif",
    "Sad": "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3NDF2cGVuZWs1bnVkNTVqdTFmYjdqamo4Ynd0bjVocHoxYjNoZWt5ayZlcD12MV9naWZzX3NlYXJjaCZjdD1n/2rtQMJvhzOnRe/giphy.gif",
    "Angry": "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3Nzh3ZWIxbnJianduaGhtbzl1ZGwxYnd3Y2E1eDV4ZDgxcmMzZWY3YSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/29bKyyjDKX1W8/giphy.gif",
    "Tired": "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExbGxpZzEwaXBzdjA1ZzN5dnFzdmZrem02ZzdpMXdudDR4Ynk3NXJqMCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Zsc4dATQgcBmU/giphy.gif",
    "Hungry": "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExcWF4ZXU3MmdidzZwZDF2bXRsZmRoNjFtbWV0YzdmYzF2YXIzOXZtNiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/jKaFXbKyZFja0/giphy.gif",
    "Proud": "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNDdhNXQyNXAxZm84ajI5eTNvNDR6YWR6Mnl0bDlndHFqc2t0MW95ciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/Vg2TAoPzDstzy/giphy.gif",
    "Love": "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3aTFyanZnNHg5NWprN2EzM3o2YjNzbmdlZG8zYm1iOWdjYzN4NGNhaiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/XtluHogie3wB2/giphy.gif",
}

def seconds_until_midnight():
    now = datetime.datetime.now()
    tomorrow = now + datetime.timedelta(days=1)
    midnight = datetime.datetime.combine(tomorrow.date(), datetime.time.min)
    return int((midnight - now).total_seconds())

@app.route("/")
def mood_of_the_day():
    today = datetime.date.today().isoformat()
    redis_key = f"mood:{today}"

    hostname = socket.gethostname()

    cached = redis_client.hgetall(redis_key)

    if cached:
        mood = cached["mood"]
        gif = cached["gif"]
        generated_at = cached["generated_at"]
        cache_status = "HIT"
    else:
        mood, gif = random.choice(list(MOODS.items()))
        generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        redis_client.hset(redis_key, mapping={"mood": mood, "gif": gif, "generated_at": generated_at})
        redis_client.expire(redis_key, seconds_until_midnight())
        cache_status = "MISS"
    
    logger.info(
        "mood_generated",
        extra={
            "container": hostname,
            "request_path": "/",
            "redis_key": redis_key,
            "cache_status": cache_status,
            "mood": mood
        }
    )

    return render_template("index.html", mood=mood, gif=gif, generated_at=generated_at, hostname=hostname)

@app.route("/refresh", methods=["POST"])
def refresh_mood():
    if not require_basic_auth():
        return Response(
            "Unauthorized",
            401,
            {"WWW-Authenticate": 'Basic realm="mood"'}
        )
    today = datetime.date.today().isoformat()
    redis_key = f"mood:{today}"

    hostname = socket.gethostname()

    # Invalidate cache
    redis_client.delete(redis_key)
    generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Generate new mood
    mood, gif = random.choice(list(MOODS.items()))
    redis_client.hset(redis_key, mapping={"mood": mood, "gif": gif, "generated_at": generated_at})
    redis_client.expire(redis_key, seconds_until_midnight())

    return jsonify({
        "mood": mood,
        "gif": gif,
        "generated_at": generated_at,
        "hostname": hostname
    })

@app.route("/whoami")
def whoami():
    return socket.gethostname()

@app.route("/health")
def health():
    try:
        redis_client.ping()
        return {"status": "ready"}, 200
    except Exception:
        return {"status": "not_ready"}, 503

@app.route("/live")
def live():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
