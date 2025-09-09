Title: New Rust crate: generational-arena-dom
Date: 2023-07-08
Tags: html, rust

I've just published a new crate someone may find interesting. I recently had a take-home assessment where I used the [Servo project's](https://servo.org/) `html5ever` HTML parser crate. [`html5ever`](https://github.com/servo/html5ever) is the main crate that servo uses to parse HTML content on the web. This crate is very customizable, and you have to bring your own implementation of the DOM (which means you can handle memory management however you want!). They provide an example implementation of the DOM that uses `Rc<RefCell<T>>`s all over, which is a bit annoying to use with Rust's borrow checking model. This becomes particularly frustrating when dealing with frequent DOM mutations, as was the case in my project.

Fortunately, I recalled the benefits of using arenas for ergonomic memory management when working with trees. I also had recently read about [Vale's generational arena usage](https://verdagon.dev/blog/hybrid-generational-memory), and I was inspired to build a DOM implementation based on a generational arena design. Generational arenas are nice because they don't suffer from [the ABA problem](https://en.wikipedia.org/wiki/ABA_problem), so it is thread-safe to add, update, and delete nodes in the DOM. I ended up coming across the [generational-indextree](https://crates.io/crates/generational-indextree) crate, which uses tokens instead of references to refer to tree members, which made working with mutable elements of the DOM much easier!

Anyway, I encourage anyone who is interested to learn more to check out the project [on my github](https://github.com/emmatyping/generational-arena-dom) or [on the project page on crates.io](https://crates.io/crates/generational-arena-dom)
