# import asyncpg
#
#
# async def get_user_by_username(pool, username):
#     async with pool.acquire() as connection:
#         async with connection.transaction():
#             result = await connection.fetchrow(
#                 f"SELECT * FROM {DB_TABLE} WHERE username = $1", username
#             )
#             return dict(result)