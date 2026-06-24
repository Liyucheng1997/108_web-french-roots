# -*- coding: utf-8 -*-
"""把 法语构词-1.1.md 解析成图数据 (节点 + 边)。
结构: 词根(root) -> 派生词(word) 树, 缩进(Tab)表示层级。
另解析词缀(affix): 前缀/后缀。
输出 graph-data.js (window.GRAPH = {...})。
"""
import re, json, sys

SRC = "法语构词-1.1.md"

def split_label_meaning(text):
    """'argent/n.m 银,钱财' -> ('argent','n.m 银,钱财')
       'ac/ag/尖的'        -> ('ac/ag','尖的')  最后一段为释义"""
    parts = text.split("/")
    if len(parts) == 1:
        return parts[0].strip(), ""
    meaning = parts[-1].strip()
    label = "/".join(parts[:-1]).strip()
    return label, meaning

POS_RE = re.compile(r"^(n\.?\s?[fme]|adj|adv|v|prep|pron|conj|interj)\b", re.I)
def extract_pos(meaning):
    m = POS_RE.match(meaning.strip())
    return m.group(0).strip() if m else ""

def first_letter(label):
    for ch in label:
        if ch.isascii() and ch.isalpha():
            return ch.upper()
    # 处理带音符的首字母
    norm = {"à":"A","â":"A","é":"E","è":"E","ê":"E","î":"I","ï":"I","ô":"O","û":"U","ù":"U","ç":"C"}
    for ch in label.lower():
        if ch in norm:
            return norm[ch]
    return "#"

def main():
    with open(SRC, encoding="utf-8") as f:
        lines = f.readlines()

    nodes = {}      # id -> node
    links = []      # {source,target}
    order = 0

    def add_node(nid, **kw):
        nonlocal order
        if nid in nodes:
            nid = nid + "__" + str(order)  # 去重
        kw["id"] = nid
        kw["order"] = order
        nodes[nid] = kw
        order += 1
        return nid

    # ---- 区段定位 ----
    sec = None  # 'prefix' / 'suffix' / 'simple' / 'compound'
    list_re = re.compile(r"^(\t*)-\s+(.*\S)\s*$")

    # 用于树解析的栈: [(depth, node_id, root_id)]
    stack = []
    cur_root_kind = None

    affix_group = None  # 当前词缀大类名 (如 名词性后缀)
    affix_sub = None    # 当前词缀子类名 (如 指物)

    for raw in lines:
        line = raw.rstrip("\n")
        s = line.strip()

        # 区段切换 (这些是无缩进的纯标题行)
        if s == "前缀":
            sec = "prefix"; stack=[]; continue
        if s == "后缀":
            sec = "suffix"; stack=[]; continue
        if s == "简单词根":
            sec = "simple"; cur_root_kind="simple"; stack=[]; continue
        if s == "合成词根":
            sec = "compound"; cur_root_kind="compound"; stack=[]; continue
        if s == "词根" or s == "词缀":
            continue

        m = list_re.match(line)
        if not m:
            # 词缀里的分类标题如 "1. 方向性前缀"
            if sec in ("prefix","suffix") and re.match(r"^\d+\.", s):
                affix_group = re.sub(r"^\d+\.\s*","",s)
                affix_sub = None
            continue

        depth = len(m.group(1))
        text = m.group(2)
        label, meaning = split_label_meaning(text)
        if not label:
            continue

        if sec in ("prefix","suffix"):
            # 纯中文的列表项是子分类标题(如 指物/指人), 不是真词缀
            if not re.search(r"[A-Za-zàâéèêîïôûùç]", label):
                affix_sub = label
                continue
            grp = affix_group or ""
            if affix_sub:
                grp = (grp + " · " + affix_sub) if grp else affix_sub
            nid = add_node("affix::"+label+"::"+str(order),
                           label=label, meaning=meaning,
                           type="affix", affixType=sec, group=grp,
                           letter=first_letter(label))
            continue

        if sec in ("simple","compound"):
            node_type = "root" if depth == 0 else "word"
            nid = add_node(("root::" if depth==0 else "word::")+label+"::"+str(order),
                           label=label, meaning=meaning,
                           pos=extract_pos(meaning),
                           type=node_type,
                           rootKind=cur_root_kind,
                           letter=first_letter(label))
            # 维护栈
            while stack and stack[-1][0] >= depth:
                stack.pop()
            if depth == 0:
                root_id = nid
                nodes[nid]["rootId"] = nid
            else:
                parent = stack[-1] if stack else None
                if parent:
                    links.append({"source": parent[1], "target": nid, "kind":"derive"})
                    nodes[nid]["parent"] = parent[1]
                root_id = stack[0][2] if stack else nid
                nodes[nid]["rootId"] = root_id
            stack.append((depth, nid, root_id if depth>0 else nid))

    out = {"nodes": list(nodes.values()), "links": links}
    stats = {
        "roots": sum(1 for n in out["nodes"] if n["type"]=="root"),
        "words": sum(1 for n in out["nodes"] if n["type"]=="word"),
        "affixes": sum(1 for n in out["nodes"] if n["type"]=="affix"),
        "links": len(links),
    }
    with open("graph-data.js","w",encoding="utf-8") as f:
        f.write("window.GRAPH = ")
        json.dump(out, f, ensure_ascii=False)
        f.write(";\n")
    print(json.dumps(stats, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
