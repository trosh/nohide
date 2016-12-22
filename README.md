# No Hide

editors that dont really delete,
or just an excuse to build editors

## Idea

Reading good authors' drafts brings insight and transparency
to their writing process. Reading people's thought out edits
on online fora can bring the conversation to life.

Why not make a forum where everything you delete as you type
or edit can still be accessed? The users / writers, aware of
this, will write with a different mindset; let's see if it's
of any use!

## Current solution

Implement one or several POC editors that keep deleted text
accessible.

Instead of a full blown history graph, I currently choose to
flatten deleted text. The point is not to scroll through
history, just to see the accumulated attempts.

### For example

![example ed session](helloworld.gif)

<!--
<pre>
$ ed
>a
hello world
.
>s/hello/goodbye
goodbye world
>P
<del>hello</del> goodbye world
</pre>
-->

## TODO:

- Everything in ed's help's todo list
- Choose how to append after last line if there is an appendix.
  (currently doesn't merge appendix as beginning of new text)
- explore non line based storage ?
- explore journaling storage (line-based or not)
- vi
