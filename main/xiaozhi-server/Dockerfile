FROM kalicyh/uv:v3.10_xiaozhi

WORKDIR /opt/xiaozhi-esp32-server

COPY main/xiaozhi-server/ .

RUN uv sync

CMD ["uv", "run", "app.py"]