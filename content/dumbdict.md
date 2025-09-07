Title: Stupid solutions for stupid problems
Date: 2018-06-04
Tags: silly, python

A while back, a friend of mine was working on a coding challenge for some internship. The prompt said to create a dictionary with string keys and string values in your favorite programming language, without using the built in dictionary type.

This got me thinking of how I would solve this, and this terrible monster is what I came up with:

    :::python
    class DumbDict:
        __getitem__ = getattr
        __setitem__ = setattr

This is a very silly solution. I don't feel bad about it. Here it is in action:

    :::python
    >>>d = DumbDict()
    >>>d['hi'] = 'test'
    >>>d['hi']
    'test'


How does it work? Well, in Python `__getitem__` is the protocol for subscribtion access. When I write `d['hi']` Python internally calls `d.__getitem__('hi')`. So whats the deal with the `getattr` call then?

In Python, everything is an object. By default, objects internally map attribute names to values. In my dictionary implementation, I take advantage of this to use Python's internals to create my dictionary.

The pros of this dictionary are that it is fast. It is close (within 10%) of the builtin dictionary type (there is a bit of overhead with function calls).

There are quite a few cons, the first of which several of the more knowledable among you have already realized. I'm totally cheating here. Well, maybe. Or I'm not. Technically, classes use something called `types.MappingProxyType` to manage attribute mappings. This is however an implementation detail, so its up to personal opinion whether I'm using a built in dictionary or not. Anyway, I think its pretty cool. And remember I did say it was stupid...
