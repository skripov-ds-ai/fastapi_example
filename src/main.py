from typing import Optional

import asyncpg
import uvicorn

# import strawberry
# from strawberry.asgi import GraphQL

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException


DB_HOST = "localhost"
DB_DATABASE = "postgres"
DB_USER = "fastapi_example"
DB_PASSWORD = "password"
DB_TABLE = "users"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "some_password"


# @strawberry.type
# class UserModel:
#     rights: str
#     enabled: str
#     username: str
#     password: str


async def init_pool():
    return await asyncpg.create_pool(
        host=DB_HOST,
        database=DB_DATABASE,
        user=DB_USER,
        password=DB_PASSWORD,
    )


async def drop_table(connection):
    pass


async def create_table(connection):
    await connection.execute(
        f"""CREATE TABLE IF NOT EXISTS {DB_TABLE} (
            username varchar(45) NOT NULL,
            password varchar(45) NOT NULL,
            rights varchar(1) NOT NULL DEFAULT '1',
            enabled varchar(1) NOT NULL DEFAULT '1',
            PRIMARY KEY (username)
        )"""
    )


async def create_admin_user(connection):
    await connection.execute(
        f"""INSERT INTO {DB_TABLE}(username, password) 
                VALUES($1, $2) 
                ON CONFLICT (username) 
                DO UPDATE SET password = $2;""",
        ADMIN_USERNAME,
        ADMIN_PASSWORD,
    )


async def get_db():
    pool = await init_pool()
    async with pool.acquire() as connection:
        await drop_table(connection)
        await create_table(connection)
        await create_admin_user(connection)
    return pool


app: FastAPI = FastAPI()
db: Optional[asyncpg.Pool] = None
templates = Jinja2Templates(directory="templates")
# schema = strawberry.Schema(query=UserModel)
# graphql_app = GraphQL(schema)
# app.add_route("/graphql", graphql_app)
# app.add_websocket_route("/graphql", graphql_app)


async def get_pool() -> asyncpg.Pool:
    global db
    if not db:
        db = await get_db()
    return db


@app.on_event("startup")
async def startup():
    pass


@app.on_event("shutdown")
async def shutdown():
    global db
    if db:
        await db.close()
        db = None


async def get_user_by_username(connection, username):
    async with connection.transaction():
        result = await connection.fetchrow(
            f"SELECT * FROM {DB_TABLE} WHERE username = $1", username
        )
        return dict(result)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")


@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request, pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as connection:
        user = await get_user_by_username(connection, "admin")
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    return templates.TemplateResponse("404.html", {"request": request})


@app.get("/api/home")
async def homepage(pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as connection:
        return await get_user_by_username(connection, "admin")


@app.get("/api/create_user_by_get")
async def create_user_by_get(
    username: str,
    password: str,
    rights: str = "0",
    enabled: str = "0",
    pool: asyncpg.Pool = Depends(get_pool),
):
    if rights not in ["0", "1"]:
        raise HTTPException(
            status_code=410, detail="Incorrect `rights` parameter value"
        )
    if enabled not in ["0", "1"]:
        raise HTTPException(
            status_code=410, detail="Incorrect `enabled` parameter value"
        )

    async with pool.acquire() as connection:
        await connection.execute(
            f"""INSERT INTO {DB_TABLE}(username, password, rights, enabled)
            VALUES($1, $2, $3, $4)
            ON CONFLICT (username)
            DO NOTHING;""",
            username,
            password,
            rights,
            enabled,
        )
        return await get_user_by_username(connection, username)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
