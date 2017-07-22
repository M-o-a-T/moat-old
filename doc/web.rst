The Web frontend
################

MoaT's web front-end is dynamic. It basically works like this.

The web page displays a sub-hierarchy under /web. The default is
/web/default. Within that hierarchy you can create items (``moat web add
…``) which refer to data that get displayed.

The front-end opens a Web socket and tells the server which part to
display. The sub-hierarchy is not transmitted all at once; instead, the
server sends "replace" messages which include the parent element's ID;
the element in question gets appended to the parent's content if it's not
found.

Entries are updated dynamically, whenever they change in etcd. For that
to work, there are a couple of conventions:

* All top-level elements have that entry's ID.

* The container for sub-entries has the same ID, prefixed with "c".
  New entries will be appended to that.

* The container for the item itself, if there is one at the hierarchy
  level, has an ID prefixed with "d".

* The actual data (i.e. not the title or any buttons) has an ID
  prefixed with "e". This will restict visual effects like fading to the
  data itself.

* If a hierarchy-level element is replaced, the content of the containers
  for c+ID and d+ID are preserved.

IDs are created by concatenating "f_" with the creation serial number of
the item's etcd entry.

Requests to change state are sent via the same web socket. They include
the desired state and the ID of the element in question. The Web element
shall not directly update the state it displays.

The practical upshot of this is that you can do this:

    moat dev extern add my/flag bool input/topic=read.some.flag
    moat web add default/foo bool extern/my/flag
    moat run -g extern &
    moat web serve -p 8080 &
    firefox http://localhost:8080

then if somebody sends some JSON {"value":"on"} to that topic on the
"alert" exchange, your web page will change.

More to come.
