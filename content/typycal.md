Title: Typycal - Generate type stubs from runtime type information
Date: 2017-07-26
Tags: typing, python

EDIT: This project stalled and is no longer being worked on. You can find the sources [on my github](https://github.com/emmatyping/typycal). The original blog is below.

Note: This blog post assumes basic familiarity with typing

I am a collaborator on the [mypy](http://mypy-lang.org) project, which implements a static type checker for Python. Static typing is useful for many reasons, such as making refactoring and other code maintenance easier. At PyCon this year, I heard from many developers using mypy who found it useful in understanding their code and finding type errors. Andreas Dewes gave a nice summary and analysis of typing in Python in a [Europython talk](https://www.slideshare.net/japh44/type-annotations-in-python-whats-whys-and-wows). I highly recommend it if you are just starting typing or are not convinced it is worth it to read the slides from that talk.

At the moment, several companies and open source projects have moved to using static typing, such as Dropbox, Google, and [Zulip](https://zulip.org/), an open source chat application. One of the design goals of static typing in Python is to be optional and gradual. However, even with these goals, annotating code, especially for large code bases, can be a significant time drain. With this in mind, I was interested in trying to make it easier for people to adopt typing in their Python code. Some work has been put into making a more advanced type inference tool that would be able to generate useful type information such as Google's [pytype](https://github.com/google/pytype) project and mypy's stubgen script. Google and Facebook both have their own closed source runtime type inferencers. However, pytype can be inaccurate and crash on valid code (which is bad if you want to adopt static typing). In addition it only runs on Python 2 (though it can check Python 3 code). Stubgen is rather incomplete, and will likely never be able to infer the most complex cases. These are useful tools, but I believe that runtime introspection can do better.

These solutions seemed overly complex when all the type information needed is right in front of us: in the running code itself! At the time I was thinking about this problem, I coincidentally had been reading up on [Pyjion](https://github.com/Microsoft/Pyjion) and [PEP 523: Adding a frame evaluation API to CPython](https://www.python.org/dev/peps/pep-0523/) when I realized I could use the new frame evaluation API to do runtime type introspection!

## So what is this frame evaluation API?

The frame evaluation API was introduced mainly for JIT (just in time) compilers, and debuggers (PyCharm uses it). However, I wanted to use it to analyze the types in frames. You may be asking yourself: what is a frame? A frame is a data structure that Python uses to describe scopes and information about that scope. The simplest to understand frame is a function:

    :::python
    def test():
        ...


Modules, functions, generators, and comprehensions have their own scope so they get their own frame. So when I call `os.path.abspath`(path), I am creating a new frame. The frame data is represented by a C struct in CPython (if you aren't familiar with C, just think of it like a Python class with some attributes). It contains information about the function called, such as its name (`abspath` in our example), its file path, and most importantly its locals. Locals is a symbol table (a mapping of names to values) for the scope of the frame. For example, in `abspath`, the `path` argument is a local. Consider the following:

    :::python
    def hello(name):
        msg = "Hello %s!"
        print(msg % name)


Both `name` and `msg` are locals in the `hello` frame.

The frame evaluation API allows us to inspect the values of `name` and `msg`. The important part of locals is that function arguments are in the locals of a frame. We can get the type of these objects and log the argument types of the frame. Then we can execute the frame (run the Python code) and capture the return value (and type) as well. Thus the full signature of the function for each call is available. Here is basically how the code works (Python equivalent of the C code in typycal).

    :::python
    def typycal_evalframe(frame: frameobject, exc: int):
        """
        frame is the current frame to be executed
        exc indicates whether an exception has been thrown calling the frame.
        """
        if exc:
            return _PyEval_EvalFrameDefault(frame, exc)  # execute the frame as normal, this function is part of Python's private C API
        else:
            code = frame.f_code  # this is the bytecode of the frame (stuff to be executed), and some other useful info
            name = code.co_name
            file_name = code.co_filename
            if whitelisted(file_name, name):  # ignore stdlib and generators/comprehensions
                locals = frame.f_locals  # a dict of locals. names are keys, objects are values
                argc = code.co_argcount  # number of arguments passed to the function
                ret = _PyEval_EvalFrameDefault(frame, exc)  # run the frame, store the return value for analysis
                serialize_types(file_name, name, locals, argc, ret)
                return ret
            else:
                return _PyEval_EvalFrameDefault(frame, exc)  # don't want to analyze this frame, so execute it as normal

    def hook():
        thread_state = thread_state_get() # Needed to tell Python to run our frame evaluation function, instead of the default
        thread_state.interp.eval_frame = typycal_evalframe  # assign our function to be called when a frame needs to be evaluated

    def unhook():
        thread_state = thread_state_get()
        thread_state.interp.eval_frame = _PyEval_EvalFrameDefault(frame, exc)


The `serialize_types` function just takes the Python object and generates PEP 484 compliant type data that is written to a file. You can call the hook from your code:

    :::python
    import typycal
    typycal.hook()
    ... # your code here


The hook will be put in place and typycal will be able to introspect frames, no decorators needed! We now have a means to serialize the type of the current frame! But how to get to *.pyi files?

## Building *.pyi files

With this information logged, one can then run a Python program (part of typycal) to analyze the signatures and generate stub files. The hope is that companies and individuals will be able to run typycal on their source via unit tests or other uses, and come out with stubs that are a basis to typing their entire code. Currently typycal is implemented in C++, both to interop with CPython well and to be fast. It is rather unoptimized, and causes the execution of 12 million frames to slow by roughly 5x, which is obviously not ideal. Most of the slowness comes from checking if a frame should be analyzed. To not greatly burden I/O and keep the serialized data as minimal as possible, we want to exclude the standard library, which can add millions of frames to a medium sized code base. I have a few plans to reduce the time spent on I/O and other optimizations in mind.

Since getting type information for all types gets very complex, typycal for now handles `int`, `str`, `tuple`, `list`, `callable`s, and `None`. `dict` should be relatively straightforward too. All other types will likely be `Any`'d since they may not be safe to put in a stub. This will likely change with time.

## The future

I plan on spending the rest of the summer improving typycal to work decently well to the point that I can release it publicly. If you are are interested in getting a look at the library to play with, feel free to contact me, and I will consider sharing it. I also will be discussing this project and static typing in general at PyBay on August 11, and would be happy to answer questions in person.
