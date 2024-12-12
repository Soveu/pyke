import asyncio

class Target:
    def __init__(self, dependencies=None, name=None):
        if name is None:
            self.name = f"anonymous_{id(self)}"
        else:
            self.name = name

        if dependencies is None:
            self.dependencies = []
        else:
            self.dependencies = dependencies

    async def run(self):
        return True

class Command(Target):
    def __init__(self, args, dependencies=None, name=None):
        Target.__init__(self, dependencies, name)
        self.args = args

    async def run(self):
        #print(self.args)
        proc = await asyncio.create_subprocess_exec(
            self.args[0],
            *self.args[1:],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        return (await proc.wait()) == 0

# --------------

class AsyncTarget:
    def __init__(self, coro, name):
        self.name = name
        self.lock = asyncio.Lock()
        self.coro = coro
        self.has_value = False
        self.value = None

    async def get(self, state):
        async with self.lock:
            if not self.has_value:
                async with state.job_pool:
                    state.notify_build_start(self.name)
                    self.value = await self.coro

                state.notify_build_end(self.name)
                self.coro = None
                self.has_value = True

            return self.value

def _build_cache(target, cache):
    if target in cache:
        return

    for dep in target.dependencies:
        _build_cache(dep, cache)

    cache[target] = AsyncTarget(target.run(), target.name)

class BuildState:
    def __init__(self, root, jobs):
        self.root = root
        self.job_pool = asyncio.BoundedSemaphore(jobs)
        self.coroutines = dict()
        _build_cache(root, self.coroutines)

        self.currently_building = set()

    def notify_build_start(self, name):
        self.currently_building.add(name)
        print(f"Building {self.currently_building}")

    def notify_build_end(self, name):
        self.currently_building.discard(name)

async def __async_build(target, state):
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(__async_build(dep, state)) for dep in target.dependencies]

    if not all(tasks):
        return False

    return await state.coroutines[target].get(state)

def build(root):
    state = BuildState(root, 8)
    return asyncio.run(__async_build(root, state))

    
# --------------

import random

a = Target(
    dependencies = [
        Command(
            ["sleep", str(random.randint(1, 10) * 0.125)],
            name = f"sleep_a_{i}",
        ) for i in range(50)
    ],
    name = 'a',
)

b = Target(
    dependencies = [
        Command(
            ["sleep", str(random.randint(1, 10) * 0.125)],
            dependencies = [a],
            name = f"sleep_b_{i}",
        ) for i in range(40)
    ],
    name = 'b',
)

c = Target(
    dependencies = [
        Command(
            ["sleep", str(random.randint(1, 10) * 0.125)],
            dependencies = [a],
            name = f"sleep_c_{i}",
        ) for i in range(30)
    ],
    name = 'c',
)

d = Target(dependencies = [b, c], name='d')

e = Target(dependencies = [a, d], name='e')

print(build(e))
