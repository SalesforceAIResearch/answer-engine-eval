def greedy_set_cover(universe, subsets):
    """
    Greedy algorithm for set cover problem.
    Returns the keys (source indices) instead of the subsets.
    """
    elements = set(universe)
    covered = set()
    cover = []
    subsets_items = list(subsets.items())
    while covered != elements:
        source_idx, subset = max(subsets_items, key=lambda item: len(set(item[1]) - covered))
        cover.append(source_idx)
        covered |= set(subset)
    return cover
