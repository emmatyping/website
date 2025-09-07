Title: Revamping my blog... again
Date: 2025-09-07
Tags: meta, python

## Background

Well, I've succumbed to the ever-present urge to completely change one's blog setup. It all started when
I wanted to add my blog to the [Awesome PyLadies' blogs repo](https://github.com/cosimameyer/awesome-pyladies-blogs/). As part of the configuration you can add your blog's RSS feed (structured information about a blog's contents). But the configuration says:

> if you wish to have your blog posts being promoted by the Mastodon bot; the RSS feed should be for Python-related posts

My previous blog generator was [zola](https://www.getzola.org/), which worked really well and was easy to set up! However, zola does not support per-tag (or "taxonomy" as zola calls them) feeds. I considered contributing support for this to zola, but I figured I'd look around at other static site generators and see what they support. My blog content is just a bunch of Markdown files after all, so it should be easy to move to another static site generator!

## Yak shaving, for fun and profit

I came across [Pelican](https://getpelican.com/), which was really appealing for a few reasons. First, it supported per-feed RSS feeds. But also, it is written in Python and I felt like it would be fitting since I am a Pythonista. So I decided I would try to port my blog to Pelican. As you may be able to tell by looking at the footer, I did so successfully :)

Setting up Pelican is actually super easy. I installed pelican with markdown support by running `uv tool install pelican[markdown]` and ran `pelican-quickstart` to set up a project. After answering a few prompts, I had a full project set up and could copy over the Markdown files used to write this blog. After changing the metadata from zola's format to Pelican's, I had a blog generated... with no theme.

Oh... I needed to see what themes were available. Fortunately Pelican makes this easy by going to the [pelicanthemes.com](https://pelicanthemes.com/) website. That site has a number of community authored themes. Unfortunately, I didn't see any themes I loved.

## Introducing pelican-theme-terminimal

So, I did the only natural thing to do and ported the [zola theme I was using](https://github.com/pawroman/zola-theme-terminimal) to Pelican. Fortunately, this wasn't actually too bad. Zola uses [Tera](https://keats.github.io/tera/) for its templates, which is based on Jinja2, which is what Pelican uses. So for the most part I could minimally update the variables used and get the theme ported over easily. The layout between the two is slightly different so I had to restructure how things are designed, but overall it was pretty easy and enjoyable.

You can check out [the theme's code here](https://github.com/emmatyping/pelican-theme-terminimal/). I
don't plan on working on the theme a *ton* more, mostly just to add features or customizations I want, but it is open source if anyone else wants to use it or submit patches.

The top priorities I have to work on are:

- Links to RSS feeds
- Mastodon verification

So yeah, my blog is now running on Pelican and Python 🎉

I have a few ideas to blog about over the next week or two so check back soon, or subscribe to
[my RSS feed](/feeds/all.rss.xml).
