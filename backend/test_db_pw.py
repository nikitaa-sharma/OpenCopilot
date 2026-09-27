import asyncio
import asyncpg

passwords = ['postgres', 'root', 'admin', 'password', '1234', '123456', '12345678', 'Nikita', 'nikita', '', 'opencopilot']

async def try_passwords():
    for p in passwords:
        for db in ['opencopilot', 'postgres']:
            try:
                conn = await asyncpg.connect(host='127.0.0.1', port=5432, user='postgres', password=p, database=db, timeout=2)
                print(f'SUCCESS! password="{p}", db="{db}"')
                await conn.close()
                return
            except asyncpg.InvalidPasswordError:
                pass
            except Exception as e:
                print(f'Error with {p}/{db}: {e}')
    print('None of the common passwords worked on 127.0.0.1:5432')

asyncio.run(try_passwords())
