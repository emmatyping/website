Title: Revamping my blog
Date: 2022-11-25
Tags: meta

Well, I've decided I want to blog a bit more, in part thanks to [Simon Willison's post](https://simonwillison.net/2022/Nov/6/what-to-blog-about/) suggesting keeping a blog is a good idea.

I've changed the UI a bit and I am now publishing via a Github action (I now just need to write a markdown file and push to a git repo!). I hope making it easier to blog will hopefully mean I blog a bit more.

One slight issue I ran into is I would push a commit, then my website would go down. The custom domain setting in Github pages would be reset to empty. At first, I thought this was a bug, how could this get reset so frequently! Turns out Github ties the custom domain to a file named `CNAME` in the root of the `gh-pages` branch (or whatever you configure to publish in the settings). I've now set that as a static asset to be included in the root so I won't run into this problem, but rather annoying behavior, my git repo shouldn't be used to store configuration!