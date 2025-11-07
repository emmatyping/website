Title: Finding a miscompilation in Rust/LLVM
Date: 2025-10-14
Tags: python, rust, compression

Among my friends I have a reputation for ~~causing~~ stumbling across esoteric error messages. Whether that is `SSL read: I/O error: Success` (caused by a layered SSH connection hangup on Windows), or that time I tried installing NixOS on my laptop and `os-prober` failed to start (this was several years ago, so I am sure it is no longer an issue). I attribute these oddities to my curiosity, particularly around trying things that may or may not work and seeing if they do. Recently, I was trying to complete an item from [my OSS TODO list](https://notes.emmatyping.dev/share/ossTODO) when I came across a bug that stumped me for several days. Turns out sometimes even compilers have bugs...

My goal was to build CPython with Rust implementations of common compression libraries to see if the Rust libraries could be supported. **C**Python relies on **C** code to do many performance sensitive activities such as [`math`](https://docs.python.org/3.14/library/math.html) and [`compression`](https://docs.python.org/3.14/library/compression.html). I had recently read about the [Trifecta Tech Foundation](https://trifectatech.org/)'s initiative to re-write popular compression libraries in Rust. So far as of September 2025, they have pure-Rust re-implementations of [zlib](https://github.com/trifectatechfoundation/zlib-rs) (the library used for zip and gzip files), and [bzip2](https://github.com/trifectatechfoundation/libbzip2-rs) that are available for use.

These Rust libraries not only bring increased memory safety, they're also [as fast or faster than their C counter-parts](https://trifectatechfoundation.github.io/zlib-rs-bench/). Additionally, zlib-rs is widely deployed in Firefox, to the point that it may have [tripped over a CPU hardware bug(!)](https://github.com/trifectatechfoundation/zlib-rs/issues/306). So I had confidence that at least zlib-rs would work out of the box.

To add support for these libraries to CPython, I made [a branch with changes to the autoconf script](https://github.com/emmatyping/cpython/tree/build-with-rust-compression-libs) to search for the Rust libraries through `pkg-config`. I built [zlib-rs's C library](https://github.com/trifectatechfoundation/zlib-rs/tree/main/libz-rs-sys-cdylib) with `RUSTFLAGS="-Ctarget-cpu=native"` for maximum speed, and then pointed CPython's build process to the built zlib_rs library. Everything built just fine. Next, I wanted to run the CPython zlib test suite to verify zlib-rs was working correctly. I mostly did this to make sure I had built things properly, I had no doubts the tests would pass.

![A screenshot of test failures. The test_wbits and test_combine_no_iv tests in test_zlib failed.]({static}/static/zlib_test_failure.png)

And yet. I was shocked! zlib-rs is used in Firefox, cargo, and many other widely used tools and applications. Hard to believe it would have a glaring bug that would be surfaced by CPython's test suite. At first I assumed I had somehow made a mistake when building. I realized I had used my system zlib header when building, so maybe there was some weirdness with symbol compatibility?? No, re-building CPython pointing to the zlib-rs include directory didn't fix it.
I tried running `cargo test` in the zlib-rs directory to make sure there wasn't something wrong I could catch there. No failures occurred.

At this point I was convinced it was probably a bug with how I was building things, or a bug in the cdylib (Rust lingo for "C library") wrapping zlib-rs since test Rust tests passed but the tests in CPython failed. To make my testing simpler, I captured the state of the [`test_zlib.test_combine_no_iv` test](https://github.com/python/cpython/blob/c50d794c7bb81f31d1b977e63d0faba0b926a168/Lib/test/test_zlib.py#L169-L174) using PDB and wrote a C program which does the same thing as the test, with deterministic inputs:

    :::C
    #include <stdio.h>
    #include <string.h>
    #include "zlib.h"

    int main()
    {
        unsigned char a[32] = {0x88, 0x64, 0x15, 0xce, 0x5e, 0x3b, 0x8d, 0x35,
                            0xdb, 0xd2, 0xb5, 0xfa, 0x8e, 0xa7, 0x73, 0x10,
                            0x66, 0x83, 0x1b, 0xd1, 0xde, 0x0f, 0x25, 0x86,
                            0xeb, 0xe5, 0x42, 0x44, 0xad, 0x62, 0xff, 0x11};
        uInt chk_a = crc32(0, a, 32);
        unsigned char b[64] = {0x31, 0xb8, 0xce, 0x94, 0x4d, 0x2b, 0xb9, 0x7e,
                            0xd5, 0x81, 0x7f, 0xc2, 0x40, 0xbf, 0x3d, 0xa5,
                            0x25, 0xa5, 0xf9, 0xdf, 0x53, 0x68, 0xc4, 0xf6,
                            0xbe, 0x06, 0x7d, 0xf3, 0xc7, 0xdc, 0x5b, 0x84,
                            0xce, 0xd2, 0xb2, 0xeb, 0x87, 0x62, 0x60, 0xe3,
                            0x10, 0x05, 0x64, 0x59, 0x15, 0xc4, 0x2d, 0x78,
                            0xc8, 0xf3, 0x14, 0x38, 0x87, 0x39, 0xb3, 0x58,
                            0xb5, 0x95, 0x07, 0x25, 0xd9, 0xc1, 0xac, 0x04};
        uInt chk_b = crc32(0, b, 64);
        unsigned char buff[96];
        memcpy(buff, a, 32);
        memcpy(buff + 32, b, 64);
        uInt chk = crc32(0, buff, 96);
        uInt chk_combine = crc32_combine(chk_a, chk_b, 64);
        printf("chk (%u) = chk_combine (%u)? %s\n", chk, chk_combine, chk == chk_combine ? "True" : "False");
        return (0);
    }

This program also failed. Hm, okay, not an issue with CPython at least. I then translated the above test into Rust to add to the zlib-rs test suite, since the Rust tests passed. If it failed I could more easily debug the issue.

    :::diff
    diff --git a/zlib-rs/src/crc32/combine.rs b/zlib-rs/src/crc32/combine.rs
    index 40e3745..65c0143 100644
    --- a/zlib-rs/src/crc32/combine.rs
    +++ b/zlib-rs/src/crc32/combine.rs
    @@ -66,6 +66,26 @@ mod test {

        use crate::crc32;

    +    #[test]
    +    fn test_crc32_combine_no_iv() {
    +        for _ in 0..1000 {
    +            let a: &[u8] = &[0x88, 0x64, 0x15, 0xce, 0x5e, 0x3b, 0x8d, 0x35, 0xdb, 0xd2, 0xb5, 0xfa, 0x8e, 0xa7, 0x73, 0x10, 0x66, 0x83, 0x1b, 0xd1, 0xde, 0x0f, 0x25, 0x86, 0xeb, 0xe5, 0x42, 0x44, 0xad, 0x62, 0xff, 0x11];
    +            let b: &[u8] = &[0x31, 0xb8, 0xce, 0x94, 0x4d, 0x2b, 0xb9, 0x7e, 0xd5, 0x81, 0x7f, 0xc2, 0x40, 0xbf, 0x3d, 0xa5, 0x25, 0xa5, 0xf9, 0xdf, 0x53, 0x68, 0xc4, 0xf6, 0xbe, 0x06, 0x7d, 0xf3, 0xc7, 0xdc, 0x5b, 0x84, 0xce, 0xd2, 0xb2, 0xeb, 0x87, 0x62, 0x60, 0xe3, 0x10, 0x05, 0x64, 0x59, 0x15, 0xc4, 0x2d, 0x78, 0xc8, 0xf3, 0x14, 0x38, 0x87, 0x39, 0xb3, 0x58, 0xb5, 0x95, 0x07, 0x25, 0xd9, 0xc1, 0xac, 0x04];
    +            let both: &[u8] = &[0x88, 0x64, 0x15, 0xce, 0x5e, 0x3b, 0x8d, 0x35, 0xdb, 0xd2, 0xb5, 0xfa, 0x8e, 0xa7, 0x73, 0x10, 0x66, 0x83, 0x1b, 0xd1, 0xde, 0x0f, 0x25, 0x86, 0xeb, 0xe5, 0x42, 0x44, 0xad, 0x62, 0xff, 0x11, 0x31, 0xb8, 0xce, 0x94, 0x4d, 0x2b, 0xb9, 0x7e, 0xd5, 0x81, 0x7f, 0xc2, 0x40, 0xbf, 0x3d, 0xa5, 0x25, 0xa5, 0xf9, 0xdf, 0x53, 0x68, 0xc4, 0xf6, 0xbe, 0x06, 0x7d, 0xf3, 0xc7, 0xdc, 0x5b, 0x84, 0xce, 0xd2, 0xb2, 0xeb, 0x87, 0x62, 0x60, 0xe3, 0x10, 0x05, 0x64, 0x59, 0x15, 0xc4, 0x2d, 0x78, 0xc8, 0xf3, 0x14, 0x38, 0x87, 0x39, 0xb3, 0x58, 0xb5, 0x95, 0x07, 0x25, 0xd9, 0xc1, 0xac, 0x04];
    +
    +            let chk_a = crc32(0, &a);
    +            assert_eq!(chk_a, 101488544);
    +            let chk_b = crc32(0, &b);
    +            assert_eq!(chk_b, 2995985109);
    +
    +            let combined = crc32_combine(chk_a, chk_b, 64);
    +            assert_eq!(combined, 2546675245);
    +            let chk_both = crc32(0, &both);
    +            assert_eq!(chk_both, 3010918023);
    +            assert_eq!(combined, chk_both);
    +        }
    +    }
    +
        #[test]
        fn test_crc32_combine() {
            ::quickcheck::quickcheck(test as fn(_) -> _);

Running `cargo test` passed! I was at my wits end! How could the C code fail but the Rust code succeed??

I felt like I had enough information that I reported the issue to zlib-rs. Let me interrupt this story to mention that I really want to thank Folkert de Vries (maintainer of zlib-rs) for help debugging this. They were extremely friendly and helpful in figuring out what was going wrong. Folkert responded to my issue that my C program sample works for them!
Why would my machine be any different? I was running in the WSL at the time, maybe that could cause weirdness? I decided to write up a Containerfile to ensure I had a clean environment:

    :::Dockerfile
    FROM ubuntu:24.04

    RUN apt-get update && \
        apt-get install -y \
            build-essential \
            curl \
            git \
            pkg-config \
            libssl-dev

    RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
    ENV PATH="/root/.cargo/bin:${PATH}"
    RUN curl -sSL https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add -
    RUN echo "deb http://apt.llvm.org/noble/ llvm-toolchain-noble-20 main" > /etc/apt/sources.list.d/llvm.list
    RUN apt-get update  && apt-get upgrade -y && apt-get install -y clang-20
    RUN cargo install cargo-c
    RUN mkdir /scratch
    RUN git clone https://github.com/trifectatechfoundation/zlib-rs.git /scratch/zlib-rs
    COPY ./test.c /scratch/zlib-rs/libz-rs-sys-cdylib/test.c
    WORKDIR /scratch/zlib-rs/libz-rs-sys-cdylib
    ENV RUSTFLAGS="-Ctarget-cpu=native" # comment this out to fix the bug
    RUN cargo cbuild --release
    RUN clang-20 -o test test.c -I ./include/ -static ./target/x86_64-unknown-linux-gnu/release/libz_rs.a
    ENV LD_LIBRARY_PATH="target/x86_64-unknown-linux-gnu/release/"
    ENTRYPOINT ["./test"]

While experimenting with setting up this container, I found a lead at last! If I compiled with `RUSTFLAGS="-Ctarget-cpu=native"`, the program gave the wrong results. If I compiled *without* using native code generation, the program worked correctly. Bizarre!!

Backing up a bit, let me explain what `RUSTFLAGS="-Ctarget-cpu=native"` actually does (if you know already, please skip to the next paragraph). Compilers like `rustc` have feature flags for each target (aka OS + CPU architecture family) which allows them to optionally emit code that uses features of processors. For example, most x86 processors have `sse2`, and ARM64 processors have NEON or SVE. Newer processes usually come with newer features which provide optimized implementations of some useful thing, for example some x86 processors has optimized implementations of SHA hashing. Since not all computers have every feature, these need to be opted into at compile time. In the case of `RUSTFLAGS="-Ctarget-cpu=native"` I'm telling Rust "use all the features for my current processor." This is a way to eke out the most performance from a program. But in this case, it meant I had a bug on my hands! Folkert (maintainer of zlib-rs) suggested I try to narrow down exactly which instruction set extension was causing the issue. After a bit of binary searching, I found out it was `avx512vl`. AVX is an extension to provide [SIMD](https://en.wikipedia.org/wiki/Single_instruction,_multiple_data) and AVX512-VL is an extension which allows interoperability between 128/256-bit wide SIMD and faster 512-bit wide SIMD. This made a lot of sense in some ways, after all, I have an AMD R9 9950X, and one of it's features is AVX512 support! But how exactly did these AVX512 instructions get into the final binary?

> **NOTE**:<br> As pointed out in a message on Mastodon, AVX512-VL is actually 11 years old! It was first introduced in Intel AVX512 implementations. However, AVX512 support in Rust is relatively new.

So enabling AVX512 was the culprit for the bug in crc32 calculations. Skimming over the zlib-rs code, I was a bit surprised to find that it does not explicitly use AVX-512 *anywhere*! In fact it uses the older SSE4.1 instruction set (presumably for maximum portability). So why was AVX512-VL causing these issues? Unfortunately, I don't know for sure. But I have a theory.

Rust uses LLVM as it's default backend (the bit of the compiler that emits instructions/binaries). LLVM probably realized it could use AVX512-VL instructions (available on my machine) to speed up the SSE4.1 code that zlib-rs is using. However, AVX512-VL is new enough that there was a bug in the compiler - a miscompilation - and the wrong code was emitted. I haven't found a smoking gun issue but [it is probably one of these](https://github.com/llvm/llvm-project/issues?q=is%3Aissue%20state%3Aclosed%20avx512vl).

I am happy to report that this issue does not present itself with Rust 1.90+ or the latest release of zlib-rs. Many thanks again to Folkert for not only helping figure out the source of the issue, but also adding a mitigation to zlib-rs and cutting a new release to work around the miscompilation! Now the CPython test suite passes when linked against zlib-rs and I can continue my experiments...
