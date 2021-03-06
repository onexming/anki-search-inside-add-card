def to_tag_hierarchy(tags):
    tmap = {}
    for t in sorted(tags, key=lambda t: t.lower()):
        tmap = _add_to_tag_list(tmap, t)
    tmap = dict(sorted(tmap.items(), key=lambda item: item[0].lower()))
    return tmap


def iterateTagmap(tmap, prefix):
    if len(tmap) == 0:
        return []
    res = []
    if prefix:
        prefix = prefix + "::"
    for key, value in tmap.items():
        if type(value) is dict:
            if len(value) > 0:
                res.append(prefix + key)
                res +=  iterateTagmap(value, prefix + key)
            else:
                res.append(prefix + key)
    return res


def _add_to_tag_list(tmap, name):
    """
    Helper function to build the tag hierarchy.
    """
    names = [s for s in name.split("::") if s != ""]
    for c, d in enumerate(names):
        found = tmap
        for i in range(c):
            found = found.setdefault(names[i], {})
        if not d in found:
            found.update({d : {}}) 
    return tmap