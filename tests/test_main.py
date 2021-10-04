from string import ascii_lowercase, digits

import asyncstdlib as a
import pytest
from async_asgi_testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

import src.main
from src.main import ADMIN_PASSWORD, ADMIN_USERNAME, app

src.main.DB_TABLE = "test_database"
DB_TABLE = src.main.DB_TABLE


async def drop_table(connection):
    await connection.execute(
        f"""
        DROP TABLE IF EXISTS {DB_TABLE};
    """
    )


src.main.drop_table = drop_table


def assert_json(response, json_answer):
    assert response.status_code == 200
    assert response.json() == json_answer


@a.lru_cache
@pytest.fixture
def admin_params():
    return {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
        "rights": "1",
        "enabled": "1",
    }


async def create_user_template(params):
    async with TestClient(app) as ac:
        response = await ac.get("/create_user_by_get", query_string=params)
    assert_json(response, params)


# Is it reasonable?
@st.composite
def user_params_dict(
    draw,
    username=st.text(ascii_lowercase + digits, min_size=5, max_size=45),
    password=st.text(ascii_lowercase + digits, min_size=5, max_size=45),
    rights=st.sampled_from(["0", "1"]),
    enabled=st.sampled_from(["0", "1"]),
):
    return {
        "username": draw(username),
        "password": draw(password),
        "rights": draw(rights),
        "enabled": draw(enabled),
    }


@pytest.mark.asyncio
async def test_root(admin_params):
    async with TestClient(app) as ac:
        response = await ac.get("/")
    assert_json(response, admin_params)


@pytest.mark.asyncio
async def test_create_admin(admin_params):
    await create_user_template(admin_params)


@pytest.mark.asyncio
@given(user_params_dict())
@settings(max_examples=50, deadline=None)
async def test_create_user(user_params):
    await create_user_template(user_params)
