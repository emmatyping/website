Title: Using multiprocessing and sqlite3 together
Date: 2023-05-19
Tags: sql, python, multiprocessing

> Note from the author: this is a pseudo TIL, but I hadn't seen it written down anywhere, hopefully someone finds it useful!
> Jump to "Solution" below if you don't care about the background.

# Background

### Generating Data

I recently started working on a reinforcement learning project, and I needed to generate a lot of training data. The project involves quantum compilers, so the data I generate is quantum circuits. For those unfamiliar, quantum circuits are just sequences of unitary matrices laid out in a particular order. I chose to store the circuit as a sequence of unitary gate names. The output of the data generation is the unitaries (numpy arrays) that are the result of multiplying the matrices in the circuit together.

I ended up wanting to generate somewhere in the region of a few hundred billion matrices, each of them very small. I knew off the bat that this would require a fair bit of time, and I wanted to take advantage of the 32 core server I own. Since I was using Python to generate this data, I used the multiprocessing module. Sadly I cannot yet take advantage of [Python multithreading coming in 3.12](https://martinheinz.dev/blog/97).

### Disk Space Woes

For saving the generated matrices, I started off by doing the simplest thing, just using plain-old `np.savetxt` to save the (pretty tiny) matrices to disk in each process after computing the product of the matrices in the quantum circuit. This... was problematic. I quickly ran into a disk out of space error. Normally this means I need to clear out space on whatever VM I am using, but there was one problem -- I still had hundreds of gigabytes of space left on disk! 

I quickly deduced the error actually was caused by hitting the limit on entries in a directory, dang it [CIFS](https://cifs.com/)! I briefly tried to make my own schema to split the unitaries into more directories to avoid this limit but I ended up hitting more file system limits. It was clear just writing files to disk wouldn't scale to the size of dataset I needed to generate.

### Choosing a Database

Of course, dealing with so many small files, a database was the right solution to this problem. Why didn't I start with a database to begin with? Partially because I wanted to make it easy to load individual unitaries (`np.loadtxt` is an incredibly handy API). Also, I was just hacking this data generation script together.

I had one issue with switching to a database: I wanted something simple and lightweight, I didn't need anything fancy like postgres or the like. Sqlite is the obvious choice but sqlite does not by default support concurrent *writes*, which is exactly what I wanted to do!

# Solution


So how can one achieve concurrent writes in Python using sqlite3? Sqlite by default uses a rollback log to maintain consistency. You can change the configuration so that sqlite uses [a *write-ahead* log (WAL) mode](https://www.sqlite.org/wal.html) as well, which allows for concurrent writes. You can enable WAL mode in Python by setting the [journal mode](https://www.sqlite.org/pragma.html#pragma_journal_mode):

    :::python
    # assume some Cursor object `cursor`
    cursor.execute('PRAGMA journal_mode = WAL')


However, I started getting exceptions part way through. Some processes calculating the unitaries were being told the database was locked, even though it should not be (these processes should be writing to the WAL, which I want to always be available). Therefore I also set [the sqlite pragma `synchronous`](https://www.sqlite.org/pragma.html#pragma_synchronous) to `OFF`, which means that the WAL does not synchronize before checkpoints. Note this is **dangerous** because theoretically your database could become corrupted if the process crashes or the server shuts down. This is acceptable to me because I can always regenerate the database and either of these are very unlikely to occur while I run these data generation tasks. This can be done in Python like so:

    :::python
    # assume some Cursor object `cursor`
    cursor.execute('PRAGMA synchronous = OFF')

In summary, by enabling the WAL and turning some sync'ing off, I was able to get multi-processed Python code to concurrently write to a sqlite database. This also gave a nice speed bump since sqlite is optimized for writing many small amounts of data to disk, a nice bonus!