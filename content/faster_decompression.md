Title: Decompression is up to 30% faster in CPython 3.15
Date: 2025-11-11
Tags: python, compression, zstd

> **tl;dr**<br>
> `compression.zstd` is the fastest Python Zstandard bindings with Python 3.15. Changes to code managing output
> buffers has led to a 25-30% performance uplift for Zstandard decompression and a 10-15% performance uplift for `zlib`
> for data at least 1 MiB in size. This has broad implications for e.g. faster wheel installations with pip and many
> other use cases.

## Motivation

Since [landing Zstandard support in CPython](https://peps.python.org/pep-0784/), I wanted to explore
the performance of CPython's compression modules to ensure they were well-optimized. Furthermore, the maintainer of
[pyzstd](https://github.com/Rogdham/pyzstd/) and [backports.zstd](https://github.com/Rogdham/backports.zstd) (a backport of
`compression.zstd` to Python versions before 3.14) benchmarked the new `compression.zstd` module against 3rd party Zstandard
Python bindings such as [pyzstd](https://github.com/Rogdham/pyzstd/),
[zstandard](https://github.com/indygreg/python-zstandard), and [zstd](https://github.com/sergey-dryabzhinsky/python-zstd),
and found the standard library was slower than most other bindings!

Let's take a closer look at [the benchmarks](https://github.com/Rogdham/zstd-benchmark/blob/master/results/2025-09-22_linux.md)
and how to read them:

>Figures give timing comparison. For example, +42% means that the library needs 42% more time than stdlib/backports.zstd.
>The reference time column indicates an average time for a single run.
>
>Emoji scale: ❤️‍🩹 -25% 🟥 -15% 🔴 -5% ⚪ +5% 🟢 +15% 🟩 +25% 💚

Okay, so hopefully we don't see a lot of red, meaning the reference standard library (stdlib) time is slower...

>## CPython 3.14.0rc3
>| Case                   | stdlib     | pyzstd       | zstandard    | zstd      |
>|------------------------|------------|--------------|--------------|-----------|
>| compress 1k level 3    | <1ms       | ⚪ - 3.81%    | ⚪ - 1.17%    | 🟢 + 5.86% |
>| compress 1k level 10   | <1ms       | ⚪ + 1.91%    | 🟢 + 6.18%    | 🟢 + 9.83% |
>| compress 1k level 17   | <1ms       | 🟢 + 6.33%    | 🟢 + 7.67%    | 🟢 +12.92% |
>| compress 1M level 3    | 7ms        | ⚪ + 0.60%    | 🔴 - 7.37%    | 🟢 +12.08% |
>| compress 1M level 10   | 27ms       | 🟢 +10.39%    | ⚪ + 3.39%    | 🟢 +12.46% |
>| compress 1M level 17   | 174ms      | ⚪ - 2.48%    | ⚪ - 3.91%    | ⚪ + 0.08% |
>| compress 1G level 3    | 6.03s      | 🟩 +16.17%    | ⚪ - 2.94%    | ⚪ + 2.25% |
>| decompress 1k level 3  | <1ms       | 🟥 -15.14%    | 🔴 - 8.53%    | ⚪ - 2.37% |
>| decompress 1k level 10 | <1ms       | 🟥 -15.41%    | 🔴 - 9.22%    | ⚪ - 3.35% |
>| decompress 1k level 17 | <1ms       | 🔴 -11.16%    | 🔴 - 7.09%    | ⚪ + 2.07% |
>| decompress 1M level 3  | 1ms        | 🔴 - 6.88%    | ⚪ - 4.03%    | 💚 +26.88% |
>| decompress 1M level 10 | 1ms        | 🔴 - 6.69%    | ⚪ - 4.86%    | 💚 +25.63% |
>| decompress 1M level 17 | 1ms        | 🔴 - 7.99%    | ⚪ - 4.96%    | 💚 +25.58% |
>| decompress 1G level 3  | 1.49s      | 🟥 -19.41%    | 🟥 -17.58%    | 🟢 + 6.98% |
>| decompress 1G level 10 | 1.62s      | ❤️‍🩹 -27.65%    | ❤️‍🩹 -26.48%    | 🔴 - 6.92% |
>| decompress 1G level 17 | 1.67s      | 🟥 -24.01%    | 🟥 -23.04%    | ⚪ - 4.43% |

Ouch. 10-25% slower is quite unfortunate! A silver lining is that most of the performance difference is in decompression,
so that narrows the area that is in need of optimization.

After sitting down and thinking about it for a while, I came up with a few theories as to why `compression.zstd` would
be slower compared to pyzstd and zstandard. My thinking was focused on noting differences in implementation I knew
existed between the various bindings. First, both pyzstd and zstandard build against their own copies of libzstd (the C
library implementing Zstandard compression and decompression). Meanwhile, CPython will build against the system-
installed libzstd, which is older on my system. Maybe there is a performance improvement in the newer libzstd
versions? Second, most of the performance difference is in decompression speed. Perhaps the implementation of
`compression.zstd.decompress()` is inefficient? It uses multiple decompression instances to handle multi-frame input
where pyzstd uses one, so perhaps that's the issue? Finally, maybe the handling of output buffers is slow? When
decompressing data, CPython needs to provide an output buffer (location in memory to write to) to store the
uncompressed data. If the creation/allocation of that output buffer is slow it could bottleneck the decompressor.

## Premature Optimizations

> These optimizations didn't work, so if you'd like to skip to the optimizations which worked, please move to the next
> section!

I decided to tackle these one at a time. First, I built pyzstd and zstandard against the system libzstd. Unfortunately,
after re-running the benchmark, this yielded zero performance difference. Darn.

Next, I was pretty confident that `compression.zstd.decompress()` was at least partially the culprit of the worse
performance. The [current `decompress()` implementation](https://github.com/python/cpython/blob/95f6e1275b1c9de550d978cb2b4351cc4ed24fe4/Lib/compression/zstd/__init__.py#L152-L172)
is written in Python and creates multiple decompression contexts and joins the results together. Surely that had to
lead to some performance degradation? I ended up re-implementing the `decompress()` function in C using a single
decompression context to see if my theory was correct. To my chagrin, there was no performance uplift, and it may have
even performed *worse*! For the curious, you can see [my hacked together branch here](https://github.com/emmatyping/cpython/tree/zstd-decompress-in-c).
Goes to show that you can never be sure about performance bottlenecks based on code itself!

## Properly Profiling CPython

With my first two attempts at optimizing Zstandard decompression in CPython unsuccessful, I realized that I should do
what I probably should have done from the beginning: profile the code! I decided to use the
[standard library support for the perf profiler](https://docs.python.org/3/howto/perf_profiling.html), as it would
allow me to see both native/C frames such as inside libzstd or the bindings module `_zstd`, as well as Python frames.

So I went ahead and compiled CPython [with some flags to improve perf data](https://docs.python.org/3/howto/perf_profiling.html#how-to-obtain-the-best-results)
and ran a simple script which called `compression.zstd.decompress()` on a variety of data sizes. I highly recommend
reading the Python documentation about perf support for more details but essentially what I ran was:

    :::bash
    # in a cpython checkout
    ./configure --enable-optimizations --with-lto CFLAGS="-fno-omit-frame-pointer -mno-omit-leaf-frame-pointer"
    make -j$(nproc)
    cd ../compression-benchmarks
    perf record -F 9999 -g -o perf.data ../cpython/python -X perf profile_zstd.py

After analyzing the profile with `perf report --stdio -n -g`, I noticed a significant bottleneck in the output buffer
management code! Let's take a brief detour to discuss what the output buffer management code does and why it was the
decompression bottleneck.

## (Fast) Buffer Handling is Hard

When decompressing data, you feed the decompressor (libzstd in our case) a buffer (`bytes` in Python) that is then
decompressed and needs to be written to a new buffer. Since this all happens in C, basically we need to allocate some
memory for libzstd to write the decompressed data into. But how much memory? Well, in many cases, we don't know! So we
need to dynamically resize the output buffer as it is filled up.

This is actually a pretty challenging problem because there are several constraints and considerations to be made. The
buffer management needs to be fast for a variety of output buffer sizes. If you allocate too much memory up front,
you'll waste time allocating unused memory and slow down decompressing small amounts of data. On the other hand, if you
don't allocate enough, you'll have to make a lot of calls to the allocator, which will also slow things down as each
allocation has overhead and leads to fragmenting the output data. The memory should not grow exponentially for large
outputs, otherwise you could run out of memory for tasks that would normally fit into memory. Finally, each output from
the decompressor can vary in size, given that it may need to buffer data internally.

Because of the complexity in managing an output buffer, there is code shared across compression modules in CPython to
manage the buffer. This code lives in
[pycore_blocks_output_buffer.h](https://github.com/python/cpython/blob/404425575c68bef9d2f042710fc713134d04c23f/Include/internal/pycore_blocks_output_buffer.h).
The code was [modified four years ago](https://github.com/python/cpython/commit/f9bedb630e8a0b7d94e1c7e609b20dfaa2b22231)
to use an implementation which writes to a series of `bytes` objects stored in a `list` to hold the output of
decompress calls. When finished, the bytes objects get concatenated together in `_BlocksOutputBuffer_Finish`,
returning the final `bytes` object containing the decompressed data. When profiling Zstandard decompression, I found
that greater than 50% (!) of decompression time was spent in `_BlocksOutputBuffer_Finish`! This seemed inordinately
long, ideally this function should just be a few `memcpy`s. So with this knowledge in hand, I tried to think of how
best to optimize the output buffer code.

## Sometimes Timing Works Out

Right around the time that I was working on this, [PEP 782](https://peps.python.org/pep-0782/) was accepted. This PEP
introduces a new `PyBytesWriter` API to CPython which makes it easier to incrementally build up `bytes` data in a safe
and performant way at the Python C API level. It seemed like a natural fit for what the blocks output buffer code was
doing, so I wanted to experiment with using it for the output buffer code. After modifying
`pycore_blocks_output_buffer.h` to use `PyBytesWriter`, I re-ran the original benchmark to see if we had closed the
performance gap:

> Note: this benchmark was run on my local machine and the wall times are not comparable to the previous benchmark.
>
>| Case                   | stdlib     | zstandard   |
>|------------------------|------------|-------------|
>| compress 1k level 3    | <1ms       | 💚 +61.02%   |
>| compress 1k level 10   | <1ms       | 💚 +57.77%   |
>| compress 1k level 17   | <1ms       | 💚 +364.86%  |
>| compress 1M level 3    | 5ms        | 💚 +40.02%   |
>| compress 1M level 10   | 32ms       | ⚪ - 0.99%   |
>| compress 1M level 17   | 126ms      | 🟩 +15.93%   |
>| compress 1G level 3    | 4.47s      | 💚 +48.69%   |
>| decompress 1k level 3  | <1ms       | ⚪ + 4.67%   |
>| decompress 1k level 10 | <1ms       | ⚪ + 4.79%   |
>| decompress 1k level 17 | <1ms       | 🟢 + 5.38%   |
>| decompress 1M level 3  | 1ms        | 💚 +50.23%   |
>| decompress 1M level 10 | 1ms        | 💚 +41.94%   |
>| decompress 1M level 17 | 1ms        | 💚 +47.37%   |
>| decompress 1G level 3  | 1.80s      | 🟢 +12.87%   |
>| decompress 1G level 10 | 1.77s      | 🟢 +12.54%   |
>| decompress 1G level 17 | 1.80s      | 🟢 + 8.76%   |


WOW! Not only have we closed the gap, `compression.zstd` is now *faster* than the popular zstandard 3rd-party module.

## Validating Our Results

Wanting to validate the speedup, I decided to write up my own minimal benchmark suite at this point too, to compare
between revisions of the standard library code and use [`pyperf`](https://pyperf.readthedocs.io/en/latest/),
a benchmarking toolkit used in the venerable [pyperformance benchmark suite](https://github.com/python/pyperformance).

So I went ahead and wrote up a [benchmark for zstd](https://github.com/emmatyping/compression-benchmarks/blob/fab8806f3af89b369e40e77be291dd37f3223b7c/bench_zstd.py)
which tests compression and decompression using default parameters for sizes 1 KiB, 1 MiB, and 1 GiB. I ran these
benchmarks on main and my branch which uses `PyBytesWriter`.

    :::
    zstd.compress(1K): Mean +- std dev: [main_zstd_3] 3.01 us +- 0.03 us -> [pybyteswriter_zstd_3] 3.00 us +- 0.03 us: 1.01x faster
    zstd.compress(1M): Mean +- std dev: [main_zstd_3] 2.92 ms +- 0.02 ms -> [pybyteswriter_zstd_3] 2.89 ms +- 0.02 ms: 1.01x faster
    zstd.compress(1G): Mean +- std dev: [main_zstd_3] 2.72 sec +- 0.01 sec -> [pybyteswriter_zstd_3] 2.67 sec +- 0.01 sec: 1.02x faster
    zstd.decompress(1K): Mean +- std dev: [main_zstd_3] 1.40 us +- 0.01 us -> [pybyteswriter_zstd_3] 1.38 us +- 0.01 us: 1.01x faster
    zstd.decompress(1M): Mean +- std dev: [main_zstd_3] 734 us +- 4 us -> [pybyteswriter_zstd_3] 546 us +- 3 us: 1.34x faster
    zstd.decompress(1G): Mean +- std dev: [main_zstd_3] 790 ms +- 4 ms -> [pybyteswriter_zstd_3] 634 ms +- 3 ms: 1.25x faster

    Geometric mean: 1.10x faster

For input sizes great than 1 MiB that's 25-30% faster decompression! In hindsight, this actually makes sense if you
consider that libzstd's decompression implementation is exceptionally fast.
[lzbench](https://github.com/inikep/lzbench), a popular compression library benchmark, found that libzstd can
decompress data at greater than 1 GiB/s. This is much faster than bz2, lzma, or zlib, the other compression modules in
the standard library. One of the motivations for adding Zstandard to CPython was it's performance. So it is not too
surprising that the output buffer code would be a bottleneck, given that the existing compression libraries don't write
as quickly to the output buffer. This also explains why compression isn't faster after changing the output buffer
code. Compression is very CPU intensive so more time is spent in the compressor rather than writing to the output
buffer. This also explains why the speedup is non-existent for decompressing 1 KiB of data - the first 32 KiB block that
is allocated is plenty to store all of the output data, meaning all of the time is spent in the decompressor.

One final validation I wished to do was to check the performance of `zlib`, to ensure that the change did not regress
performance for other standard library compression modules. I wrote
[a similar benchmark for zlib](https://github.com/emmatyping/compression-benchmarks/blob/fab8806f3af89b369e40e77be291dd37f3223b7c/bench_zlib.py)
to the one I wrote for zstd, and found that there was also a performance increase with the output buffer change!

    :::
    zlib.compress(1M): Mean +- std dev: [main] 13.5 ms +- 0.1 ms -> [pybyteswriter] 13.4 ms +- 0.0 ms: 1.00x faster
    zlib.compress(1G): Mean +- std dev: [main] 11.4 sec +- 0.0 sec -> [pybyteswriter] 11.3 sec +- 0.0 sec: 1.00x faster
    zlib.decompress(1K): Mean +- std dev: [main] 1.42 us +- 0.01 us -> [pybyteswriter] 1.39 us +- 0.01 us: 1.02x faster
    zlib.decompress(1M): Mean +- std dev: [main] 1.29 ms +- 0.00 ms -> [pybyteswriter] 1.17 ms +- 0.00 ms: 1.10x faster
    zlib.decompress(1G): Mean +- std dev: [main] 1.36 sec +- 0.00 sec -> [pybyteswriter] 1.17 sec +- 0.00 sec: 1.17x faster

    Benchmark hidden because not significant (1): zlib.compress(1K)

    Geometric mean: 1.05x faster

10-15% faster decompression on data of at least 1 MiB for zlib is pretty significant, especially when you consider that
zlib is used by pip to unpack files in almost every wheel package Python users install.

## Conclusion

With the improvements to output buffer handling, I was not only able to improve the performance of `compression.zstd`,
but all of the compression module's decompression code. After stumbling over a few optimization ideas, I definitely
learned my lesson to profile code before jumping to conclusions! You won't know what is a real bottleneck unless you
can test it! Just having a benchmark is not enough!

[The original issue I opened](https://github.com/python/cpython/issues/139877) goes into a bit more detail about the
process of benchmarking the compression modules, and [the commit with the improvement](https://github.com/python/cpython/commit/f262297d525e87906c5e4ab28e80284189641c9e)
has the diff of changes to adopt `PyBytesWriter`. One thing I'm proud of is that not only did the change improve
performance, it also simplifies the implementation of the output buffer code and removed 60 lines of code in the
process!

I did some more profiling of zlib to see if there were any more performance gains to be made, but the profile I
gathered seems to indicate that 95+% of the time is spent in zlib's inflate implementation (with the rest in the
CPython VM), so there is little if any room for further optimization in CPython's bindings for zlib. I think this
is good, as it indicates Python users are getting the best performance they can in 3.15!

Going forward, I am planning on profiling compression code more, but the vast majority of the time spent
there will probably be in the compressor since compression is so CPU intensive. Finally, I want to investigate
optimizations related to providing more information about the final size of the output data. In some cases the output
buffer is initialized to a small value and dynamically resized as output is produced, but ideally users would be able
to provide more information about their workflow and see a performance improvement over it. I have a lot of other ideas
related to compression I'd like to work on, check out [my OSS TODO list](https://notes.emmatyping.dev/share/ossTODO)
for all of the random ideas I want to work on in the future!
