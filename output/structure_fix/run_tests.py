import asyncio, threading, pathlib, os, sys, unittest
root=pathlib.Path(__file__).resolve().parents[2]
os.chdir(root); sys.path.insert(0,str(root))
os.environ.update(DB_HOST='127.0.0.1',DB_PORT='3307',RUN_MYSQL_TESTS='1')
ready=threading.Event()
async def proxy(r,w):
    rr,ww=await asyncio.open_connection('127.0.0.1',3306)
    async def pipe(a,b):
        try:
            while data:=await a.read(65536):
                b.write(data); await b.drain()
        except (ConnectionError,OSError): pass
        finally: b.close()
    await asyncio.gather(pipe(r,ww),pipe(rr,w))
async def serve():
    server=await asyncio.start_server(proxy,'127.0.0.1',3307)
    ready.set()
    async with server: await server.serve_forever()
threading.Thread(target=lambda:asyncio.run(serve()),daemon=True).start()
assert ready.wait(10)
with (root/'output/structure_fix/test-results.txt').open('w') as log:
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover('tests'))
print(f'Tests {result.testsRun}; failures {len(result.failures)}; errors {len(result.errors)}; skipped {len(result.skipped)}')
sys.exit(not result.wasSuccessful() or bool(result.skipped))
