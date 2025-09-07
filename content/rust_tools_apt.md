Title: Rust CLI tools apt repo
Date: 2022-11-26
Tags: rust, packaging

> tl;dr
> Go to [http://apt.cli.rs](http://apt.cli.rs) and follow the instructions to add the apt repo

I guess its only fair to start my new blogging kick by catching up on a project I'd worked on several months ago which is pretty much "done." I really like several Rust tools, such as [`ripgrep`](https://github.com/BurntSushi/ripgrep), [`hyperfine`](https://github.com/sharkdp/hyperfine), and [`fd`](https://github.com/sharkdp/fd). I wanted an easy way to install them on Debian-based systems that may not have them in the official repos, so I needed to create my own apt repo. I was originally considering making a ppa, or private package archive, since I mainly use Ubuntu, but I decided I wanted these tools available on Debian as well, so my only option was an apt repo.

It turns out that apt repos are really simple, you just need to serve a directory with e.g. nginx. It took me a while to find a tool I liked using for making the apt repo, however. I started with trying `reprepro`, but I found it was more annoying to use than I wanted, so I ended up using [`aptly`](https://www.aptly.info/), a newer apt repo management tool.

When setting up the repo, my criteria for inclusion were:

 - the tool must be able to build `*.deb` packages. This is the package format for Debian/Ubuntu so definitely required
 - the tool must build those packages. I wanted to use the official/same binaries as those in the Github release
 - the binary packages must be statically musl-linked. Since various versions of Debian/Ubuntu use different versions of glibc, you can get version compatibility errors if you don't statically link. Statically linking to musl is *much* easier than glibc, so this seemed to be the best route to avoid compatibility errors.

With these criteria in hand, I then set up the apt repo with the CLI tools that fit and wrote a script to try updating all of the packages, pulling from the official Github releases. I have subscribed to releases on Github from all the repos that are currently included in the apt repo so all I have to do is run the script when a new release comes out from one of the repos. I may end up setting up a cronjob that runs this update script, but I'm weighing whether it is worth any potential risks...

Anyway, if you are interested in using this apt repo, head on over to [https://apt.cli.rs](http://apt.cli.rs), I've written up the commands you need to get started using the apt repo.

If you have suggestions for Rust CLI tools that should be included, please [open an issue on the github](https://github.com/emmatyping/apt.cli.rs/issues/new)! If a package doesn't build musl-linked Debian packages, consider opening an issue on that project to add it. However, please *do not* spam maintainers asking for these packages to be built. I unfortunately do not have time to contribute to the packaging of every great Rust CLI tool, but I can add them to the apt repo if they are packaged already!

Anyway, hopefully someone else finds it useful!
