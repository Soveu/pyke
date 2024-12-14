import asyncio

# --------------

import compiler.c
import dataclasses

class CombineIntOrBoolException(Exception):
    pass

class CombineDictException(Exception):
    pass

class CombineFieldException(Exception):
    def __init__(self, class_name, field, e):
        self.class_name = class_name
        self.field = field
        self.e = e

def _combine_field(a, b, name):
    try:
        return combine(getattr(a, name), getattr(b, name))
    except e:
        raise CombineFieldException(type(a), name, e) from None

def combine(a, b):
    if a is None:
        return b

    if b is None:
        return a

    #if isinstance(a, Exception) and isinstance(b, Exception):
    #    return Exception((a, b))
    #if isinstance(a, Exception):
    #    return a
    #if isinstance(b, Exception):
    #    return b

    if type(a) != type(b):
        raise Exception("must be the same type or None")

    if a == b:
        return a

    if isinstance(a, set):
        return a | b

    if isinstance(a, dict):
        result = a | b
        rev = b | a

        if result != rev:
            keys = set(a.keys()) & set(b.keys())
            diff = {
                key: (a[key], b[key])
                for key in keys if a[key] != b[key]
            }

            raise CombineDictException(diff)

        return result

    if isinstance(a, list):
        return a + b

    if isinstance(a, bool) or isinstance(a, int):
        raise CombineIntOrBoolException((a, b))

    if not dataclasses.is_dataclass(a):
        # return a.combine(b) - maybe?
        raise Exception("complex type")

    construct_dict = {
        f.name: _combine_field(a, b, f.name)
        for f in dataclasses.fields(a)
    }
    return type(a)(**construct_dict)

flags1 = compiler.c.Flags(
    opt_level = 3,
    lang_version = compiler.c.LanguageVersion.C23,
    warnings_as_errors = True,
    definitions = {
        "BUILD_DATE": "2024-12-24-21:40",
        "CURRENT_TARGET": "x86_64-unknown-linux-gnu",
    },
    include_directories = {"/flags1/include/path"},
)

flags2 = compiler.c.Flags(
    #warnings_as_errors=Exception("AAAA"),
    #warnings_as_errors=False,
    #definitions = {"CURRENT_TARGET": "amd64-unknown-linux-gnu"},
    include_directories = {"/flags2/path/to/include"},
)

flags = combine(flags1, flags2)

print(flags.to_args())

# --------------

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

#print(build(e))
